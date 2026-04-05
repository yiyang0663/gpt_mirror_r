import json

from django.http import HttpResponse, JsonResponse, StreamingHttpResponse
from rest_framework.views import APIView

from app.accounts.quota import build_user_quota_status
from app.chatgpt.relay import build_proxy_headers, build_relay_chat_completions_url, \
    forward_request, get_gateway_account_mirror_token, is_stream_request, resolve_proxy_mirror_token
from app.chatgpt.usage import save_usage_ledger
from app.settings import CHATGPT_GATEWAY_URL


class ChatCompletionsProxyView(APIView):
    authentication_classes = ()
    permission_classes = ()
    MAX_CAPTURE_BYTES = 262144

    @staticmethod
    def _extract_bearer_token(request):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return None
        return auth_header.split(" ", 1)[1].strip()

    @staticmethod
    def _extract_request_model(request_body):
        if not request_body:
            return ""

        try:
            payload = json.loads(request_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return ""
        return str(payload.get("model") or "").strip()

    @staticmethod
    def _append_capture(chunks, current_size, chunk):
        if current_size < ChatCompletionsProxyView.MAX_CAPTURE_BYTES:
            remaining = ChatCompletionsProxyView.MAX_CAPTURE_BYTES - current_size
            chunks.append(chunk[:remaining])
            current_size += len(chunk[:remaining])
        return current_size

    @staticmethod
    def _stream_chunks(proxy_response, usage_context=None, request_model="", request_type="chat.completions"):
        capture_chunks = []
        capture_size = 0
        try:
            for chunk in proxy_response.iter_content(chunk_size=8192):
                if chunk:
                    if usage_context:
                        capture_size = ChatCompletionsProxyView._append_capture(capture_chunks, capture_size, chunk)
                    yield chunk
        finally:
            if usage_context:
                save_usage_ledger(
                    user=usage_context["user"],
                    account=usage_context["account"],
                    model_name=request_model,
                    request_type=request_type,
                    status_code=proxy_response.status_code,
                    response_body=b"".join(capture_chunks),
                    is_stream=True,
                )
            proxy_response.close()

    @staticmethod
    def _build_response(proxy_response, stream, usage_context=None, request_model="", request_type="chat.completions"):
        content_type = proxy_response.headers.get("Content-Type", "application/json")
        if stream or content_type.startswith("text/event-stream"):
            streaming_response = StreamingHttpResponse(
                ChatCompletionsProxyView._stream_chunks(
                    proxy_response,
                    usage_context=usage_context,
                    request_model=request_model,
                    request_type=request_type,
                ),
                status=proxy_response.status_code,
                content_type=content_type,
            )
            if proxy_response.headers.get("Cache-Control"):
                streaming_response["Cache-Control"] = proxy_response.headers["Cache-Control"]
            return streaming_response

        response_body = proxy_response.content
        if usage_context:
            save_usage_ledger(
                user=usage_context["user"],
                account=usage_context["account"],
                model_name=request_model,
                request_type=request_type,
                status_code=proxy_response.status_code,
                response_body=response_body,
                is_stream=False,
            )
        response = HttpResponse(
            response_body,
            status=proxy_response.status_code,
            content_type=content_type,
        )
        proxy_response.close()
        return response

    def post(self, request):
        bearer_token = self._extract_bearer_token(request)
        if not bearer_token:
            return JsonResponse({"message": "Authorization header is required"}, status=401)

        request_body = request.body
        request_stream = is_stream_request(request_body)
        request_model = self._extract_request_model(request_body)
        proxy_context = None
        try:
            proxy_context = resolve_proxy_mirror_token(bearer_token, model_name=request_model)
        except PermissionError as exc:
            return JsonResponse({"message": str(exc)}, status=403)

        if proxy_context:
            quota_status = build_user_quota_status(proxy_context["user"], channel="api", model_name=request_model)
            if not quota_status["allowed"]:
                save_usage_ledger(
                    user=proxy_context["user"],
                    account=proxy_context["account"],
                    model_name=request_model,
                    request_type="chat.completions",
                    status_code=429,
                    response_body=b"",
                    is_stream=False,
                    error_code="quota_exceeded",
                )
                return JsonResponse(
                    {
                        "message": quota_status["reason"],
                        "quota_rules": quota_status["rules"],
                    },
                    status=429,
                )
            account = proxy_context["account"]
            if account.is_relay_account:
                target_url = build_relay_chat_completions_url(account.relay_base_url)
                outbound_headers = build_proxy_headers(request.headers, f"Bearer {account.relay_api_key}")
            else:
                try:
                    gateway_mirror_token = get_gateway_account_mirror_token(proxy_context["user"], account)
                except PermissionError as exc:
                    return JsonResponse({"message": str(exc)}, status=403)
                target_url = f"{CHATGPT_GATEWAY_URL}{request.path}"
                outbound_headers = build_proxy_headers(request.headers, f"Bearer {gateway_mirror_token}")
        else:
            target_url = f"{CHATGPT_GATEWAY_URL}{request.path}"
            outbound_headers = build_proxy_headers(request.headers, request.headers.get("Authorization"))

        try:
            proxy_response = forward_request("POST", target_url, outbound_headers, request_body)
        except Exception as exc:
            if proxy_context:
                save_usage_ledger(
                    user=proxy_context["user"],
                    account=proxy_context["account"],
                    model_name=request_model,
                    request_type="chat.completions",
                    status_code=502,
                    response_body=b"",
                    is_stream=False,
                    error_code="proxy_request_failed",
                )
            return JsonResponse({"message": f"Proxy request failed: {exc}"}, status=502)

        return self._build_response(
            proxy_response,
            request_stream,
            usage_context=proxy_context,
            request_model=request_model,
            request_type="chat.completions",
        )

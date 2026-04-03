from django.http import HttpResponse, JsonResponse, StreamingHttpResponse
from rest_framework.views import APIView

from app.chatgpt.relay import build_proxy_headers, build_relay_chat_completions_url, forward_request, \
    is_stream_request, resolve_relay_mirror_token
from app.settings import CHATGPT_GATEWAY_URL


class ChatCompletionsProxyView(APIView):
    authentication_classes = ()
    permission_classes = ()

    @staticmethod
    def _extract_bearer_token(request):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return None
        return auth_header.split(" ", 1)[1].strip()

    @staticmethod
    def _stream_chunks(proxy_response):
        try:
            for chunk in proxy_response.iter_content(chunk_size=8192):
                if chunk:
                    yield chunk
        finally:
            proxy_response.close()

    @staticmethod
    def _build_response(proxy_response, stream):
        content_type = proxy_response.headers.get("Content-Type", "application/json")
        if stream or content_type.startswith("text/event-stream"):
            streaming_response = StreamingHttpResponse(
                ChatCompletionsProxyView._stream_chunks(proxy_response),
                status=proxy_response.status_code,
                content_type=content_type,
            )
            if proxy_response.headers.get("Cache-Control"):
                streaming_response["Cache-Control"] = proxy_response.headers["Cache-Control"]
            return streaming_response

        response = HttpResponse(
            proxy_response.content,
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
        relay_context = resolve_relay_mirror_token(bearer_token)

        if relay_context:
            account = relay_context["account"]
            target_url = build_relay_chat_completions_url(account.relay_base_url)
            outbound_headers = build_proxy_headers(request.headers, f"Bearer {account.relay_api_key}")
        else:
            target_url = f"{CHATGPT_GATEWAY_URL}{request.path}"
            outbound_headers = build_proxy_headers(request.headers, request.headers.get("Authorization"))

        try:
            proxy_response = forward_request("POST", target_url, outbound_headers, request_body)
        except Exception as exc:
            return JsonResponse({"message": f"Proxy request failed: {exc}"}, status=502)

        return self._build_response(proxy_response, request_stream)

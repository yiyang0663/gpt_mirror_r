import json
import time

from django.http import HttpResponse, JsonResponse, StreamingHttpResponse
from rest_framework.views import APIView

from app.accounts.quota import build_user_quota_status
from app.chatgpt.content_blocks import FILE_BLOCK_TYPE, IMAGE_BLOCK_TYPE, TEXT_BLOCK_TYPE, normalize_chat_content_blocks
from app.chatgpt.relay import build_proxy_headers, build_relay_chat_completions_url, \
    forward_request, get_gateway_account_mirror_token, is_stream_request, resolve_proxy_mirror_token
from app.chatgpt.usage import save_usage_ledger
from app.settings import CHATGPT_GATEWAY_URL


class ChatCompletionsProxyView(APIView):
    authentication_classes = ()
    permission_classes = ()
    MAX_CAPTURE_BYTES = 262144
    DEFAULT_RESPONSES_INSTRUCTIONS = "You are a helpful assistant."

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
    def _decode_request_payload(request_body):
        if not request_body:
            return None

        try:
            return json.loads(request_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None

    @staticmethod
    def _convert_block_to_responses_content(block):
        block_type = str(block.get("type") or "").strip()
        if block_type == TEXT_BLOCK_TYPE:
            text = str(block.get("text") or "")
            if not text.strip():
                return None
            return {
                "type": "input_text",
                "text": text,
            }

        if block_type == IMAGE_BLOCK_TYPE:
            image_payload = block.get("image_url") or {}
            image_url = str(image_payload.get("url") or "").strip()
            if not image_url:
                return None
            normalized = {
                "type": "input_image",
                "image_url": image_url,
            }
            detail = str(image_payload.get("detail") or "").strip()
            if detail:
                normalized["detail"] = detail
            return normalized

        if block_type == FILE_BLOCK_TYPE:
            file_payload = block.get("file") or {}
            normalized = {
                "type": "input_file",
            }
            for key in ("filename", "file_data", "file_id", "file_url"):
                value = str(file_payload.get(key) or "").strip()
                if value:
                    normalized[key] = value
            if "file_data" not in normalized and "file_id" not in normalized and "file_url" not in normalized:
                return None
            return normalized

        return None

    @classmethod
    def _should_use_relay_responses_compat(cls, account, model_name):
        if not account or not getattr(account, "is_relay_account", False):
            return False
        normalized_model = str(model_name or "").strip().lower()
        return normalized_model.startswith("gpt-5")

    @classmethod
    def _prepare_relay_request_body(cls, request_body, account, model_name):
        if not cls._should_use_relay_responses_compat(account, model_name):
            return request_body, None

        payload = cls._decode_request_payload(request_body)
        if not isinstance(payload, dict):
            return request_body, None

        messages = payload.pop("messages", None)
        if not isinstance(messages, list):
            return request_body, None

        instructions_list = []
        input_items = []
        for message in messages:
            if not isinstance(message, dict):
                continue
            role = str(message.get("role") or "").strip().lower()
            content_blocks = normalize_chat_content_blocks(message.get("content"))
            if not content_blocks:
                continue

            if role == "system":
                system_text = "".join(
                    str(block.get("text") or "")
                    for block in content_blocks
                    if str(block.get("type") or "") == TEXT_BLOCK_TYPE
                ).strip()
                if system_text:
                    instructions_list.append(system_text)
                continue

            if role not in {"user", "assistant", "developer"}:
                role = "user"

            content_items = []
            for block in content_blocks:
                normalized_block = cls._convert_block_to_responses_content(block)
                if normalized_block:
                    content_items.append(normalized_block)
            if not content_items:
                continue

            input_items.append(
                {
                    "role": role,
                    "content": content_items,
                }
            )

        payload["instructions"] = str(payload.get("instructions") or "\n\n".join(instructions_list)).strip() or cls.DEFAULT_RESPONSES_INSTRUCTIONS
        payload["input"] = input_items
        reasoning_effort = str(payload.pop("reasoning_effort", "") or "").strip()
        if reasoning_effort:
            reasoning_payload = payload.get("reasoning")
            if not isinstance(reasoning_payload, dict):
                reasoning_payload = {}
            reasoning_payload["effort"] = reasoning_effort
            payload["reasoning"] = reasoning_payload

        if "max_tokens" in payload and "max_output_tokens" not in payload:
            payload["max_output_tokens"] = payload.pop("max_tokens")

        payload.pop("n", None)
        payload.pop("logprobs", None)

        return json.dumps(payload).encode("utf-8"), {
            "mode": "relay_responses_compat",
        }

    @staticmethod
    def _extract_usage_payload(usage):
        if not isinstance(usage, dict):
            return {}

        prompt_tokens = int(usage.get("input_tokens") or usage.get("prompt_tokens") or 0)
        completion_tokens = int(usage.get("output_tokens") or usage.get("completion_tokens") or 0)
        total_tokens = int(usage.get("total_tokens") or (prompt_tokens + completion_tokens))
        return {
            "prompt_tokens": max(prompt_tokens, 0),
            "completion_tokens": max(completion_tokens, 0),
            "total_tokens": max(total_tokens, 0),
        }

    @classmethod
    def _extract_response_output_text(cls, payload):
        if not isinstance(payload, dict):
            return ""

        text_parts = []
        for item in payload.get("output") or []:
            if not isinstance(item, dict):
                continue
            for content_item in item.get("content") or []:
                if not isinstance(content_item, dict):
                    continue
                content_type = str(content_item.get("type") or "").strip()
                if content_type in {"output_text", "text"}:
                    text_parts.append(str(content_item.get("text") or ""))
        return "".join(text_parts)

    @staticmethod
    def _is_chat_completion_payload(payload):
        return isinstance(payload, dict) and isinstance(payload.get("choices"), list)

    @classmethod
    def _build_chat_completion_payload(cls, payload, request_model=""):
        usage_payload = cls._extract_usage_payload(payload.get("usage"))
        return {
            "id": payload.get("id") or f"chatcmpl-{int(time.time())}",
            "object": "chat.completion",
            "created": int(payload.get("created_at") or time.time()),
            "model": str(payload.get("model") or request_model or ""),
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": cls._extract_response_output_text(payload),
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": usage_payload,
        }

    @staticmethod
    def _extract_error_message(payload):
        if not isinstance(payload, dict):
            return ""

        error_payload = payload.get("error")
        if isinstance(error_payload, dict):
            return str(error_payload.get("message") or error_payload.get("detail") or "").strip()
        if isinstance(error_payload, str):
            return error_payload.strip()
        return str(payload.get("message") or payload.get("detail") or "").strip()

    @classmethod
    def _normalize_error_response_body(cls, response_body):
        try:
            payload = json.loads(response_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return response_body

        message = cls._extract_error_message(payload)
        if not message:
            return response_body

        normalized_payload = {
            "message": message,
            "error": payload.get("error"),
        }
        return json.dumps(normalized_payload).encode("utf-8")

    @staticmethod
    def _build_chat_completion_chunk(response_id, created_at, model_name, delta=None, finish_reason=None, usage=None):
        chunk_payload = {
            "id": response_id or f"chatcmpl-{int(time.time())}",
            "object": "chat.completion.chunk",
            "created": int(created_at or time.time()),
            "model": model_name or "",
            "choices": [
                {
                    "index": 0,
                    "delta": delta or {},
                    "finish_reason": finish_reason,
                }
            ],
        }
        if usage:
            chunk_payload["usage"] = usage
        return chunk_payload

    @classmethod
    def _encode_sse_payload(cls, payload):
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n".encode("utf-8")

    @classmethod
    def _stream_responses_as_chat_chunks(cls, proxy_response, usage_context=None, request_model="", request_type="chat.completions"):
        capture_chunks = []
        capture_size = 0
        response_id = ""
        created_at = int(time.time())
        response_model = request_model
        role_sent = False
        stream_finished = False
        latest_usage = {}
        streamed_text = ""
        stream_mode = ""

        try:
            for raw_line in proxy_response.iter_lines(decode_unicode=True):
                line = (raw_line or "").strip()
                if not line or not line.startswith("data:"):
                    continue

                payload_text = line[5:].strip()
                if not payload_text:
                    continue

                if payload_text == "[DONE]":
                    if stream_mode == "chat.completions":
                        done_chunk = b"data: [DONE]\n\n"
                        capture_size = cls._append_capture(capture_chunks, capture_size, done_chunk)
                        stream_finished = True
                        yield done_chunk
                        break
                    continue

                try:
                    payload = json.loads(payload_text)
                except json.JSONDecodeError:
                    continue

                if cls._is_chat_completion_payload(payload):
                    stream_mode = "chat.completions"
                    passthrough_chunk = f"data: {payload_text}\n\n".encode("utf-8")
                    capture_size = cls._append_capture(capture_chunks, capture_size, passthrough_chunk)
                    if payload.get("choices", [{}])[0].get("finish_reason"):
                        stream_finished = True
                    yield passthrough_chunk
                    continue

                payload_type = str(payload.get("type") or "").strip()
                if payload_type.startswith("response."):
                    stream_mode = "responses"

                if payload_type in {"response.created", "response.in_progress"}:
                    response_payload = payload.get("response") or {}
                    response_id = response_payload.get("id") or response_id
                    response_model = response_payload.get("model") or response_model
                    created_at = int(response_payload.get("created_at") or created_at)
                    usage_payload = cls._extract_usage_payload(response_payload.get("usage"))
                    if usage_payload:
                        latest_usage = usage_payload

                    if not role_sent:
                        encoded_chunk = cls._encode_sse_payload(
                            cls._build_chat_completion_chunk(
                                response_id,
                                created_at,
                                response_model,
                                delta={"role": "assistant"},
                            )
                        )
                        capture_size = cls._append_capture(capture_chunks, capture_size, encoded_chunk)
                        role_sent = True
                        yield encoded_chunk
                    continue

                if payload_type in {"response.output_text.delta", "response.output_text.done"}:
                    delta_text = str(payload.get("delta") or payload.get("text") or "")
                    if not delta_text:
                        continue
                    if not role_sent:
                        encoded_role_chunk = cls._encode_sse_payload(
                            cls._build_chat_completion_chunk(
                                response_id,
                                created_at,
                                response_model,
                                delta={"role": "assistant"},
                            )
                        )
                        capture_size = cls._append_capture(capture_chunks, capture_size, encoded_role_chunk)
                        role_sent = True
                        yield encoded_role_chunk

                    encoded_delta_chunk = cls._encode_sse_payload(
                        cls._build_chat_completion_chunk(
                            response_id,
                            created_at,
                            response_model,
                            delta={"content": delta_text},
                        )
                    )
                    capture_size = cls._append_capture(capture_chunks, capture_size, encoded_delta_chunk)
                    streamed_text += delta_text
                    yield encoded_delta_chunk
                    continue

                if payload_type == "response.completed":
                    response_payload = payload.get("response") or {}
                    response_id = response_payload.get("id") or response_id
                    response_model = response_payload.get("model") or response_model
                    created_at = int(response_payload.get("created_at") or created_at)
                    usage_payload = cls._extract_usage_payload(response_payload.get("usage"))
                    if usage_payload:
                        latest_usage = usage_payload

                    final_text = cls._extract_response_output_text(response_payload)
                    remaining_text = ""
                    if final_text:
                        if not streamed_text:
                            remaining_text = final_text
                        elif final_text.startswith(streamed_text):
                            remaining_text = final_text[len(streamed_text):]

                    if remaining_text:
                        if not role_sent:
                            encoded_role_chunk = cls._encode_sse_payload(
                                cls._build_chat_completion_chunk(
                                    response_id,
                                    created_at,
                                    response_model,
                                    delta={"role": "assistant"},
                                )
                            )
                            capture_size = cls._append_capture(capture_chunks, capture_size, encoded_role_chunk)
                            role_sent = True
                            yield encoded_role_chunk

                        encoded_delta_chunk = cls._encode_sse_payload(
                            cls._build_chat_completion_chunk(
                                response_id,
                                created_at,
                                response_model,
                                delta={"content": remaining_text},
                            )
                        )
                        capture_size = cls._append_capture(capture_chunks, capture_size, encoded_delta_chunk)
                        streamed_text += remaining_text
                        yield encoded_delta_chunk

                    encoded_finish_chunk = cls._encode_sse_payload(
                        cls._build_chat_completion_chunk(
                            response_id,
                            created_at,
                            response_model,
                            delta={},
                            finish_reason="stop",
                            usage=latest_usage,
                        )
                    )
                    done_chunk = b"data: [DONE]\n\n"
                    capture_size = cls._append_capture(capture_chunks, capture_size, encoded_finish_chunk)
                    capture_size = cls._append_capture(capture_chunks, capture_size, done_chunk)
                    stream_finished = True
                    yield encoded_finish_chunk
                    yield done_chunk
                    break
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

        if not stream_finished:
            done_chunk = b"data: [DONE]\n\n"
            yield done_chunk

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
        compat_mode = usage_context.get("compat_mode") if usage_context else ""
        is_event_stream = content_type.startswith("text/event-stream")

        if compat_mode == "relay_responses_compat" and proxy_response.ok and is_event_stream:
            streaming_response = StreamingHttpResponse(
                ChatCompletionsProxyView._stream_responses_as_chat_chunks(
                    proxy_response,
                    usage_context=usage_context,
                    request_model=request_model,
                    request_type=request_type,
                ),
                status=proxy_response.status_code,
                content_type="text/event-stream; charset=utf-8",
            )
            streaming_response["Cache-Control"] = "no-cache"
            return streaming_response

        if proxy_response.ok and (stream or is_event_stream):
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
        if compat_mode == "relay_responses_compat":
            if proxy_response.ok:
                try:
                    response_payload = json.loads(response_body.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    response_payload = {}
                if not ChatCompletionsProxyView._is_chat_completion_payload(response_payload):
                    response_body = json.dumps(
                        ChatCompletionsProxyView._build_chat_completion_payload(response_payload, request_model=request_model),
                        ensure_ascii=False,
                    ).encode("utf-8")
                content_type = "application/json"
            else:
                response_body = ChatCompletionsProxyView._normalize_error_response_body(response_body)
                content_type = "application/json"

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
        compat_context = None
        proxy_channel = "api"
        request_type = "chat.completions"
        try:
            proxy_context = resolve_proxy_mirror_token(bearer_token, model_name=request_model)
        except PermissionError as exc:
            return JsonResponse({"message": str(exc)}, status=403)

        if proxy_context:
            proxy_channel = proxy_context.get("channel") or "api"
            request_type = "web.chat.completions" if proxy_channel == "web" else "chat.completions"
            quota_status = build_user_quota_status(proxy_context["user"], channel=proxy_channel, model_name=request_model)
            if not quota_status["allowed"]:
                save_usage_ledger(
                    user=proxy_context["user"],
                    account=proxy_context["account"],
                    model_name=request_model,
                    request_type=request_type,
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
                request_body, compat_context = self._prepare_relay_request_body(request_body, account, request_model)
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
                    request_type=request_type,
                    status_code=502,
                    response_body=b"",
                    is_stream=False,
                    error_code="proxy_request_failed",
                )
            return JsonResponse({"message": f"Proxy request failed: {exc}"}, status=502)

        return self._build_response(
            proxy_response,
            request_stream,
            usage_context={
                **proxy_context,
                "compat_mode": compat_context.get("mode") if proxy_context and compat_context else "",
            }
            if proxy_context
            else None,
            request_model=request_model,
            request_type=request_type,
        )

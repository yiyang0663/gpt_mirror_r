import json
from urllib.parse import urlsplit, urlunsplit

import requests
from django.core import signing
from django.core.signing import BadSignature

from app.accounts.models import User
from app.chatgpt.dispatcher import select_dispatch_account
from app.chatgpt.models import ChatgptAccount
from app.utils import req_gateway

RELAY_MIRROR_TOKEN_SALT = "relay-mirror-token"
ACCOUNT_PROXY_TOKEN_SALT = "account-proxy-token"


def build_relay_mirror_token(user_id, chatgpt_id):
    payload = {
        "type": "relay_api",
        "user_id": user_id,
        "chatgpt_id": chatgpt_id,
    }
    return signing.dumps(payload, salt=RELAY_MIRROR_TOKEN_SALT)


def build_account_proxy_token(user_id, chatgpt_id):
    payload = {
        "type": "account_proxy",
        "user_id": user_id,
        "chatgpt_id": chatgpt_id,
    }
    return signing.dumps(payload, salt=ACCOUNT_PROXY_TOKEN_SALT)


def _load_proxy_payload(token):
    for salt in (ACCOUNT_PROXY_TOKEN_SALT, RELAY_MIRROR_TOKEN_SALT):
        try:
            payload = signing.loads(token, salt=salt)
        except BadSignature:
            continue
        return payload
    return None


def resolve_proxy_mirror_token(token, model_name=""):
    payload = _load_proxy_payload(token)
    if not payload:
        return None

    proxy_type = payload.get("type")
    if proxy_type not in {"relay_api", "account_proxy"}:
        return None

    user_id = payload.get("user_id")
    chatgpt_id = payload.get("chatgpt_id")
    if not isinstance(user_id, int) or not isinstance(chatgpt_id, int):
        return None

    user = User.objects.filter(id=user_id).first()
    account = ChatgptAccount.objects.filter(id=chatgpt_id).first()
    if not user or not account:
        raise PermissionError("当前代理通道不可用")

    selected_account = select_dispatch_account(
        user,
        channel="api",
        model_name=model_name,
        requested_account_id=chatgpt_id,
        entrypoint="api_proxy",
        allow_relay=True,
    )
    if not selected_account:
        raise PermissionError("当前代理通道不可用或不支持所选模型")

    if proxy_type == "relay_api" and not selected_account.is_relay_account:
        raise PermissionError("当前 relay 通道不可用")
    if proxy_type == "account_proxy" and selected_account.is_relay_account:
        raise PermissionError("当前官方代理通道不可用")

    return {"user": user, "account": selected_account, "proxy_type": proxy_type}


def resolve_relay_mirror_token(token, model_name=""):
    proxy_context = resolve_proxy_mirror_token(token, model_name=model_name)
    if proxy_context and proxy_context["proxy_type"] == "relay_api":
        return proxy_context
    return None


def resolve_gateway_proxy_context(token, model_name=""):
    proxy_context = resolve_proxy_mirror_token(token, model_name=model_name)
    if proxy_context and proxy_context["proxy_type"] == "account_proxy":
        return proxy_context
    return None


def get_gateway_account_mirror_token(user, account):
    if not user or not account or account.is_relay_account:
        raise PermissionError("当前官方账号通道不可用")

    try:
        gateway_response = req_gateway(
            "post",
            "/api/get-mirror-token",
            json={
                "isolated_session": user.isolated_session,
                "limits": user.model_limit,
                "chatgpt_list": [account.chatgpt_username],
                "user_name": user.username,
            },
        )
    except Exception:
        raise PermissionError("当前官方账号通道不可用")
    gateway_item = gateway_response[0] if gateway_response else {}
    mirror_token = gateway_item.get("mirror_token")
    if not mirror_token:
        raise PermissionError("当前官方账号通道不可用")
    return mirror_token


def build_relay_chat_completions_url(base_url):
    parsed = urlsplit(base_url.rstrip("/"))
    path = parsed.path.rstrip("/")

    if path.endswith("/chat/completions"):
        new_path = path
    elif path.endswith("/v1"):
        new_path = f"{path}/chat/completions"
    else:
        new_path = f"{path}/v1/chat/completions"

    return urlunsplit((parsed.scheme, parsed.netloc, new_path, parsed.query, parsed.fragment))


def build_proxy_headers(request_headers, authorization):
    headers = {}
    for key, value in request_headers.items():
        lower_key = key.lower()
        if lower_key in {"host", "content-length", "authorization"}:
            continue
        headers[key] = value

    headers["Authorization"] = authorization
    headers.setdefault("Content-Type", "application/json")
    return headers


def is_stream_request(body):
    if not body:
        return False

    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return False

    return bool(payload.get("stream"))


def forward_request(method, url, headers, body, timeout=300):
    return requests.request(method, url, headers=headers, data=body, stream=True, timeout=timeout, allow_redirects=False)

import json
from urllib.parse import urlsplit, urlunsplit

import requests
from django.core import signing
from django.core.signing import BadSignature
from django.utils import timezone

from app.accounts.models import User
from app.chatgpt.models import ChatgptAccount

RELAY_MIRROR_TOKEN_SALT = "relay-mirror-token"


def build_relay_mirror_token(user_id, chatgpt_id):
    payload = {
        "type": "relay_api",
        "user_id": user_id,
        "chatgpt_id": chatgpt_id,
    }
    return signing.dumps(payload, salt=RELAY_MIRROR_TOKEN_SALT)


def resolve_relay_mirror_token(token):
    try:
        payload = signing.loads(token, salt=RELAY_MIRROR_TOKEN_SALT)
    except BadSignature:
        return None

    if payload.get("type") != "relay_api":
        return None

    user_id = payload.get("user_id")
    chatgpt_id = payload.get("chatgpt_id")
    if not isinstance(user_id, int) or not isinstance(chatgpt_id, int):
        return None

    user = User.objects.filter(id=user_id, is_active=True).first()
    account = ChatgptAccount.objects.filter(id=chatgpt_id, auth_status=True).first()
    if not user or not account or not account.is_relay_account:
        return None
    if user.expired_date and user.expired_date <= timezone.now().date():
        return None

    if account.id not in [item.id for item in ChatgptAccount.get_by_gptcar_list(user.gptcar_list)]:
        return None

    return {"user": user, "account": account}


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

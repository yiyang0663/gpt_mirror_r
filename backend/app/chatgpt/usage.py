import json
from decimal import Decimal

from app.chatgpt.models import UsageLedger


def normalize_model_name(model_name):
    return str(model_name or "").strip()


def _extract_error_code(payload):
    if not isinstance(payload, dict):
        return ""

    error = payload.get("error")
    if isinstance(error, dict):
        return str(error.get("code") or error.get("type") or "").strip()
    if isinstance(error, str):
        return error.strip()
    return ""


def _extract_usage_fields(usage):
    if not isinstance(usage, dict):
        return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    prompt_tokens = int(usage.get("prompt_tokens") or 0)
    completion_tokens = int(usage.get("completion_tokens") or 0)
    total_tokens = int(usage.get("total_tokens") or (prompt_tokens + completion_tokens))
    return {
        "prompt_tokens": max(prompt_tokens, 0),
        "completion_tokens": max(completion_tokens, 0),
        "total_tokens": max(total_tokens, 0),
    }


def extract_usage_from_response_body(response_body, is_stream=False):
    if not response_body:
        return {"model_name": "", "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "error_code": ""}

    if not is_stream:
        try:
            payload = json.loads(response_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return {"model_name": "", "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "error_code": ""}

        usage_fields = _extract_usage_fields(payload.get("usage"))
        return {
            "model_name": normalize_model_name(payload.get("model")),
            **usage_fields,
            "error_code": _extract_error_code(payload),
        }

    text = response_body.decode("utf-8", errors="ignore")
    latest_model_name = ""
    latest_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    latest_error_code = ""

    for line in text.splitlines():
        if not line.startswith("data:"):
            continue
        event_data = line[5:].strip()
        if not event_data or event_data == "[DONE]":
            continue
        try:
            payload = json.loads(event_data)
        except json.JSONDecodeError:
            continue

        if not latest_model_name and payload.get("model"):
            latest_model_name = normalize_model_name(payload.get("model"))
        if isinstance(payload.get("usage"), dict):
            latest_usage = _extract_usage_fields(payload.get("usage"))
        if not latest_error_code:
            latest_error_code = _extract_error_code(payload)

    return {
        "model_name": latest_model_name,
        **latest_usage,
        "error_code": latest_error_code,
    }


def save_usage_ledger(
    *,
    user=None,
    account=None,
    model_name="",
    request_type="chat.completions",
    status_code=0,
    response_body=b"",
    is_stream=False,
    error_code="",
):
    if not user and not account:
        return None

    extracted = extract_usage_from_response_body(response_body, is_stream=is_stream)
    total_tokens = extracted["total_tokens"]
    unit_cost = getattr(account, "unit_cost", Decimal("0")) or Decimal("0")
    estimated_cost = Decimal(total_tokens) * Decimal(unit_cost)

    return UsageLedger.save_data(
        {
            "user": user,
            "account": account,
            "model_name": normalize_model_name(extracted["model_name"] or model_name),
            "request_type": request_type,
            "prompt_tokens": extracted["prompt_tokens"],
            "completion_tokens": extracted["completion_tokens"],
            "total_tokens": total_tokens,
            "estimated_cost": estimated_cost,
            "status_code": max(int(status_code or 0), 0),
            "error_code": (error_code or extracted["error_code"] or "").strip()[:128],
        }
    )

from typing import Iterable, Optional

from django.utils import timezone

from app.chatgpt.models import ChatgptAccount, DispatcherDecisionLog


HEALTH_SCORE_MAP = {
    ChatgptAccount.HEALTH_STATUS_HEALTHY: 0,
    ChatgptAccount.HEALTH_STATUS_DEGRADED: 1,
    ChatgptAccount.HEALTH_STATUS_DOWN: 2,
}


def normalize_model_name(model_name):
    return str(model_name or "").strip().lower()


def normalize_supported_models(values):
    return [str(item).strip().lower() for item in values or [] if str(item).strip()]


def account_supports_model(account, model_name):
    model_name = normalize_model_name(model_name)
    if not model_name:
        return True

    supported_models = normalize_supported_models(getattr(account, "supported_models", []))
    if not supported_models:
        return True

    if model_name in supported_models or "*" in supported_models or "all" in supported_models:
        return True

    for pattern in supported_models:
        if pattern.endswith("*") and model_name.startswith(pattern[:-1]):
            return True
    return False


def account_sort_key(account):
    return (
        account.priority,
        HEALTH_SCORE_MAP.get(account.health_status, 99),
        -max(account.weight or 1, 1),
        account.unit_cost,
        account.id or 0,
    )


def get_user_dispatch_block_reason(user):
    if not user or not getattr(user, "is_active", False):
        return "账号已停用"
    if getattr(user, "status", "") in {"disabled", "expired"}:
        return "账号已停用" if getattr(user, "status", "") == "disabled" else "账号已过期"

    expired_date = getattr(user, "expired_date", None)
    if expired_date and expired_date <= timezone.now().date():
        return "账号已过期"
    return ""


def get_dispatch_candidates(user, channel="web", model_name="", only_available=True):
    if get_user_dispatch_block_reason(user):
        return []

    queryset = ChatgptAccount.get_for_user(user, channel=channel, only_available=only_available)
    accounts = [account for account in queryset if account_supports_model(account, model_name)]
    return sorted(accounts, key=account_sort_key)


def save_dispatch_log(
    *,
    user=None,
    account=None,
    entrypoint="",
    channel="web",
    model_name="",
    requested_account_id=None,
    candidate_accounts: Optional[Iterable[ChatgptAccount]] = None,
    decision_status=DispatcherDecisionLog.DECISION_STATUS_SELECTED,
    reason="",
):
    DispatcherDecisionLog.save_data(
        {
            "user": user,
            "account": account,
            "entrypoint": entrypoint,
            "channel": channel,
            "model_name": normalize_model_name(model_name),
            "requested_account_id": requested_account_id,
            "candidate_account_ids": [item.id for item in list(candidate_accounts or [])],
            "decision_status": decision_status,
            "reason": reason,
        }
    )


def select_dispatch_account(
    user,
    *,
    channel="web",
    model_name="",
    requested_account_id=None,
    only_available=True,
    entrypoint="",
    allow_relay=True,
):
    block_reason = get_user_dispatch_block_reason(user)
    if block_reason:
        save_dispatch_log(
            user=user,
            account=None,
            entrypoint=entrypoint,
            channel=channel,
            model_name=model_name,
            requested_account_id=requested_account_id,
            candidate_accounts=[],
            decision_status=DispatcherDecisionLog.DECISION_STATUS_REJECTED,
            reason=block_reason,
        )
        return None

    candidates = get_dispatch_candidates(user, channel=channel, model_name=model_name, only_available=only_available)
    if not allow_relay:
        candidates = [account for account in candidates if not account.is_relay_account]

    if requested_account_id:
        account = next((item for item in candidates if item.id == requested_account_id), None)
        if account:
            save_dispatch_log(
                user=user,
                account=account,
                entrypoint=entrypoint,
                channel=channel,
                model_name=model_name,
                requested_account_id=requested_account_id,
                candidate_accounts=candidates,
                decision_status=DispatcherDecisionLog.DECISION_STATUS_SELECTED,
                reason="requested account accepted",
            )
            return account

        save_dispatch_log(
            user=user,
            account=None,
            entrypoint=entrypoint,
            channel=channel,
            model_name=model_name,
            requested_account_id=requested_account_id,
            candidate_accounts=candidates,
            decision_status=DispatcherDecisionLog.DECISION_STATUS_REJECTED,
            reason="requested account is unavailable for current user/channel/model",
        )
        return None

    account = candidates[0] if candidates else None
    save_dispatch_log(
        user=user,
        account=account,
        entrypoint=entrypoint,
        channel=channel,
        model_name=model_name,
        requested_account_id=None,
        candidate_accounts=candidates,
        decision_status=(
            DispatcherDecisionLog.DECISION_STATUS_SELECTED
            if account
            else DispatcherDecisionLog.DECISION_STATUS_EMPTY
        ),
        reason="auto selected best candidate" if account else "no candidate account matched current request",
    )
    return account

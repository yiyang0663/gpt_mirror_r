from django.db import models
from django.db.models import Q
from django.utils import timezone

from app.accounts.gateway_usage import get_synced_gateway_monthly_request_count, sync_gateway_daily_usage_for_user
from app.accounts.models import GatewayUserDailyUsage, QuotaRule, ServicePlan, UserSubscription
from app.chatgpt.models import ChatgptAccount, UsageLedger


def normalize_model_name(model_name):
    return str(model_name or "").strip().lower()


def model_matches(pattern, model_name):
    pattern = normalize_model_name(pattern)
    model_name = normalize_model_name(model_name)
    if not pattern:
        return True
    if pattern in {"*", "all"}:
        return True
    if not model_name:
        return False
    if pattern == model_name:
        return True
    if pattern.endswith("*") and model_name.startswith(pattern[:-1]):
        return True
    return False


def get_rule_window_start(period):
    now = timezone.now()
    if period == QuotaRule.PERIOD_DAILY:
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return int(start.timestamp())


def build_plan_snapshot(plan):
    if not plan:
        return {}

    return {
        "plan_id": plan.id,
        "plan_name": plan.name,
        "plan_code": plan.code,
        "allow_web": plan.allow_web,
        "allow_api": plan.allow_api,
        "rules": [
            {
                "id": rule.id,
                "model_name": rule.model_name,
                "channel": rule.channel,
                "period": rule.period,
                "request_limit": rule.request_limit,
                "token_limit": rule.token_limit,
                "enabled": rule.enabled,
            }
            for rule in plan.quota_rules.order_by("period", "channel", "id").all()
        ],
    }


def get_active_subscription(user):
    if not user:
        return None

    today = timezone.now().date()
    UserSubscription.objects.filter(
        user=user,
        status=UserSubscription.STATUS_ACTIVE,
        end_date__isnull=False,
        end_date__lt=today,
    ).update(status=UserSubscription.STATUS_EXPIRED)

    return (
        UserSubscription.objects.select_related("service_plan")
        .filter(
            user=user,
            status=UserSubscription.STATUS_ACTIVE,
            start_date__lte=today,
        )
        .filter(Q(end_date__isnull=True) | Q(end_date__gte=today))
        .order_by("-start_date", "-id")
        .first()
    )


def get_user_plan(user):
    subscription = get_active_subscription(user)
    if subscription and subscription.service_plan and subscription.service_plan.is_active:
        return subscription.service_plan

    plan_id = getattr(user, "plan_id", None)
    if not plan_id:
        return None
    return ServicePlan.objects.filter(id=plan_id, is_active=True).first()


def sync_user_plan_snapshot(user, save=True):
    plan = get_user_plan(user)
    user.plan_id = plan.id if plan else None
    user.quota_snapshot = build_plan_snapshot(plan)
    if save:
        user.save(update_fields=["plan_id", "quota_snapshot"])
    return user.quota_snapshot


def assign_service_plan(user, plan=None, start_date=None, end_date=None):
    today = timezone.now().date()
    start_date = start_date or today

    UserSubscription.objects.filter(
        user=user,
        status=UserSubscription.STATUS_ACTIVE,
    ).update(status=UserSubscription.STATUS_CANCELED)

    if not plan:
        user.plan_id = None
        user.quota_snapshot = {}
        user.save(update_fields=["plan_id", "quota_snapshot"])
        return None

    subscription = UserSubscription.objects.create(
        user=user,
        service_plan=plan,
        status=UserSubscription.STATUS_ACTIVE,
        start_date=start_date,
        end_date=end_date,
        quota_snapshot=build_plan_snapshot(plan),
    )
    user.plan_id = plan.id
    user.quota_snapshot = subscription.quota_snapshot
    user.save(update_fields=["plan_id", "quota_snapshot"])
    return subscription


def get_applicable_quota_rules(plan, channel="api", model_name=""):
    if not plan:
        return []

    rules = []
    for rule in plan.quota_rules.filter(enabled=True).order_by("period", "id").all():
        if rule.channel not in {QuotaRule.CHANNEL_ALL, channel}:
            continue
        if not model_matches(rule.model_name, model_name):
            continue
        rules.append(rule)
    return rules


def get_rule_usage(user, rule, channel="api", gateway_daily_request_count=None, gateway_monthly_request_count=None):
    usage_source = "ledger"
    usage_note = ""
    relay_request_count = 0

    if channel == "web" and rule.request_limit and not rule.model_name:
        relay_request_count = UsageLedger.objects.filter(
            user=user,
            account__source_type=ChatgptAccount.SOURCE_TYPE_RELAY,
            request_type="web.chat.completions",
            status_code__gte=200,
            status_code__lt=400,
            created_at__gte=get_rule_window_start(rule.period),
        ).count()

    if channel == "web" and rule.period == QuotaRule.PERIOD_DAILY and rule.request_limit and not rule.model_name:
        return {
            "request_count": int(gateway_daily_request_count or 0) + relay_request_count,
            "total_tokens": 0,
            "usage_source": "gateway_daily_requests_plus_relay",
            "usage_note": "网页全部模型的每日请求次数按 gateway 当日用量 + relay 直连网页请求统计",
        }
    if channel == "web" and rule.period == QuotaRule.PERIOD_MONTHLY and rule.request_limit and not rule.model_name:
        return {
            "request_count": int(gateway_monthly_request_count or 0) + relay_request_count,
            "total_tokens": 0,
            "usage_source": "gateway_monthly_snapshots_plus_relay",
            "usage_note": "网页全部模型的每月请求次数按 gateway 快照累计 + relay 直连网页请求统计",
        }

    queryset = UsageLedger.objects.filter(
        user=user,
        status_code__gte=200,
        status_code__lt=400,
        created_at__gte=get_rule_window_start(rule.period),
    )
    if rule.model_name:
        matched_models = [
            item.model_name
            for item in UsageLedger.objects.filter(
                user=user,
                status_code__gte=200,
                status_code__lt=400,
                created_at__gte=get_rule_window_start(rule.period),
            ).only("model_name")
            if model_matches(rule.model_name, item.model_name)
        ]
        if matched_models:
            queryset = queryset.filter(model_name__in=matched_models)
        else:
            queryset = queryset.none()

    usage = queryset.aggregate(
        request_count=models.Count("id"),
        total_tokens=models.Sum("total_tokens"),
    )
    return {
        "request_count": int(usage["request_count"] or 0),
        "total_tokens": int(usage["total_tokens"] or 0),
        "usage_source": usage_source,
        "usage_note": usage_note,
    }


def build_user_quota_status(user, channel="api", model_name=""):
    plan = get_user_plan(user)
    if not plan:
        return {
            "allowed": True,
            "reason": "",
            "plan": None,
            "rules": [],
            "warnings": [],
        }

    if channel == "api" and not plan.allow_api:
        return {"allowed": False, "reason": "当前套餐未开通 API 调用", "plan": plan, "rules": [], "warnings": []}
    if channel == "web" and not plan.allow_web:
        return {"allowed": False, "reason": "当前套餐未开通网页使用", "plan": plan, "rules": [], "warnings": []}

    applicable_rules = get_applicable_quota_rules(plan, channel=channel, model_name=model_name)
    gateway_daily_request_count = None
    gateway_monthly_request_count = None
    warnings = []
    if channel == "web":
        need_gateway_request_sync = any(
            rule.request_limit and not rule.model_name and rule.period in {QuotaRule.PERIOD_DAILY, QuotaRule.PERIOD_MONTHLY}
            for rule in applicable_rules
        )
        if need_gateway_request_sync:
            try:
                gateway_daily_request_count = sync_gateway_daily_usage_for_user(user)
            except Exception:
                warnings.append("暂时无法同步最新网页用量，当前网页请求统计可能有少量延迟")
                gateway_daily_request_count = int(
                    GatewayUserDailyUsage.objects.filter(user=user, stat_date=timezone.now().date())
                    .values_list("request_count", flat=True)
                    .first() or 0
                )
            gateway_monthly_request_count = get_synced_gateway_monthly_request_count(user)
        if any(rule.token_limit for rule in applicable_rules):
            warnings.append("网页渠道当前未回流 Token 用量，Token 上限暂无法严格校验")
        if any(rule.period == QuotaRule.PERIOD_MONTHLY and rule.request_limit and not rule.model_name for rule in applicable_rules):
            warnings.append("网页月度请求次数按站内同步快照累计，启用前的历史网页请求不会自动补录")
        if any(rule.model_name and rule.request_limit for rule in applicable_rules):
            warnings.append("网页渠道当前没有按模型拆分的用量回流，模型级请求上限暂无法严格校验")

    rules = []
    for rule in applicable_rules:
        usage = get_rule_usage(
            user,
            rule,
            channel=channel,
            gateway_daily_request_count=gateway_daily_request_count,
            gateway_monthly_request_count=gateway_monthly_request_count,
        )
        can_enforce_request_limit = not (
            channel == "web" and (
                (bool(rule.model_name) and rule.request_limit)
            )
        )
        can_enforce_token_limit = not (channel == "web" and rule.token_limit)
        rule_status = {
            "rule_id": rule.id,
            "model_name": rule.model_name,
            "channel": rule.channel,
            "period": rule.period,
            "request_limit": rule.request_limit,
            "token_limit": rule.token_limit,
            "used_requests": usage["request_count"],
            "used_tokens": usage["total_tokens"],
            "remaining_requests": max(rule.request_limit - usage["request_count"], 0) if rule.request_limit else None,
            "remaining_tokens": max(rule.token_limit - usage["total_tokens"], 0) if rule.token_limit else None,
            "usage_source": usage["usage_source"],
            "usage_note": usage["usage_note"],
            "request_limit_enforced": can_enforce_request_limit,
            "token_limit_enforced": can_enforce_token_limit,
        }
        if can_enforce_request_limit and rule.request_limit and usage["request_count"] >= rule.request_limit:
            return {
                "allowed": False,
                "reason": "已达到当前套餐的请求次数上限",
                "plan": plan,
                "rules": rules + [rule_status],
                "warnings": warnings,
            }
        if can_enforce_token_limit and rule.token_limit and usage["total_tokens"] >= rule.token_limit:
            return {
                "allowed": False,
                "reason": "已达到当前套餐的 Token 上限",
                "plan": plan,
                "rules": rules + [rule_status],
                "warnings": warnings,
            }
        rules.append(rule_status)

    return {"allowed": True, "reason": "", "plan": plan, "rules": rules, "warnings": warnings}

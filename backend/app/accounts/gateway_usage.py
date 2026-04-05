from django.db.models import Sum
from django.utils import timezone

from app.accounts.models import GatewayUserDailyUsage, User
from app.settings import ADMIN_USERNAME
from app.utils import req_gateway


def fetch_gateway_user_use_count_map(username_list):
    usernames = [str(item).strip() for item in username_list or [] if str(item).strip()]
    if not usernames:
        return {}

    response = req_gateway("post", "/api/get-user-use-count", json={"username_list": usernames})
    return response if isinstance(response, dict) else {}


def sync_gateway_daily_usage_for_users(users):
    user_list = [user for user in users if getattr(user, "username", "").strip()]
    if not user_list:
        return {}

    usage_map = fetch_gateway_user_use_count_map([user.username for user in user_list])
    today = timezone.now().date()
    synced_counts = {}
    for user in user_list:
        request_count = usage_map.get(user.username)
        if request_count is None:
            continue
        GatewayUserDailyUsage.upsert_snapshot(user, today, request_count)
        synced_counts[user.id] = int(request_count or 0)
    return synced_counts


def sync_gateway_daily_usage_for_user(user):
    if not user:
        return 0
    synced_counts = sync_gateway_daily_usage_for_users([user])
    return int(synced_counts.get(user.id, 0))


def get_active_sync_target_users():
    return list(
        User.objects.filter(is_active=True, status=User.STATUS_ACTIVE)
        .exclude(username=ADMIN_USERNAME)
        .only("id", "username", "email", "quota_snapshot", "pool_mode")
    )


def sync_gateway_daily_usage_for_active_users(batch_size=100):
    active_users = get_active_sync_target_users()
    if not active_users:
        return {
            "active_user_count": 0,
            "synced_user_count": 0,
            "failed_batches": 0,
            "errors": [],
        }

    synced_user_count = 0
    failed_batches = 0
    errors = []
    for start in range(0, len(active_users), batch_size):
        batch = active_users[start:start + batch_size]
        try:
            synced_counts = sync_gateway_daily_usage_for_users(batch)
        except Exception as exc:
            failed_batches += 1
            errors.append(str(exc))
            continue
        synced_user_count += len(synced_counts)

    return {
        "active_user_count": len(active_users),
        "synced_user_count": synced_user_count,
        "failed_batches": failed_batches,
        "errors": errors[:5],
    }


def get_synced_gateway_monthly_request_count(user, current_date=None):
    if not user:
        return 0

    current_date = current_date or timezone.now().date()
    month_start = current_date.replace(day=1)
    result = (
        GatewayUserDailyUsage.objects.filter(user=user, stat_date__gte=month_start, stat_date__lte=current_date)
        .aggregate(total=Sum("request_count"))
    )
    return int(result.get("total") or 0)

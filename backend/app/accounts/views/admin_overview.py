from datetime import datetime, timedelta

from django.db.models import Count, Max, Q, Sum
from django.db.models.functions import Coalesce
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from app.accounts.models import GatewayUserDailyUsage, ServicePlan, User, VisitLog
from app.chatgpt.models import ChatgptAccount, ChatgptCar, DispatcherDecisionLog, UsageLedger


class AdminOverviewView(APIView):
    permission_classes = (IsAuthenticated, IsAdminUser)

    def get(self, request):
        today = datetime.now().date()
        expiring_edge = today + timedelta(days=7)
        today_start = datetime.combine(today, datetime.min.time())
        tomorrow_start = today_start + timedelta(days=1)
        start_ts = int(today_start.timestamp())
        end_ts = int(tomorrow_start.timestamp())

        user_queryset = User.objects.order_by("-date_joined")
        account_queryset = ChatgptAccount.objects.order_by("-updated_time")
        pool_list = list(ChatgptCar.objects.order_by("-updated_time"))
        plan_queryset = ServicePlan.objects.order_by("display_order", "id")
        today_usage_queryset = UsageLedger.objects.filter(created_at__gte=start_ts, created_at__lt=end_ts)
        today_login_queryset = VisitLog.objects.filter(created_at__gte=start_ts, created_at__lt=end_ts).order_by("-created_at")
        today_dispatch_queryset = DispatcherDecisionLog.objects.filter(created_time__gte=start_ts, created_time__lt=end_ts)
        today_sync_queryset = GatewayUserDailyUsage.objects.filter(stat_date=today)

        traffic_summary = today_usage_queryset.aggregate(
            total_requests=Count("id"),
            failed_requests=Count("id", filter=Q(status_code__gte=400) | Q(status_code=0)),
            total_tokens=Coalesce(Sum("total_tokens"), 0),
            estimated_cost=Sum("estimated_cost"),
        )

        sync_summary = today_sync_queryset.aggregate(
            synced_user_count=Count("id"),
            total_requests=Coalesce(Sum("request_count"), 0),
            latest_sync_at=Max("updated_at"),
        )

        recent_users = [
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "status": user.status,
                "is_active": user.is_active,
                "date_joined": user.date_joined.isoformat() if user.date_joined else "",
            }
            for user in user_queryset[:6]
        ]

        recent_accounts = [
            {
                "id": account.id,
                "chatgpt_username": account.chatgpt_username,
                "account_type": account.account_type,
                "source_type": account.source_type,
                "auth_status": account.auth_status,
                "health_status": account.health_status,
                "plan_type": account.plan_type,
                "updated_time": account.updated_time,
            }
            for account in account_queryset[:6]
        ]

        recent_logins = [
            {
                "username": log.username,
                "ip": log.ip,
                "log_type": log.log_type,
                "created_at": log.created_at,
            }
            for log in today_login_queryset[:6]
        ]

        top_models = list(
            today_usage_queryset.exclude(model_name="")
            .values("model_name")
            .annotate(request_count=Count("id"), total_tokens=Coalesce(Sum("total_tokens"), 0))
            .order_by("-request_count", "-total_tokens", "model_name")[:6]
        )

        response_payload = {
            "today": today.isoformat(),
            "users": {
                "total": user_queryset.count(),
                "active": user_queryset.filter(is_active=True).exclude(status__in=[User.STATUS_DISABLED, User.STATUS_EXPIRED]).count(),
                "specific_pool": user_queryset.filter(pool_mode=User.POOL_MODE_SPECIFIC).count(),
                "expiring_soon": user_queryset.filter(
                    expired_date__isnull=False,
                    expired_date__gte=today,
                    expired_date__lte=expiring_edge,
                ).count(),
            },
            "accounts": {
                "total": account_queryset.count(),
                "available": account_queryset.filter(auth_status=True).exclude(health_status=ChatgptAccount.HEALTH_STATUS_DOWN).count(),
                "healthy": account_queryset.filter(health_status=ChatgptAccount.HEALTH_STATUS_HEALTHY).count(),
                "relay": account_queryset.filter(account_type=ChatgptAccount.ACCOUNT_TYPE_RELAY).count(),
                "web_enabled": account_queryset.filter(enabled_for_web=True).count(),
                "api_enabled": account_queryset.filter(enabled_for_api=True).count(),
            },
            "pools": {
                "total": len(pool_list),
                "non_empty": sum(1 for pool in pool_list if pool.gpt_account_list),
                "account_slots": sum(len(pool.gpt_account_list or []) for pool in pool_list),
                "bound_users": user_queryset.filter(pool_mode=User.POOL_MODE_SPECIFIC).count(),
            },
            "plans": {
                "total": plan_queryset.count(),
                "active": plan_queryset.filter(is_active=True).count(),
                "web_enabled": plan_queryset.filter(allow_web=True).count(),
                "api_enabled": plan_queryset.filter(allow_api=True).count(),
            },
            "traffic": {
                "today_requests": traffic_summary["total_requests"] or 0,
                "today_failed_requests": traffic_summary["failed_requests"] or 0,
                "today_total_tokens": traffic_summary["total_tokens"] or 0,
                "today_estimated_cost": float(traffic_summary["estimated_cost"] or 0),
                "today_unique_users": today_usage_queryset.exclude(user_id=None).values("user_id").distinct().count(),
                "today_dispatch_empty": today_dispatch_queryset.filter(
                    decision_status=DispatcherDecisionLog.DECISION_STATUS_EMPTY
                ).count(),
                "top_models": top_models,
            },
            "sync": {
                "synced_user_count": sync_summary["synced_user_count"] or 0,
                "today_request_snapshot": sync_summary["total_requests"] or 0,
                "latest_sync_at": sync_summary["latest_sync_at"] or 0,
                "today_login_count": today_login_queryset.count(),
                "today_dispatch_selected": today_dispatch_queryset.filter(
                    decision_status=DispatcherDecisionLog.DECISION_STATUS_SELECTED
                ).count(),
            },
            "recent_users": recent_users,
            "recent_accounts": recent_accounts,
            "recent_logins": recent_logins,
        }

        return Response(response_payload)

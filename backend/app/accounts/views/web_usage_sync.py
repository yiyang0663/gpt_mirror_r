from django.db.models import Count, Max, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from app.accounts.gateway_usage import sync_gateway_daily_usage_for_active_users
from app.accounts.models import GatewayUserDailyUsage, User
from app.page import DefaultPageNumberPagination
from app.settings import ADMIN_USERNAME


def get_active_user_queryset(request):
    today = timezone.now().date()
    username = str(request.GET.get("username") or "").strip()
    sync_status = str(request.GET.get("sync_status") or "").strip()

    queryset = (
        User.objects.filter(is_active=True, status=User.STATUS_ACTIVE)
        .exclude(username=ADMIN_USERNAME)
        .order_by("-id")
    )
    if username:
        queryset = queryset.filter(username__icontains=username)

    today_user_ids = list(
        GatewayUserDailyUsage.objects.filter(stat_date=today).values_list("user_id", flat=True)
    )
    if sync_status == "synced":
        queryset = queryset.filter(id__in=today_user_ids)
    elif sync_status == "stale":
        queryset = queryset.exclude(id__in=today_user_ids)
    return queryset


class SystemWebUsageSyncSummaryView(APIView):
    permission_classes = (IsAuthenticated, IsAdminUser)

    def get(self, request):
        today = timezone.now().date()
        month_start = today.replace(day=1)
        active_users = User.objects.filter(is_active=True, status=User.STATUS_ACTIVE).exclude(username=ADMIN_USERNAME)
        today_qs = GatewayUserDailyUsage.objects.filter(user__in=active_users, stat_date=today)
        month_qs = GatewayUserDailyUsage.objects.filter(user__in=active_users, stat_date__gte=month_start, stat_date__lte=today)

        active_user_count = active_users.count()
        synced_user_count = today_qs.values("user_id").distinct().count()
        latest_sync_at = today_qs.aggregate(latest=Max("updated_at")).get("latest") or 0

        top_users_today = list(
            today_qs.values("user__username")
            .annotate(request_count=Coalesce(Sum("request_count"), 0))
            .order_by("-request_count", "user__username")[:10]
        )
        top_users_month = list(
            month_qs.values("user__username")
            .annotate(request_count=Coalesce(Sum("request_count"), 0))
            .order_by("-request_count", "user__username")[:10]
        )

        return Response({
            "today": str(today),
            "month_start": str(month_start),
            "active_user_count": active_user_count,
            "synced_user_count": synced_user_count,
            "stale_user_count": max(active_user_count - synced_user_count, 0),
            "sync_ratio": round((synced_user_count / active_user_count) * 100, 2) if active_user_count else 0,
            "latest_sync_at": latest_sync_at,
            "today_total_requests": int(today_qs.aggregate(total=Coalesce(Sum("request_count"), 0)).get("total") or 0),
            "month_total_requests": int(month_qs.aggregate(total=Coalesce(Sum("request_count"), 0)).get("total") or 0),
            "month_snapshot_rows": month_qs.count(),
            "month_snapshot_days": month_qs.values("stat_date").distinct().count(),
            "top_users_today": top_users_today,
            "top_users_month": top_users_month,
        })


class SystemWebUsageSyncDetailView(APIView):
    permission_classes = (IsAuthenticated, IsAdminUser)

    def get(self, request):
        today = timezone.now().date()
        month_start = today.replace(day=1)
        queryset = get_active_user_queryset(request)

        pg = DefaultPageNumberPagination()
        pg.page_size_query_param = "page_size"
        page_users = pg.paginate_queryset(queryset, request=request)
        user_ids = [item.id for item in page_users]

        today_map = {
            item["user_id"]: item
            for item in GatewayUserDailyUsage.objects.filter(user_id__in=user_ids, stat_date=today)
            .values("user_id", "request_count", "updated_at")
        }
        month_map = {
            item["user_id"]: item
            for item in GatewayUserDailyUsage.objects.filter(
                user_id__in=user_ids,
                stat_date__gte=month_start,
                stat_date__lte=today,
            )
            .values("user_id")
            .annotate(
                month_request_count=Coalesce(Sum("request_count"), 0),
                snapshot_days=Count("id"),
                latest_month_sync_at=Max("updated_at"),
            )
        }
        latest_map = {
            item["user_id"]: item
            for item in GatewayUserDailyUsage.objects.filter(user_id__in=user_ids)
            .values("user_id")
            .annotate(
                last_snapshot_date=Max("stat_date"),
                last_synced_at=Max("updated_at"),
            )
        }

        results = []
        for user in page_users:
            today_item = today_map.get(user.id, {})
            month_item = month_map.get(user.id, {})
            latest_item = latest_map.get(user.id, {})
            has_today_snapshot = user.id in today_map
            last_snapshot_date = latest_item.get("last_snapshot_date")
            if has_today_snapshot:
                sync_status = "synced"
            elif last_snapshot_date:
                sync_status = "stale"
            else:
                sync_status = "pending"
            results.append({
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "status": user.status,
                "plan_name": (user.quota_snapshot or {}).get("plan_name", ""),
                "pool_mode": user.pool_mode,
                "today_request_count": int(today_item.get("request_count") or 0),
                "month_request_count": int(month_item.get("month_request_count") or 0),
                "snapshot_days": int(month_item.get("snapshot_days") or 0),
                "today_synced_at": int(today_item.get("updated_at") or 0),
                "last_snapshot_date": str(last_snapshot_date) if last_snapshot_date else "",
                "last_synced_at": int(latest_item.get("last_synced_at") or 0),
                "sync_status": sync_status,
            })

        return pg.get_paginated_response(results)


class SystemWebUsageSyncRunView(APIView):
    permission_classes = (IsAuthenticated, IsAdminUser)

    def post(self, request):
        result = sync_gateway_daily_usage_for_active_users()
        return Response({
            "message": "同步完成",
            **result,
            "sync_time": int(timezone.now().timestamp()),
        })

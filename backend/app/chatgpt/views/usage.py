from datetime import datetime, timedelta

from django.db.models import Count, Q, Sum
from django.db.models.functions import Coalesce
from rest_framework import generics
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from app.accounts.quota import build_user_quota_status
from app.chatgpt.models import UsageLedger
from app.chatgpt.serializers import ShowUsageLedgerSerializer
from app.page import DefaultPageNumberPagination


def to_timestamp_range(date_from, date_to):
    start_ts = None
    end_ts = None

    try:
        if date_from:
            start_dt = datetime.strptime(date_from, "%Y-%m-%d")
            start_ts = int(start_dt.timestamp())
        if date_to:
            end_dt = datetime.strptime(date_to, "%Y-%m-%d") + timedelta(days=1)
            end_ts = int(end_dt.timestamp())
    except ValueError:
        raise ValidationError({"message": "日期格式必须为 YYYY-MM-DD"})

    return start_ts, end_ts


def apply_usage_filters(queryset, request):
    username = str(request.GET.get("username") or "").strip()
    model_name = str(request.GET.get("model_name") or "").strip()
    chatgpt_username = str(request.GET.get("chatgpt_username") or "").strip()
    status_code = str(request.GET.get("status_code") or "").strip()
    date_from = str(request.GET.get("date_from") or "").strip()
    date_to = str(request.GET.get("date_to") or "").strip()

    if username:
        queryset = queryset.filter(user__username__icontains=username)
    if model_name:
        queryset = queryset.filter(model_name__icontains=model_name)
    if chatgpt_username:
        queryset = queryset.filter(account__chatgpt_username__icontains=chatgpt_username)
    if status_code.isdigit():
        queryset = queryset.filter(status_code=int(status_code))
    if date_from or date_to:
        start_ts, end_ts = to_timestamp_range(date_from, date_to)
        if start_ts is not None:
            queryset = queryset.filter(created_at__gte=start_ts)
        if end_ts is not None:
            queryset = queryset.filter(created_at__lt=end_ts)

    return queryset


def build_usage_summary(queryset):
    summary = queryset.aggregate(
        total_requests=Count("id"),
        success_requests=Count("id", filter=Q(status_code__gte=200, status_code__lt=400)),
        failed_requests=Count("id", filter=Q(status_code__gte=400) | Q(status_code=0)),
        prompt_tokens=Coalesce(Sum("prompt_tokens"), 0),
        completion_tokens=Coalesce(Sum("completion_tokens"), 0),
        total_tokens=Coalesce(Sum("total_tokens"), 0),
        estimated_cost=Coalesce(Sum("estimated_cost"), 0),
    )
    summary["estimated_cost"] = float(summary["estimated_cost"] or 0)
    summary["unique_users"] = queryset.exclude(user_id=None).values("user_id").distinct().count()
    summary["unique_accounts"] = queryset.exclude(account_id=None).values("account_id").distinct().count()
    summary["top_models"] = list(
        queryset.exclude(model_name="")
        .values("model_name")
        .annotate(request_count=Count("id"), total_tokens=Coalesce(Sum("total_tokens"), 0))
        .order_by("-request_count", "-total_tokens", "model_name")[:10]
    )
    summary["top_users"] = list(
        queryset.exclude(user_id=None)
        .values("user__username")
        .annotate(request_count=Count("id"), total_tokens=Coalesce(Sum("total_tokens"), 0))
        .order_by("-request_count", "-total_tokens", "user__username")[:10]
    )
    summary["top_accounts"] = list(
        queryset.exclude(account_id=None)
        .values("account__chatgpt_username")
        .annotate(request_count=Count("id"), total_tokens=Coalesce(Sum("total_tokens"), 0))
        .order_by("-request_count", "-total_tokens", "account__chatgpt_username")[:10]
    )
    return summary


class CurrentUserUsageSummaryView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        queryset = apply_usage_filters(UsageLedger.objects.filter(user=request.user).order_by("-id"), request)
        summary = build_usage_summary(queryset)
        quota_status = build_user_quota_status(request.user, channel="api", model_name=request.GET.get("model_name", ""))
        summary["quota_status"] = {
            "allowed": quota_status["allowed"],
            "reason": quota_status["reason"],
            "plan_name": quota_status["plan"].name if quota_status["plan"] else "",
            "plan_code": quota_status["plan"].code if quota_status["plan"] else "",
            "rules": quota_status["rules"],
            "warnings": quota_status.get("warnings", []),
        }
        summary["recent_records"] = ShowUsageLedgerSerializer(instance=queryset[:20], many=True).data
        return Response(summary)


class SystemUsageSummaryView(APIView):
    permission_classes = (IsAuthenticated, IsAdminUser)

    def get(self, request):
        queryset = apply_usage_filters(UsageLedger.objects.order_by("-id"), request)
        return Response(build_usage_summary(queryset))


class SystemUsageDetailView(generics.ListAPIView):
    permission_classes = (IsAuthenticated, IsAdminUser)
    serializer_class = ShowUsageLedgerSerializer
    pagination_class = DefaultPageNumberPagination

    def get_queryset(self):
        queryset = UsageLedger.objects.select_related("user", "account").order_by("-id")
        return apply_usage_filters(queryset, self.request)

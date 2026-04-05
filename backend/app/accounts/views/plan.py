from rest_framework import generics
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from app.accounts.models import ServicePlan, QuotaRule, User
from app.accounts.quota import assign_service_plan, sync_user_plan_snapshot
from app.accounts.serializers import ShowServicePlanSerializer, ServicePlanInputSerializer, AssignUserPlanSerializer
from app.page import DefaultPageNumberPagination


def refresh_plan_users(plan):
    for user in User.objects.filter(plan_id=plan.id).all():
        sync_user_plan_snapshot(user)


class ServicePlanEnumView(APIView):
    permission_classes = (IsAuthenticated, IsAdminUser)

    def get(self, request):
        queryset = ServicePlan.objects.filter(is_active=True).order_by("display_order", "id").values("id", "name", "code")
        return Response({"data": list(queryset)})


class ServicePlanView(generics.ListCreateAPIView):
    permission_classes = (IsAuthenticated, IsAdminUser)

    def get(self, request, *args, **kwargs):
        queryset = ServicePlan.objects.prefetch_related("quota_rules").order_by("display_order", "id")
        pg = DefaultPageNumberPagination()
        pg.page_size_query_param = "page_size"
        page_items = pg.paginate_queryset(queryset, request=request)
        serializer = ShowServicePlanSerializer(instance=page_items, many=True)
        return pg.get_paginated_response(serializer.data)

    def post(self, request, *args, **kwargs):
        serializer = ServicePlanInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        if ServicePlan.objects.filter(name=payload["name"]).exists():
            raise ValidationError({"message": "套餐名称已存在"})
        if ServicePlan.objects.filter(code=payload["code"]).exists():
            raise ValidationError({"message": "套餐编码已存在"})

        plan = ServicePlan.objects.create(
            name=payload["name"],
            code=payload["code"],
            is_active=payload["is_active"],
            allow_web=payload["allow_web"],
            allow_api=payload["allow_api"],
            monthly_price=payload["monthly_price"],
            display_order=payload["display_order"],
            remark=payload["remark"],
        )
        for rule in payload["quota_rules"]:
            QuotaRule.objects.create(service_plan=plan, **rule)

        return Response({"message": "创建套餐成功", "id": plan.id})

    def put(self, request, *args, **kwargs):
        serializer = ServicePlanInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        plan = ServicePlan.objects.filter(id=payload.get("id")).first()
        if not plan:
            raise ValidationError({"message": "套餐不存在"})

        if ServicePlan.objects.filter(name=payload["name"]).exclude(id=plan.id).exists():
            raise ValidationError({"message": "套餐名称已存在"})
        if ServicePlan.objects.filter(code=payload["code"]).exclude(id=plan.id).exists():
            raise ValidationError({"message": "套餐编码已存在"})

        plan.name = payload["name"]
        plan.code = payload["code"]
        plan.is_active = payload["is_active"]
        plan.allow_web = payload["allow_web"]
        plan.allow_api = payload["allow_api"]
        plan.monthly_price = payload["monthly_price"]
        plan.display_order = payload["display_order"]
        plan.remark = payload["remark"]
        plan.save()

        kept_rule_ids = []
        for rule in payload["quota_rules"]:
            rule_id = rule.pop("id", None)
            if rule_id:
                quota_rule = QuotaRule.objects.filter(id=rule_id, service_plan=plan).first()
                if quota_rule:
                    for field, value in rule.items():
                        setattr(quota_rule, field, value)
                    quota_rule.save()
                    kept_rule_ids.append(quota_rule.id)
                    continue
            quota_rule = QuotaRule.objects.create(service_plan=plan, **rule)
            kept_rule_ids.append(quota_rule.id)

        plan.quota_rules.exclude(id__in=kept_rule_ids).delete()
        refresh_plan_users(plan)
        return Response({"message": "更新套餐成功"})

    def delete(self, request, *args, **kwargs):
        plan_id = request.data.get("id")
        plan = ServicePlan.objects.filter(id=plan_id).first()
        if not plan:
            raise ValidationError({"message": "套餐不存在"})

        User.objects.filter(plan_id=plan.id).update(plan_id=None, quota_snapshot={})
        plan.delete()
        return Response({"message": "删除套餐成功"})


class AssignUserPlanView(APIView):
    permission_classes = (IsAuthenticated, IsAdminUser)

    def post(self, request):
        serializer = AssignUserPlanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        user = User.objects.filter(id=payload["user_id"]).first()
        if not user:
            raise ValidationError({"message": "用户不存在"})

        plan = None
        if payload.get("plan_id"):
            plan = ServicePlan.objects.filter(id=payload["plan_id"], is_active=True).first()
            if not plan:
                raise ValidationError({"message": "套餐不存在或未启用"})

        assign_service_plan(
            user,
            plan=plan,
            start_date=payload.get("start_date"),
            end_date=payload.get("end_date"),
        )
        return Response({"message": "分配套餐成功"})

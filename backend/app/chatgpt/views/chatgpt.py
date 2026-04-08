from rest_framework import generics
from django.db.models import Q
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from app.accounts.quota import build_user_quota_status
from app.chatgpt.dispatcher import get_user_dispatch_block_reason, select_dispatch_account
from app.chatgpt.models import ChatgptAccount, ChatgptCar
from app.chatgpt.serializers import ShowChatgptTokenSerializer, AddChatgptTokenSerializer, ChatGPTLoginSerializer, \
    UpdateChatgptInfoSerializer, DeleteChatgptAccountSerializer
from app.page import DefaultPageNumberPagination
from app.utils import save_visit_log, req_gateway, get_client_ip
from rest_framework.exceptions import ValidationError


def parse_bool_query(value):
    value = str(value or "").strip().lower()
    if value in {"1", "true", "yes"}:
        return True
    if value in {"0", "false", "no"}:
        return False
    return None


class ChatGPTAccountEnum(APIView):
    permission_classes = (IsAuthenticated, IsAdminUser)

    def get(self, request):
        result = ChatgptAccount.objects.filter(auth_status=True).order_by("-id").values(
            "id", "chatgpt_username", "plan_type", "health_status", "enabled_for_web", "enabled_for_api"
        ).all()
        return Response({"data": result})


class ChatGPTAccountView(generics.ListCreateAPIView):
    permission_classes = (IsAuthenticated, IsAdminUser)

    def get(self, request, *args, **kwargs):
        queryset = ChatgptAccount.objects.order_by("-id").all()
        search = str(request.GET.get("search") or "").strip()
        account_type = str(request.GET.get("account_type") or "").strip()
        health_status = str(request.GET.get("health_status") or "").strip()
        source_type = str(request.GET.get("source_type") or "").strip()
        auth_status = parse_bool_query(request.GET.get("auth_status"))
        enabled_for_web = parse_bool_query(request.GET.get("enabled_for_web"))
        enabled_for_api = parse_bool_query(request.GET.get("enabled_for_api"))

        if search:
            queryset = queryset.filter(Q(chatgpt_username__icontains=search) | Q(plan_type__icontains=search))
        if account_type:
            queryset = queryset.filter(account_type=account_type)
        if health_status:
            queryset = queryset.filter(health_status=health_status)
        if source_type:
            queryset = queryset.filter(source_type=source_type)
        if auth_status is not None:
            queryset = queryset.filter(auth_status=auth_status)
        if enabled_for_web is not None:
            queryset = queryset.filter(enabled_for_web=enabled_for_web)
        if enabled_for_api is not None:
            queryset = queryset.filter(enabled_for_api=enabled_for_api)

        pg = DefaultPageNumberPagination()
        pg.page_size_query_param = "page_size"
        page_accounts = pg.paginate_queryset(queryset, request=request)
        chatgpt_list = [i.chatgpt_username for i in page_accounts if not i.is_relay_account]

        try:
            use_count_dict = req_gateway("post", "/api/get-chatgpt-use-count", json={"chatgpt_list": chatgpt_list})
        except:
            use_count_dict = {}
        serializer = ShowChatgptTokenSerializer(instance=page_accounts, use_count_dict=use_count_dict, many=True)
        return pg.get_paginated_response(serializer.data)

    def post(self, request, *args, **kwargs):
        # 录入 chatgpt 账号
        serializer = AddChatgptTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if serializer.validated_data["account_type"] == ChatgptAccount.ACCOUNT_TYPE_RELAY:
            try:
                ChatgptAccount.save_relay_data(serializer.validated_data)
            except ValueError as exc:
                raise ValidationError({"message": str(exc)})
            return Response({"message": "录入成功"})

        for chatgpt_token in serializer.validated_data["chatgpt_token_list"]:
            res_json = req_gateway("post", "/api/get-user-info", json={"chatgpt_token": chatgpt_token})
            res_json["auth_status"] = True
            ChatgptAccount.save_data(res_json, serializer.validated_data)

            # 关闭记忆
            chatgpt_name = res_json["user_info"]["email"]
            req_gateway("post", "/api/close-chatgpt-memory", json={"chatgpt_name": chatgpt_name})

        return Response({"message": "录入成功"})

    def put(self, request):
        serializer = UpdateChatgptInfoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ChatgptAccount.objects.filter(chatgpt_username=serializer.validated_data["chatgpt_username"]).update(
            plan_type=serializer.validated_data["plan_type"],
            remark=serializer.validated_data["remark"],
            supported_models=serializer.validated_data["supported_models"],
            priority=serializer.validated_data["priority"],
            weight=serializer.validated_data["weight"],
            health_status=serializer.validated_data["health_status"],
            max_concurrency=serializer.validated_data["max_concurrency"],
            rpm_limit=serializer.validated_data["rpm_limit"],
            tpm_limit=serializer.validated_data["tpm_limit"],
            unit_cost=serializer.validated_data["unit_cost"],
            enabled_for_web=serializer.validated_data["enabled_for_web"],
            enabled_for_api=serializer.validated_data["enabled_for_api"],
        )
        return Response({"message": "更新gpt信息成功"})

    def delete(self, request):
        serializer = DeleteChatgptAccountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        gpt_obj = ChatgptAccount.objects.filter(chatgpt_username=serializer.data["chatgpt_username"]).first()
        if gpt_obj:
            for car_obj in ChatgptCar.objects.filter(gpt_account_list__contains=[gpt_obj.id]).all():
                car_obj.gpt_account_list = [item for item in car_obj.gpt_account_list if item != gpt_obj.id]
                car_obj.save()
            gpt_obj.delete()

        return Response({"message": "删除成功"})


class ChatGPTLoginView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = ChatGPTLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ip = get_client_ip(request)
        block_reason = get_user_dispatch_block_reason(request.user)
        if block_reason:
            raise ValidationError(block_reason)

        requested_chatgpt_id = serializer.validated_data.get("chatgpt_id")
        requested_model = serializer.validated_data.get("model", "")
        quota_status = build_user_quota_status(request.user, channel="web", model_name=requested_model)
        if not quota_status["allowed"]:
            raise ValidationError({
                "message": quota_status["reason"],
                "quota_rules": quota_status["rules"],
            })
        chatgpt = select_dispatch_account(
            request.user,
            channel="web",
            model_name=requested_model,
            requested_account_id=requested_chatgpt_id,
            entrypoint="chatgpt_login",
            allow_relay=False,
        )
        if not chatgpt:
            if requested_chatgpt_id:
                raise ValidationError("该账号不属于当前用户或当前不可用")
            raise ValidationError("当前账号暂未分配可用的网页登录通道")

        user_name = request.user.username + ip if request.user.username == "free_account" else request.user.username
        payload = {
            "user_name": user_name,
            "access_token": chatgpt.access_token,
            "isolated_session": request.user.isolated_session,
            "limits": request.user.model_limit
        }
        # print(payload)
        res_json = req_gateway("post", "/api/login", json=payload)

        save_visit_log(request, "choose-gpt", chatgpt.chatgpt_username)

        return Response(res_json)

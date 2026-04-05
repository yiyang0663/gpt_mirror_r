from rest_framework import generics
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from app.accounts.models import User, VisitLog, ServicePlan
from app.accounts.quota import assign_service_plan, build_user_quota_status, get_user_plan, sync_user_plan_snapshot
from app.accounts.serializers import ShowVisitLogModelSerializer, AddUserAccountSerializer, UserBindChatGPTSerializer, \
    ShowUserAccountModelSerializer, BatchModelLimitSerializer, CurrentUserProfileSerializer
from app.chatgpt.dispatcher import get_dispatch_candidates, save_dispatch_log
from app.chatgpt.models import ChatgptAccount, ChatgptCar, DispatcherDecisionLog
from app.chatgpt.relay import build_account_proxy_token, build_relay_mirror_token
from app.page import DefaultPageNumberPagination
from app.settings import ADMIN_USERNAME
from app.utils import req_gateway
from datetime import datetime


def save_user_pool_bindings(user, pool_ids):
    pool_ids = list(dict.fromkeys(pool_ids))
    user.pool_bindings.exclude(gptcar_id__in=pool_ids).delete()

    existing_ids = set(user.pool_bindings.values_list("gptcar_id", flat=True))
    for pool_id in pool_ids:
        if pool_id not in existing_ids:
            user.pool_bindings.create(gptcar_id=pool_id)


def validate_user_access(user):
    if not user or not user.is_active or user.status == User.STATUS_DISABLED:
        raise ValidationError({"message": "账号已停用"})
    if user.status == User.STATUS_EXPIRED:
        raise ValidationError({"message": "账号已过期"})
    if user.expired_date and user.expired_date <= datetime.now().date():
        raise ValidationError({"message": "账号已过期"})


def build_channel_quota_payload(user, channel="api", model_name=""):
    quota_status = build_user_quota_status(user, channel=channel, model_name=model_name)
    plan = quota_status["plan"]
    return {
        "allowed": quota_status["allowed"],
        "reason": quota_status["reason"],
        "plan_name": plan.name if plan else "",
        "plan_code": plan.code if plan else "",
        "rules": quota_status["rules"],
        "warnings": quota_status.get("warnings", []),
    }


def validate_user_channel_access(user, channel="web", model_name=""):
    validate_user_access(user)
    quota_status = build_user_quota_status(user, channel=channel, model_name=model_name)
    if not quota_status["allowed"]:
        raise ValidationError({
            "message": quota_status["reason"],
            "quota_rules": quota_status["rules"],
        })
    return quota_status


class GetMirrorToken(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        request_user_id = request.GET.get("user_id")
        model_name = request.GET.get("model", "")
        if request_user_id:
            if request.user.username != ADMIN_USERNAME and str(request.user.id) != request_user_id:
                raise ValidationError({"message": "无权查看其他用户的 Token"})
            user = User.objects.filter(id=request_user_id).first()
        else:
            user = request.user

        validate_user_channel_access(user, channel="web", model_name=model_name)

        user_gpt_list = get_dispatch_candidates(user, channel="web", model_name=model_name, only_available=True)
        save_dispatch_log(
            user=user,
            account=user_gpt_list[0] if user_gpt_list else None,
            entrypoint="get_mirror_token",
            channel="web",
            model_name=model_name,
            candidate_accounts=user_gpt_list,
            decision_status="selected" if user_gpt_list else "empty",
            reason="issued ordered mirror token candidates",
        )

        gateway_account_list = [i for i in user_gpt_list if not i.is_relay_account]
        gateway_token_dict = {}

        if gateway_account_list:
            chatgpt_username_list = [i.chatgpt_username for i in gateway_account_list]
            gateway_response = req_gateway("post", "/api/get-mirror-token", json={
                "isolated_session": user.isolated_session,
                "limits": user.model_limit,
                "chatgpt_list": chatgpt_username_list,
                "user_name": user.username,
            })
            gateway_token_dict = {line["chatgpt_username"]: line for line in gateway_response}

        res = []
        for account in user_gpt_list:
            if account.is_relay_account:
                proxy_token = build_relay_mirror_token(user.id, account.id)
                res.append({
                    "id": account.id,
                    "chatgpt_username": account.chatgpt_username,
                    "mirror_token": proxy_token,
                    "proxy_mirror_token": proxy_token,
                    "web_proxy_token": build_relay_mirror_token(user.id, account.id, channel="web"),
                    "auth_status": account.auth_status,
                    "plan_type": account.plan_type,
                    "account_type": account.account_type,
                    "source_type": account.source_type,
                })
                continue

            gateway_item = gateway_token_dict.get(account.chatgpt_username, {})
            res.append({
                "id": account.id,
                "chatgpt_username": account.chatgpt_username,
                "mirror_token": gateway_item.get("mirror_token", ""),
                "proxy_mirror_token": build_account_proxy_token(user.id, account.id),
                "web_proxy_token": build_account_proxy_token(user.id, account.id, channel="web"),
                "auth_status": gateway_item.get("auth_status", account.auth_status),
                "plan_type": account.plan_type,
                "account_type": account.account_type,
                "source_type": account.source_type,
            })
        return Response(res)


class UserChatGPTAccountList(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        model_name = request.GET.get("model", "")
        validate_user_channel_access(request.user, channel="web", model_name=model_name)
        results = []
        user_gpt_list = get_dispatch_candidates(request.user, channel="web", model_name=model_name, only_available=True)
        save_dispatch_log(
            user=request.user,
            account=user_gpt_list[0] if user_gpt_list else None,
            entrypoint="user_chatgpt_list",
            channel="web",
            model_name=model_name,
            candidate_accounts=user_gpt_list,
            decision_status="selected" if user_gpt_list else "empty",
            reason="listed ordered user accounts",
        )
        chatgpt_list = [i.chatgpt_username for i in user_gpt_list if not i.is_relay_account]

        try:
            use_count_dict = req_gateway("post", "/api/get-chatgpt-use-count", json={"chatgpt_list": chatgpt_list})
        except:
            use_count_dict = {}

        auth_user_gpt_list = [i for i in user_gpt_list if i.auth_status]
        current_minute = datetime.now().minute

        for line in auth_user_gpt_list or user_gpt_list:
            if line.is_relay_account:
                results.append({
                    "id": line.id,
                    "use_count": 0,
                    "chatgpt_flag": "{:03}{}".format(line.id, line.chatgpt_username[:3]),
                    "plan_type": line.plan_type,
                    "auth_status": False,
                    "account_type": line.account_type,
                })
                continue

            gpt_use_count_dict = use_count_dict.get(line.chatgpt_username, {}).get("gpt-4o", {})
            last_3h_use_count = (gpt_use_count_dict.get("last_1h", 0) +
                          gpt_use_count_dict.get("last_2h", 0) + gpt_use_count_dict.get("last_3h", 0) +
                          gpt_use_count_dict.get("last_4h", 0) * (1 - current_minute / 60))
            results.append({
                "id": line.id,
                "use_count": last_3h_use_count,
                "chatgpt_flag": "{:03}{}".format(line.id, line.chatgpt_username[:3]),
                "plan_type": line.plan_type,
                "auth_status": line.auth_status,
                "account_type": line.account_type,
            })

        return Response({"results": results})


class CurrentUserProfileView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        validate_user_access(request.user)
        serializer = CurrentUserProfileSerializer(instance=request.user)
        return Response(serializer.data)


class CurrentUserSessionSummaryView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        user = request.user
        validate_user_access(user)
        model_name = request.GET.get("model", "")
        web_accounts = list(ChatgptAccount.get_for_user(user, channel="web", only_available=True))
        api_accounts = list(ChatgptAccount.get_for_user(user, channel="api", only_available=True))
        web_candidates = get_dispatch_candidates(user, channel="web", model_name=model_name, only_available=True)
        api_candidates = get_dispatch_candidates(user, channel="api", model_name=model_name, only_available=True)
        web_quota_status = build_channel_quota_payload(user, channel="web", model_name=model_name)
        api_quota_status = build_channel_quota_payload(user, channel="api", model_name=model_name)
        bound_pools = [
            {
                "id": pool.id,
                "car_name": pool.car_name,
                "account_count": len(pool.gpt_account_list or []),
            }
            for pool in ChatgptCar.objects.filter(id__in=user.get_bound_pool_ids()).order_by("id").all()
        ]

        supported_models = []
        for account in web_accounts:
            for model in account.supported_models or []:
                model = str(model).strip()
                if not model or model in {"*", "all"} or model in supported_models:
                    continue
                supported_models.append(model)
        recent_dispatches = []
        recent_logs = (
            DispatcherDecisionLog.objects.select_related("account")
            .filter(user=user)
            .order_by("-id")[:8]
        )
        for item in recent_logs:
            recent_dispatches.append(
                {
                    "id": item.id,
                    "entrypoint": item.entrypoint,
                    "channel": item.channel,
                    "model_name": item.model_name,
                    "decision_status": item.decision_status,
                    "reason": item.reason,
                    "created_time": item.created_time,
                    "candidate_count": len(item.candidate_account_ids or []),
                    "account": {
                        "id": item.account_id,
                        "chatgpt_username": item.account.chatgpt_username if item.account else "",
                        "account_type": item.account.account_type if item.account else "",
                        "source_type": item.account.source_type if item.account else "",
                        "health_status": item.account.health_status if item.account else "",
                        "plan_type": item.account.plan_type if item.account else "",
                    },
                }
            )

        session_ready = web_quota_status["allowed"] and bool(web_candidates)
        recommended_account = web_candidates[0] if session_ready else None
        session_reason = ""
        if not web_quota_status["allowed"]:
            session_reason = web_quota_status["reason"]
        elif not web_candidates:
            session_reason = "当前账号暂未分配可用的对话通道"

        return Response(
            {
                "available": session_ready,
                "reason": session_reason,
                "pool_mode": user.pool_mode,
                "isolated_session": user.isolated_session,
                "bound_pools": bound_pools,
                "web_quota_status": web_quota_status,
                "api_quota_status": api_quota_status,
                "available_accounts": {
                    "web_total": len(web_accounts),
                    "api_total": len(api_accounts),
                    "web_official": len([item for item in web_accounts if item.source_type == ChatgptAccount.SOURCE_TYPE_OFFICIAL]),
                    "web_relay": len([item for item in web_accounts if item.source_type == ChatgptAccount.SOURCE_TYPE_RELAY]),
                    "api_official": len([item for item in api_accounts if item.source_type == ChatgptAccount.SOURCE_TYPE_OFFICIAL]),
                    "api_relay": len([item for item in api_accounts if item.source_type == ChatgptAccount.SOURCE_TYPE_RELAY]),
                    "web_candidates": len(web_candidates),
                    "api_candidates": len(api_candidates),
                },
                "supported_models": supported_models[:12],
                "recommended_account": (
                    {
                        "id": recommended_account.id,
                        "chatgpt_username": recommended_account.chatgpt_username,
                        "account_type": recommended_account.account_type,
                        "source_type": recommended_account.source_type,
                        "health_status": recommended_account.health_status,
                        "plan_type": recommended_account.plan_type,
                    }
                    if recommended_account
                    else None
                ),
                "recent_dispatches": recent_dispatches,
            }
        )


class BatchModelLimit(APIView):
    permission_classes = (IsAuthenticated, IsAdminUser)

    def post(self, request):
        serializer = BatchModelLimitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        User.objects.filter(id__in=serializer.data["user_id_list"]).update(model_limit=serializer.data["model_limit"])
        return Response({"message": "更新成功"})


class UserRelateGPTCarView(APIView):
    permission_classes = (IsAuthenticated, IsAdminUser)

    def post(self, request, *args, **kwargs):
        serializer = UserBindChatGPTSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        for user_id in serializer.validated_data["user_id_list"]:
            user = User.objects.filter(id=user_id).first()
            if not user:
                continue
            pool_ids = serializer.validated_data["gptcar_id_list"]
            user.pool_mode = User.POOL_MODE_SPECIFIC if pool_ids else User.POOL_MODE_PUBLIC
            user.gptcar_list = pool_ids
            user.save()
            save_user_pool_bindings(user, pool_ids)

        return Response({"message": "绑定成功"})


class UserAccountView(generics.ListCreateAPIView):
    permission_classes = (IsAuthenticated, IsAdminUser)

    def get(self, request, *args, **kwargs):
        queryset = User.objects.order_by("-id").all()
        pg = DefaultPageNumberPagination()
        pg.page_size_query_param = "page_size"
        page_accounts = pg.paginate_queryset(queryset, request=request)
        username_list = [i.username for i in page_accounts]
        try:
            use_count_dict = req_gateway("post", "/api/get-user-use-count", json={"username_list": username_list})
        except:
            use_count_dict = {}
        serializer = ShowUserAccountModelSerializer(instance=page_accounts, use_count_dict=use_count_dict, many=True)
        return pg.get_paginated_response(serializer.data)

    def post(self, request, *args, **kwargs):
        # 添加或更新用户
        serializer = AddUserAccountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        if payload["username"] == ADMIN_USERNAME:
            raise ValidationError({"message": "管理员账号不能操作"})

        user, created = User.objects.get_or_create(username=payload["username"])
        previous_plan = get_user_plan(user)

        if payload.get("password"):
            user.set_password(payload["password"])

        if "expired_date" in payload.keys():
            user.expired_date = payload["expired_date"]

        user.email = payload.get("email", "")
        user.email_verified = payload.get("email_verified", False)
        user.status = payload["status"]
        user.pool_mode = payload["pool_mode"]
        user.plan_id = payload.get("plan_id")
        user.quota_snapshot = payload.get("quota_snapshot", {})
        user.gptcar_list = payload["gptcar_list"]
        user.is_active = payload["is_active"]
        user.model_limit = payload["model_limit"]
        user.isolated_session = payload["isolated_session"]
        user.remark = payload["remark"]
        user.save()
        next_plan_id = payload.get("plan_id")
        previous_plan_id = previous_plan.id if previous_plan else None
        if previous_plan_id != next_plan_id:
            plan = ServicePlan.objects.filter(id=next_plan_id, is_active=True).first() if next_plan_id else None
            assign_service_plan(user, plan=plan)
        else:
            sync_user_plan_snapshot(user)
        save_user_pool_bindings(user, payload["binding_gptcar_list"])

        if not payload["is_active"]:
            # 注销登录
            try:
                req_gateway("post", "/api/logout", json={"user_name": payload["username"]})
            except:
                pass

        return Response({"message": "添加成功"})

    def delete(self, request, *args, **kwargs):
        username = request.data.get("username")
        if username == ADMIN_USERNAME:
            raise ValidationError({"message": "不能删除管理员账号"})
        User.objects.filter(username=username).delete()
        return Response({"message": "删除成功"})


class VisitLogView(generics.ListAPIView):
    permission_classes = (IsAuthenticated, IsAdminUser)
    queryset = VisitLog.objects.order_by("-id").all()
    serializer_class = ShowVisitLogModelSerializer
    pagination_class = DefaultPageNumberPagination

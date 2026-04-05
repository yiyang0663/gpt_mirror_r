from rest_framework import serializers

from app.accounts.models import User, VisitLog, ServicePlan, QuotaRule, UserSubscription
from app.accounts.quota import build_user_quota_status
from app.chatgpt.models import ChatgptAccount
from app.utils import clean_int_list


class ShowVisitLogModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = VisitLog
        fields = "__all__"


class ShowUserAccountModelSerializer(serializers.ModelSerializer):
    last_login = serializers.DateTimeField(format="%Y-%m-%d %H:%M", allow_null=True)
    date_joined = serializers.DateTimeField(format="%Y-%m-%d %H:%M")
    use_count = serializers.SerializerMethodField()
    chatgpt_count = serializers.SerializerMethodField()
    binding_gptcar_list = serializers.SerializerMethodField()
    plan_name = serializers.SerializerMethodField()

    def __init__(self, *args, use_count_dict=dict, **kwargs):
        super().__init__(*args, **kwargs)
        self.use_count_dict = use_count_dict

    def get_chatgpt_count(self, obj):
        return ChatgptAccount.get_for_user(obj, channel="web", only_available=True).count()

    def get_use_count(self, obj):
        return self.use_count_dict.get(obj.username, 0)

    def get_binding_gptcar_list(self, obj):
        return obj.get_bound_pool_ids()

    def get_plan_name(self, obj):
        snapshot = obj.quota_snapshot or {}
        if snapshot.get("plan_name"):
            return snapshot.get("plan_name")
        if not obj.plan_id:
            return ""
        plan = ServicePlan.objects.filter(id=obj.plan_id).first()
        return plan.name if plan else ""

    class Meta:
        model = User
        exclude = (
            "password", "is_superuser", "first_name", "last_name", "is_staff", "groups", "user_permissions")


class CurrentUserProfileSerializer(serializers.ModelSerializer):
    binding_gptcar_list = serializers.SerializerMethodField()
    available_account_count = serializers.SerializerMethodField()
    plan_name = serializers.SerializerMethodField()
    plan_code = serializers.SerializerMethodField()
    quota_status = serializers.SerializerMethodField()
    last_login = serializers.DateTimeField(format="%Y-%m-%d %H:%M", allow_null=True)
    date_joined = serializers.DateTimeField(format="%Y-%m-%d %H:%M")

    def get_binding_gptcar_list(self, obj):
        return obj.get_bound_pool_ids()

    def get_available_account_count(self, obj):
        return ChatgptAccount.get_for_user(obj, channel="web", only_available=True).count()

    def get_plan_name(self, obj):
        return (obj.quota_snapshot or {}).get("plan_name", "")

    def get_plan_code(self, obj):
        return (obj.quota_snapshot or {}).get("plan_code", "")

    def get_quota_status(self, obj):
        status = build_user_quota_status(obj, channel="api")
        return {
            "allowed": status["allowed"],
            "reason": status["reason"],
            "rules": status["rules"],
            "warnings": status.get("warnings", []),
        }

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "email_verified",
            "status",
            "pool_mode",
            "plan_id",
            "plan_name",
            "plan_code",
            "quota_snapshot",
            "quota_status",
            "remark",
            "isolated_session",
            "expired_date",
            "last_login",
            "date_joined",
            "binding_gptcar_list",
            "available_account_count",
        )


class AddUserAccountSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False)
    is_active = serializers.BooleanField()
    status = serializers.ChoiceField(choices=[item[0] for item in User.STATUS_CHOICES], default=User.STATUS_ACTIVE)
    username = serializers.CharField(min_length=4)
    password = serializers.CharField(required=False)
    email = serializers.EmailField(required=False, allow_blank=True, default="")
    email_verified = serializers.BooleanField(required=False, default=False)
    pool_mode = serializers.ChoiceField(choices=[item[0] for item in User.POOL_MODE_CHOICES], default=User.POOL_MODE_PUBLIC)
    binding_gptcar_list = serializers.JSONField(default=list)
    gptcar_list = serializers.JSONField(default=list)
    plan_id = serializers.IntegerField(required=False, allow_null=True)
    quota_snapshot = serializers.JSONField(default=dict)
    model_limit = serializers.JSONField(default=list)
    remark = serializers.CharField(default="", allow_blank=True)
    isolated_session = serializers.BooleanField()
    expired_date = serializers.DateField(required=False, allow_null=True)

    def validate(self, attrs):
        binding_gptcar_list = clean_int_list(attrs.get("binding_gptcar_list", []))
        legacy_gptcar_list = clean_int_list(attrs.get("gptcar_list", []))
        if not binding_gptcar_list:
            binding_gptcar_list = legacy_gptcar_list

        if attrs["pool_mode"] == User.POOL_MODE_SPECIFIC and not binding_gptcar_list:
            raise serializers.ValidationError({"binding_gptcar_list": "指定号池模式下必须至少绑定一个号池"})
        plan_id = attrs.get("plan_id")
        if plan_id and not ServicePlan.objects.filter(id=plan_id, is_active=True).exists():
            raise serializers.ValidationError({"plan_id": "套餐不存在或未启用"})

        attrs["binding_gptcar_list"] = binding_gptcar_list
        attrs["gptcar_list"] = binding_gptcar_list
        return attrs


class BatchModelLimitSerializer(serializers.Serializer):
    user_id_list = serializers.ListField(child=serializers.IntegerField())
    model_limit = serializers.JSONField()


class UserBindChatGPTSerializer(serializers.Serializer):
    user_id_list = serializers.ListField(child=serializers.IntegerField())
    gptcar_id_list = serializers.ListField(child=serializers.IntegerField())


class UserRegisterSerializer(serializers.Serializer):
    username = serializers.CharField(min_length=4)
    email = serializers.EmailField()
    password = serializers.CharField()


class ShowQuotaRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuotaRule
        fields = (
            "id",
            "model_name",
            "channel",
            "period",
            "request_limit",
            "token_limit",
            "enabled",
            "remark",
        )


class ShowServicePlanSerializer(serializers.ModelSerializer):
    quota_rules = ShowQuotaRuleSerializer(many=True, read_only=True)
    subscription_count = serializers.SerializerMethodField()

    def get_subscription_count(self, obj):
        return obj.subscriptions.filter(status=UserSubscription.STATUS_ACTIVE).count()

    class Meta:
        model = ServicePlan
        fields = (
            "id",
            "name",
            "code",
            "is_active",
            "allow_web",
            "allow_api",
            "monthly_price",
            "display_order",
            "remark",
            "subscription_count",
            "quota_rules",
            "created_at",
            "updated_at",
        )


class QuotaRuleInputSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False)
    model_name = serializers.CharField(required=False, allow_blank=True, default="")
    channel = serializers.ChoiceField(choices=[item[0] for item in QuotaRule.CHANNEL_CHOICES], default=QuotaRule.CHANNEL_ALL)
    period = serializers.ChoiceField(choices=[item[0] for item in QuotaRule.PERIOD_CHOICES], default=QuotaRule.PERIOD_MONTHLY)
    request_limit = serializers.IntegerField(required=False, default=0)
    token_limit = serializers.IntegerField(required=False, default=0)
    enabled = serializers.BooleanField(required=False, default=True)
    remark = serializers.CharField(required=False, allow_blank=True, default="")

    def validate(self, attrs):
        if attrs["request_limit"] < 0:
            raise serializers.ValidationError({"request_limit": "请求上限不能小于 0"})
        if attrs["token_limit"] < 0:
            raise serializers.ValidationError({"token_limit": "Token 上限不能小于 0"})
        attrs["model_name"] = attrs.get("model_name", "").strip()
        return attrs


class ServicePlanInputSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False)
    name = serializers.CharField()
    code = serializers.CharField()
    is_active = serializers.BooleanField(required=False, default=True)
    allow_web = serializers.BooleanField(required=False, default=True)
    allow_api = serializers.BooleanField(required=False, default=True)
    monthly_price = serializers.DecimalField(required=False, max_digits=10, decimal_places=2, default="0")
    display_order = serializers.IntegerField(required=False, default=100)
    remark = serializers.CharField(required=False, allow_blank=True, default="")
    quota_rules = serializers.ListField(child=serializers.DictField(), required=False, default=list)

    def validate(self, attrs):
        if attrs["display_order"] < 0:
            raise serializers.ValidationError({"display_order": "排序不能小于 0"})

        normalized_rules = []
        for item in attrs.get("quota_rules", []):
            serializer = QuotaRuleInputSerializer(data=item)
            serializer.is_valid(raise_exception=True)
            normalized_rules.append(serializer.validated_data)
        attrs["quota_rules"] = normalized_rules
        attrs["name"] = attrs["name"].strip()
        attrs["code"] = attrs["code"].strip()
        return attrs


class AssignUserPlanSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    plan_id = serializers.IntegerField(required=False, allow_null=True)
    start_date = serializers.DateField(required=False, allow_null=True)
    end_date = serializers.DateField(required=False, allow_null=True)

    def validate(self, attrs):
        start_date = attrs.get("start_date")
        end_date = attrs.get("end_date")
        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError({"end_date": "结束时间不能早于开始时间"})
        return attrs

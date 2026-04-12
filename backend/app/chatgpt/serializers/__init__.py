from rest_framework import serializers

from app.chatgpt.content_blocks import extract_text_from_content_blocks, normalize_chat_content_blocks
from app.chatgpt.models import (
    ChatConversation,
    ChatConversationMessage,
    ChatgptAccount,
    ChatgptCar,
    UsageLedger,
)
import jwt
from app.utils import clean_int_list
import time


def normalize_string_list(values):
    if values is None:
        return []
    if isinstance(values, str):
        values = [item.strip() for item in values.split(",")]
    if not isinstance(values, list):
        raise serializers.ValidationError("必须是字符串数组")
    return [str(item).strip() for item in values if str(item).strip()]

class ShowGptCarSerializer(serializers.ModelSerializer):
    gpt_account_name_list = serializers.SerializerMethodField()

    def get_gpt_account_name_list(self, obj):
        gpt_account_list = clean_int_list(obj.gpt_account_list)
        resutls = ChatgptAccount.objects.filter(id__in=gpt_account_list).values_list("chatgpt_username")
        return [i[0] for i in resutls]

    class Meta:
        model = ChatgptCar
        fields = "__all__"

class AddChatgptCarModelSerializer(serializers.ModelSerializer):

    def validate_empty_values(self, data):
        if not self.instance:
            data["created_time"] = int(time.time())

        data["updated_time"] = int(time.time())
        return (False, data)

    class Meta:
        model = ChatgptCar
        fields = "__all__"

class DeleteChatgptCarSerializer(serializers.Serializer):
    ids = serializers.ListField(child=serializers.IntegerField())


class ShowChatgptTokenSerializer(serializers.ModelSerializer):
    access_token_exp = serializers.SerializerMethodField()
    use_count = serializers.SerializerMethodField()
    auth_mode = serializers.SerializerMethodField()

    def __init__(self, *args, use_count_dict=dict, **kwargs):
        super().__init__(*args, **kwargs)
        self.use_count_dict = use_count_dict

    def get_use_count(self, obj):
        return self.use_count_dict.get(obj.chatgpt_username, 0)

    def get_access_token_exp(self, obj):
        try:
            access_token_exp = jwt.decode(obj.access_token, options={"verify_signature": False})["exp"]
        except Exception:
            access_token_exp = 0
        return access_token_exp

    def get_auth_mode(self, obj):
        return obj.auth_mode

    class Meta:
        model = ChatgptAccount
        fields = "__all__"


class AddChatgptTokenSerializer(serializers.Serializer):
    account_type = serializers.ChoiceField(
        choices=[ChatgptAccount.ACCOUNT_TYPE_CHATGPT, ChatgptAccount.ACCOUNT_TYPE_RELAY],
        default=ChatgptAccount.ACCOUNT_TYPE_CHATGPT,
    )
    chatgpt_token_list = serializers.ListField(child=serializers.CharField(allow_blank=True), required=False, default=list)
    chatgpt_username = serializers.CharField(required=False, allow_blank=True)
    relay_base_url = serializers.URLField(required=False, allow_blank=True)
    relay_api_key = serializers.CharField(required=False, allow_blank=True)
    plan_type = serializers.CharField(required=False, allow_blank=True, default="relay")
    remark = serializers.CharField(required=False, allow_blank=True, default="")
    supported_models = serializers.JSONField(required=False, default=list)
    priority = serializers.IntegerField(required=False, default=100)
    weight = serializers.IntegerField(required=False, default=1)
    health_status = serializers.ChoiceField(
        choices=[item[0] for item in ChatgptAccount.HEALTH_STATUS_CHOICES],
        required=False,
        default=ChatgptAccount.HEALTH_STATUS_HEALTHY,
    )
    max_concurrency = serializers.IntegerField(required=False, default=1)
    rpm_limit = serializers.IntegerField(required=False, default=0)
    tpm_limit = serializers.IntegerField(required=False, default=0)
    unit_cost = serializers.DecimalField(required=False, max_digits=10, decimal_places=4, default="0")
    enabled_for_web = serializers.BooleanField(required=False, default=True)
    enabled_for_api = serializers.BooleanField(required=False, default=True)

    def validate(self, attrs):
        attrs["supported_models"] = normalize_string_list(attrs.get("supported_models", []))
        if attrs["priority"] < 0:
            raise serializers.ValidationError({"priority": "优先级不能小于 0"})
        if attrs["weight"] <= 0:
            raise serializers.ValidationError({"weight": "权重必须大于 0"})
        if attrs["max_concurrency"] <= 0:
            raise serializers.ValidationError({"max_concurrency": "最大并发必须大于 0"})
        if attrs["rpm_limit"] < 0:
            raise serializers.ValidationError({"rpm_limit": "RPM 不能小于 0"})
        if attrs["tpm_limit"] < 0:
            raise serializers.ValidationError({"tpm_limit": "TPM 不能小于 0"})

        if attrs["account_type"] == ChatgptAccount.ACCOUNT_TYPE_RELAY:
            if not attrs.get("chatgpt_username"):
                raise serializers.ValidationError({"chatgpt_username": "中转站账号标识不能为空"})
            if not attrs.get("relay_base_url"):
                raise serializers.ValidationError({"relay_base_url": "中转站 URL 不能为空"})
            if not attrs.get("relay_api_key"):
                raise serializers.ValidationError({"relay_api_key": "中转站 Key 不能为空"})
            return attrs

        token_list = [item.strip() for item in attrs.get("chatgpt_token_list", []) if item.strip()]
        if not token_list:
            raise serializers.ValidationError({"chatgpt_token_list": "Token 不能为空"})

        attrs["chatgpt_token_list"] = token_list
        return attrs

class DeleteChatgptAccountSerializer(serializers.Serializer):
    chatgpt_username = serializers.CharField()

class UpdateChatgptInfoSerializer(serializers.Serializer):
    chatgpt_username = serializers.CharField()
    plan_type = serializers.CharField(required=False, allow_blank=True, default="")
    remark = serializers.CharField(required=False, allow_blank=True, default="")
    supported_models = serializers.JSONField(required=False, default=list)
    priority = serializers.IntegerField(required=False, default=100)
    weight = serializers.IntegerField(required=False, default=1)
    health_status = serializers.ChoiceField(
        choices=[item[0] for item in ChatgptAccount.HEALTH_STATUS_CHOICES],
        required=False,
        default=ChatgptAccount.HEALTH_STATUS_HEALTHY,
    )
    max_concurrency = serializers.IntegerField(required=False, default=1)
    rpm_limit = serializers.IntegerField(required=False, default=0)
    tpm_limit = serializers.IntegerField(required=False, default=0)
    unit_cost = serializers.DecimalField(required=False, max_digits=10, decimal_places=4, default="0")
    enabled_for_web = serializers.BooleanField(required=False, default=True)
    enabled_for_api = serializers.BooleanField(required=False, default=True)

    def validate(self, attrs):
        attrs["supported_models"] = normalize_string_list(attrs.get("supported_models", []))
        if attrs["priority"] < 0:
            raise serializers.ValidationError({"priority": "优先级不能小于 0"})
        if attrs["weight"] <= 0:
            raise serializers.ValidationError({"weight": "权重必须大于 0"})
        if attrs["max_concurrency"] <= 0:
            raise serializers.ValidationError({"max_concurrency": "最大并发必须大于 0"})
        if attrs["rpm_limit"] < 0:
            raise serializers.ValidationError({"rpm_limit": "RPM 不能小于 0"})
        if attrs["tpm_limit"] < 0:
            raise serializers.ValidationError({"tpm_limit": "TPM 不能小于 0"})
        return attrs


class ChatGPTLoginSerializer(serializers.Serializer):
    chatgpt_id = serializers.IntegerField(required=False, allow_null=True)
    model = serializers.CharField(required=False, allow_blank=True, default="")


class ShowUsageLedgerSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()
    chatgpt_username = serializers.SerializerMethodField()
    account_type = serializers.SerializerMethodField()
    source_type = serializers.SerializerMethodField()

    def get_username(self, obj):
        return obj.user.username if obj.user else ""

    def get_chatgpt_username(self, obj):
        return obj.account.chatgpt_username if obj.account else ""

    def get_account_type(self, obj):
        return obj.account.account_type if obj.account else ""

    def get_source_type(self, obj):
        return obj.account.source_type if obj.account else ""

    class Meta:
        model = UsageLedger
        fields = (
            "id",
            "username",
            "chatgpt_username",
            "account_type",
            "source_type",
            "model_name",
            "request_type",
            "prompt_tokens",
            "completion_tokens",
            "total_tokens",
            "estimated_cost",
            "status_code",
            "error_code",
            "created_at",
        )


class ShowChatConversationMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatConversationMessage
        fields = (
            "id",
            "role",
            "content",
            "content_blocks",
            "account_label",
            "sequence",
            "created_time",
            "updated_time",
        )


class ShowChatConversationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatConversation
        fields = (
            "id",
            "title",
            "model_name",
            "reasoning_effort",
            "preview_text",
            "message_count",
            "last_message_at",
            "created_time",
            "updated_time",
        )


class ShowChatConversationDetailSerializer(ShowChatConversationSerializer):
    messages = ShowChatConversationMessageSerializer(many=True, read_only=True)

    class Meta(ShowChatConversationSerializer.Meta):
        fields = ShowChatConversationSerializer.Meta.fields + ("messages",)


class CreateChatConversationSerializer(serializers.Serializer):
    title = serializers.CharField(required=False, allow_blank=True, default="")
    model_name = serializers.CharField(required=False, allow_blank=True, default="")
    reasoning_effort = serializers.CharField(required=False, allow_blank=True, default="")


class SyncChatConversationMessageSerializer(serializers.Serializer):
    role = serializers.ChoiceField(
        choices=[
            ChatConversationMessage.ROLE_USER,
            ChatConversationMessage.ROLE_ASSISTANT,
            ChatConversationMessage.ROLE_SYSTEM,
        ]
    )
    content = serializers.CharField(required=False, allow_blank=True, default="")
    content_blocks = serializers.JSONField(required=False, default=list)
    account_label = serializers.CharField(required=False, allow_blank=True, default="")

    def validate(self, attrs):
        normalized_blocks = normalize_chat_content_blocks(
            attrs.get("content_blocks", []),
            fallback_text=attrs.get("content", ""),
        )
        attrs["content_blocks"] = normalized_blocks
        attrs["content"] = extract_text_from_content_blocks(normalized_blocks)
        return attrs


class SyncChatConversationSerializer(serializers.Serializer):
    title = serializers.CharField(required=False, allow_blank=True, default="")
    model_name = serializers.CharField(required=False, allow_blank=True, default="")
    reasoning_effort = serializers.CharField(required=False, allow_blank=True, default="")
    messages = SyncChatConversationMessageSerializer(many=True, required=False, default=list)

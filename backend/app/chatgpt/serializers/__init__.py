from rest_framework import serializers

from app.chatgpt.models import ChatgptAccount, ChatgptCar
import jwt
from app.utils import clean_int_list
import time

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

    def validate(self, attrs):
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
    remark = serializers.CharField()


class ChatGPTLoginSerializer(serializers.Serializer):
    chatgpt_id = serializers.IntegerField()

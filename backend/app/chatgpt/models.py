import time

from django.db import models


class ChatgptCar(models.Model):
    car_name = models.CharField(unique=True, max_length=32)
    remark = models.CharField(max_length=128, blank=True, verbose_name="备注")
    gpt_account_list = models.JSONField(default=list)
    created_time = models.IntegerField(db_index=True, blank=True, verbose_name="创建时间")
    updated_time = models.IntegerField(db_index=True, blank=True, verbose_name="最后修改时间")


class ChatgptAccount(models.Model):
    ACCOUNT_TYPE_CHATGPT = "chatgpt_token"
    ACCOUNT_TYPE_RELAY = "relay_api"
    ACCOUNT_TYPE_CHOICES = (
        (ACCOUNT_TYPE_CHATGPT, "ChatGPT Token"),
        (ACCOUNT_TYPE_RELAY, "Relay URL + Key"),
    )

    chatgpt_username = models.CharField(max_length=64, unique=True)
    account_type = models.CharField(max_length=32, choices=ACCOUNT_TYPE_CHOICES, default=ACCOUNT_TYPE_CHATGPT)
    auth_status = models.BooleanField(default=True, verbose_name="授权状态")
    plan_type = models.CharField(max_length=32)
    access_token = models.TextField(blank=True)
    session_token = models.TextField(null=True, blank=True)
    refresh_token = models.TextField(null=True, blank=True)
    relay_base_url = models.URLField(null=True, blank=True)
    relay_api_key = models.TextField(null=True, blank=True)
    remark = models.TextField(null=True, blank=True, verbose_name="备注")
    created_time = models.IntegerField(db_index=True, blank=True, verbose_name="创建时间")
    updated_time = models.IntegerField(db_index=True, blank=True, verbose_name="最后修改时间")

    @property
    def is_relay_account(self):
        return self.account_type == self.ACCOUNT_TYPE_RELAY

    @property
    def auth_mode(self):
        if self.is_relay_account:
            return "relay_url_key"
        if self.refresh_token:
            return "refresh_token"
        if self.session_token:
            return "session_token"
        return "access_token"

    @classmethod
    def get_by_gptcar_list(cls, gptcar_list):
        chatgpt_account_list = []
        for line in ChatgptCar.objects.filter(id__in=gptcar_list).values("gpt_account_list"):
            chatgpt_account_list.extend(line["gpt_account_list"])

        gptaccount = ChatgptAccount.objects
        if gptcar_list:
            gptaccount = gptaccount.filter(id__in=chatgpt_account_list)

        return gptaccount.order_by("-plan_type", "-id").all()


    @classmethod
    def get_by_id(cls, chatgpt_id):
        return cls.objects.filter(id=chatgpt_id).first()

    @classmethod
    def save_data(cls, data):
        obj = cls.objects.filter(chatgpt_username=data["user_info"]["email"]).first()
        new_obj = obj or cls()
        new_obj.chatgpt_username = data["user_info"]["email"]
        new_obj.account_type = cls.ACCOUNT_TYPE_CHATGPT
        new_obj.plan_type = data["user_info"]["plan_type"]
        new_obj.access_token = data["access_token"]
        new_obj.relay_base_url = None
        new_obj.relay_api_key = None

        if data.get("auth_status") is not None:
            new_obj.auth_status = data["auth_status"]

        if data.get("session_token"):
            new_obj.session_token = data["session_token"]
            new_obj.refresh_token = None

        if data.get("refresh_token"):
            new_obj.refresh_token = data["refresh_token"]
            new_obj.session_token = None


        new_obj.updated_time = int(time.time())

        if not obj:
            new_obj.created_time = int(time.time())

        new_obj.save()
        return new_obj.id

    @classmethod
    def save_relay_data(cls, data):
        obj = cls.objects.filter(chatgpt_username=data["chatgpt_username"]).first()
        if obj and obj.account_type != cls.ACCOUNT_TYPE_RELAY:
            raise ValueError("账号标识已存在，且不是中转站账号")

        new_obj = obj or cls()
        now = int(time.time())
        new_obj.chatgpt_username = data["chatgpt_username"]
        new_obj.account_type = cls.ACCOUNT_TYPE_RELAY
        new_obj.auth_status = data.get("auth_status", True)
        new_obj.plan_type = data.get("plan_type") or "relay"
        new_obj.access_token = ""
        new_obj.session_token = None
        new_obj.refresh_token = None
        new_obj.relay_base_url = data["relay_base_url"].rstrip("/")
        new_obj.relay_api_key = data["relay_api_key"]
        new_obj.remark = data.get("remark", "")
        new_obj.updated_time = now

        if not obj:
            new_obj.created_time = now

        new_obj.save()
        return new_obj.id

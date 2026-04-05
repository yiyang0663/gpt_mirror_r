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
    SOURCE_TYPE_OFFICIAL = "official"
    SOURCE_TYPE_RELAY = "relay"
    SOURCE_TYPE_CHOICES = (
        (SOURCE_TYPE_OFFICIAL, "官方账号"),
        (SOURCE_TYPE_RELAY, "中转站"),
    )
    HEALTH_STATUS_HEALTHY = "healthy"
    HEALTH_STATUS_DEGRADED = "degraded"
    HEALTH_STATUS_DOWN = "down"
    HEALTH_STATUS_CHOICES = (
        (HEALTH_STATUS_HEALTHY, "健康"),
        (HEALTH_STATUS_DEGRADED, "降级"),
        (HEALTH_STATUS_DOWN, "停用"),
    )

    chatgpt_username = models.CharField(max_length=64, unique=True)
    account_type = models.CharField(max_length=32, choices=ACCOUNT_TYPE_CHOICES, default=ACCOUNT_TYPE_CHATGPT)
    source_type = models.CharField(max_length=32, choices=SOURCE_TYPE_CHOICES, default=SOURCE_TYPE_OFFICIAL)
    auth_status = models.BooleanField(default=True, verbose_name="授权状态")
    health_status = models.CharField(max_length=32, choices=HEALTH_STATUS_CHOICES, default=HEALTH_STATUS_HEALTHY)
    plan_type = models.CharField(max_length=32)
    supported_models = models.JSONField(default=list)
    priority = models.IntegerField(default=100)
    weight = models.IntegerField(default=1)
    max_concurrency = models.PositiveIntegerField(default=1)
    rpm_limit = models.PositiveIntegerField(default=0)
    tpm_limit = models.PositiveIntegerField(default=0)
    unit_cost = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    enabled_for_web = models.BooleanField(default=True)
    enabled_for_api = models.BooleanField(default=True)
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
        if not gptcar_list:
            return cls.objects.none()

        chatgpt_account_list = []
        for line in ChatgptCar.objects.filter(id__in=gptcar_list).values("gpt_account_list"):
            chatgpt_account_list.extend(line["gpt_account_list"])

        return cls.objects.filter(id__in=chatgpt_account_list).order_by("-plan_type", "-id").all()

    @classmethod
    def get_for_user(cls, user, channel=None, only_available=False):
        if not user:
            return cls.objects.none()

        if getattr(user, "pool_mode", "public_pool") == "specific_pools":
            queryset = cls.get_by_gptcar_list(user.get_bound_pool_ids())
        else:
            queryset = cls.objects.order_by("-plan_type", "-id").all()

        if channel == "web":
            queryset = queryset.filter(enabled_for_web=True)
        elif channel == "api":
            queryset = queryset.filter(enabled_for_api=True)

        if only_available:
            queryset = queryset.filter(auth_status=True).exclude(health_status=cls.HEALTH_STATUS_DOWN)

        return queryset

    @classmethod
    def apply_metadata(cls, obj, metadata=None):
        metadata = metadata or {}
        obj.source_type = metadata.get("source_type") or (
            cls.SOURCE_TYPE_RELAY if obj.account_type == cls.ACCOUNT_TYPE_RELAY else cls.SOURCE_TYPE_OFFICIAL
        )
        obj.health_status = metadata.get("health_status", obj.health_status or cls.HEALTH_STATUS_HEALTHY)
        obj.supported_models = metadata.get("supported_models", obj.supported_models or [])
        obj.priority = metadata.get("priority", obj.priority or 100)
        obj.weight = metadata.get("weight", obj.weight or 1)
        obj.max_concurrency = metadata.get("max_concurrency", obj.max_concurrency or 1)
        obj.rpm_limit = metadata.get("rpm_limit", obj.rpm_limit or 0)
        obj.tpm_limit = metadata.get("tpm_limit", obj.tpm_limit or 0)
        obj.unit_cost = metadata.get("unit_cost", obj.unit_cost or 0)
        obj.enabled_for_web = metadata.get("enabled_for_web", obj.enabled_for_web if obj.pk else True)
        obj.enabled_for_api = metadata.get("enabled_for_api", obj.enabled_for_api if obj.pk else True)
        obj.remark = metadata.get("remark", obj.remark or "")
        plan_type = metadata.get("plan_type")
        if plan_type:
            obj.plan_type = plan_type


    @classmethod
    def get_by_id(cls, chatgpt_id):
        return cls.objects.filter(id=chatgpt_id).first()

    @classmethod
    def save_data(cls, data, metadata=None):
        obj = cls.objects.filter(chatgpt_username=data["user_info"]["email"]).first()
        new_obj = obj or cls()
        new_obj.chatgpt_username = data["user_info"]["email"]
        new_obj.account_type = cls.ACCOUNT_TYPE_CHATGPT
        new_obj.source_type = cls.SOURCE_TYPE_OFFICIAL
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

        cls.apply_metadata(new_obj, metadata)

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
        new_obj.source_type = cls.SOURCE_TYPE_RELAY
        new_obj.auth_status = data.get("auth_status", True)
        new_obj.plan_type = data.get("plan_type") or "relay"
        new_obj.access_token = ""
        new_obj.session_token = None
        new_obj.refresh_token = None
        new_obj.relay_base_url = data["relay_base_url"].rstrip("/")
        new_obj.relay_api_key = data["relay_api_key"]
        cls.apply_metadata(new_obj, data)
        new_obj.updated_time = now

        if not obj:
            new_obj.created_time = now

        new_obj.save()
        return new_obj.id


class DispatcherDecisionLog(models.Model):
    DECISION_STATUS_SELECTED = "selected"
    DECISION_STATUS_EMPTY = "empty"
    DECISION_STATUS_REJECTED = "rejected"
    DECISION_STATUS_CHOICES = (
        (DECISION_STATUS_SELECTED, "已选中"),
        (DECISION_STATUS_EMPTY, "无可用账号"),
        (DECISION_STATUS_REJECTED, "请求被拒绝"),
    )

    user = models.ForeignKey(
        "accounts.User",
        related_name="dispatcher_logs",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    account = models.ForeignKey(
        ChatgptAccount,
        related_name="dispatcher_logs",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    entrypoint = models.CharField(max_length=64, blank=True, verbose_name="入口")
    channel = models.CharField(max_length=16, verbose_name="渠道")
    model_name = models.CharField(max_length=128, blank=True, verbose_name="请求模型")
    decision_status = models.CharField(
        max_length=32,
        choices=DECISION_STATUS_CHOICES,
        default=DECISION_STATUS_SELECTED,
        verbose_name="调度结果",
    )
    requested_account_id = models.PositiveIntegerField(null=True, blank=True, verbose_name="请求账号 ID")
    candidate_account_ids = models.JSONField(default=list, verbose_name="候选账号列表")
    reason = models.TextField(blank=True, verbose_name="调度说明")
    created_time = models.IntegerField(db_index=True, blank=True, verbose_name="创建时间")

    @classmethod
    def save_data(cls, data):
        payload = dict(data)
        payload.setdefault("created_time", int(time.time()))
        return cls.objects.create(**payload)


class UsageLedger(models.Model):
    user = models.ForeignKey(
        "accounts.User",
        related_name="usage_ledgers",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    account = models.ForeignKey(
        ChatgptAccount,
        related_name="usage_ledgers",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    model_name = models.CharField(max_length=128, blank=True, verbose_name="模型名")
    request_type = models.CharField(max_length=64, verbose_name="请求类型")
    prompt_tokens = models.PositiveIntegerField(default=0, verbose_name="输入 Tokens")
    completion_tokens = models.PositiveIntegerField(default=0, verbose_name="输出 Tokens")
    total_tokens = models.PositiveIntegerField(default=0, verbose_name="总 Tokens")
    estimated_cost = models.DecimalField(max_digits=12, decimal_places=6, default=0, verbose_name="预估成本")
    status_code = models.PositiveIntegerField(default=0, verbose_name="状态码")
    error_code = models.CharField(max_length=128, blank=True, verbose_name="错误码")
    created_at = models.IntegerField(db_index=True, blank=True, verbose_name="创建时间")


class ChatConversation(models.Model):
    user = models.ForeignKey(
        "accounts.User",
        related_name="chat_conversations",
        on_delete=models.CASCADE,
    )
    title = models.CharField(max_length=160, default="新对话", verbose_name="会话标题")
    model_name = models.CharField(max_length=128, blank=True, verbose_name="默认模型")
    preview_text = models.TextField(blank=True, verbose_name="预览内容")
    message_count = models.PositiveIntegerField(default=0, verbose_name="消息数量")
    last_message_at = models.IntegerField(default=0, db_index=True, verbose_name="最后消息时间")
    created_time = models.IntegerField(db_index=True, blank=True, verbose_name="创建时间")
    updated_time = models.IntegerField(db_index=True, blank=True, verbose_name="更新时间")

    class Meta:
        ordering = ("-updated_time", "-id")


class ChatConversationMessage(models.Model):
    ROLE_USER = "user"
    ROLE_ASSISTANT = "assistant"
    ROLE_SYSTEM = "system"
    ROLE_CHOICES = (
        (ROLE_USER, "用户"),
        (ROLE_ASSISTANT, "助手"),
        (ROLE_SYSTEM, "系统"),
    )

    conversation = models.ForeignKey(
        ChatConversation,
        related_name="messages",
        on_delete=models.CASCADE,
    )
    role = models.CharField(max_length=16, choices=ROLE_CHOICES, verbose_name="消息角色")
    content = models.TextField(blank=True, verbose_name="消息内容")
    account_label = models.CharField(max_length=128, blank=True, verbose_name="通道标签")
    sequence = models.PositiveIntegerField(default=0, db_index=True, verbose_name="排序序号")
    created_time = models.IntegerField(db_index=True, blank=True, verbose_name="创建时间")
    updated_time = models.IntegerField(db_index=True, blank=True, verbose_name="更新时间")

    class Meta:
        ordering = ("sequence", "id")

    @classmethod
    def save_data(cls, data):
        payload = dict(data)
        payload.setdefault("created_at", int(time.time()))
        return cls.objects.create(**payload)

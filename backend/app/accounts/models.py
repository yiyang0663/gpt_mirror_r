import time

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    STATUS_ACTIVE = "active"
    STATUS_DISABLED = "disabled"
    STATUS_EXPIRED = "expired"
    STATUS_CHOICES = (
        (STATUS_ACTIVE, "正常"),
        (STATUS_DISABLED, "停用"),
        (STATUS_EXPIRED, "过期"),
    )

    POOL_MODE_PUBLIC = "public_pool"
    POOL_MODE_SPECIFIC = "specific_pools"
    POOL_MODE_CHOICES = (
        (POOL_MODE_PUBLIC, "站点公共账号池"),
        (POOL_MODE_SPECIFIC, "指定号池"),
    )

    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default=STATUS_ACTIVE, verbose_name="状态")
    email_verified = models.BooleanField(default=False, verbose_name="邮箱已验证")
    pool_mode = models.CharField(
        max_length=32,
        choices=POOL_MODE_CHOICES,
        default=POOL_MODE_PUBLIC,
        verbose_name="账号池模式",
    )
    plan_id = models.PositiveIntegerField(blank=True, null=True, verbose_name="套餐ID")
    quota_snapshot = models.JSONField(default=dict, verbose_name="额度快照")
    model_limit = models.JSONField(default=list, verbose_name="备注")
    remark = models.TextField(blank=True, verbose_name="备注")
    isolated_session = models.BooleanField(default=True, verbose_name="独立回话")
    gptcar_list = models.JSONField(default=list)
    expired_date = models.DateField(blank=True, null=True, verbose_name="过期日期")

    def get_bound_pool_ids(self):
        binding_ids = []
        if self.pk:
            binding_ids = list(self.pool_bindings.order_by("gptcar_id").values_list("gptcar_id", flat=True))
        if binding_ids:
            return binding_ids
        pool_ids = []
        for item in self.gptcar_list or []:
            if isinstance(item, int):
                pool_ids.append(item)
            elif isinstance(item, str) and item.isdigit():
                pool_ids.append(int(item))
        return pool_ids


class UserPoolBinding(models.Model):
    user = models.ForeignKey(User, related_name="pool_bindings", on_delete=models.CASCADE)
    gptcar = models.ForeignKey("chatgpt.ChatgptCar", related_name="user_bindings", on_delete=models.CASCADE)

    class Meta:
        unique_together = ("user", "gptcar")


class ServicePlan(models.Model):
    name = models.CharField(max_length=64, unique=True, verbose_name="套餐名")
    code = models.CharField(max_length=64, unique=True, verbose_name="套餐编码")
    is_active = models.BooleanField(default=True, verbose_name="是否启用")
    allow_web = models.BooleanField(default=True, verbose_name="网页可用")
    allow_api = models.BooleanField(default=True, verbose_name="API 可用")
    monthly_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="月费")
    display_order = models.PositiveIntegerField(default=100, verbose_name="排序")
    remark = models.TextField(blank=True, verbose_name="备注")
    created_at = models.IntegerField(db_index=True, blank=True, verbose_name="创建时间")
    updated_at = models.IntegerField(db_index=True, blank=True, verbose_name="修改时间")

    def save(self, *args, **kwargs):
        now = int(time.time())
        if not self.created_at:
            self.created_at = now
        self.updated_at = now
        super().save(*args, **kwargs)


class UserSubscription(models.Model):
    STATUS_ACTIVE = "active"
    STATUS_EXPIRED = "expired"
    STATUS_CANCELED = "canceled"
    STATUS_CHOICES = (
        (STATUS_ACTIVE, "生效中"),
        (STATUS_EXPIRED, "已过期"),
        (STATUS_CANCELED, "已取消"),
    )

    user = models.ForeignKey(User, related_name="subscriptions", on_delete=models.CASCADE)
    service_plan = models.ForeignKey(ServicePlan, related_name="subscriptions", on_delete=models.CASCADE)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default=STATUS_ACTIVE, verbose_name="状态")
    start_date = models.DateField(verbose_name="生效时间")
    end_date = models.DateField(blank=True, null=True, verbose_name="结束时间")
    quota_snapshot = models.JSONField(default=dict, verbose_name="额度快照")
    created_at = models.IntegerField(db_index=True, blank=True, verbose_name="创建时间")
    updated_at = models.IntegerField(db_index=True, blank=True, verbose_name="修改时间")

    def save(self, *args, **kwargs):
        now = int(time.time())
        if not self.created_at:
            self.created_at = now
        self.updated_at = now
        super().save(*args, **kwargs)


class QuotaRule(models.Model):
    CHANNEL_ALL = "all"
    CHANNEL_WEB = "web"
    CHANNEL_API = "api"
    CHANNEL_CHOICES = (
        (CHANNEL_ALL, "全部"),
        (CHANNEL_WEB, "网页"),
        (CHANNEL_API, "API"),
    )

    PERIOD_DAILY = "daily"
    PERIOD_MONTHLY = "monthly"
    PERIOD_CHOICES = (
        (PERIOD_DAILY, "每日"),
        (PERIOD_MONTHLY, "每月"),
    )

    service_plan = models.ForeignKey(ServicePlan, related_name="quota_rules", on_delete=models.CASCADE)
    model_name = models.CharField(max_length=128, blank=True, verbose_name="模型名")
    channel = models.CharField(max_length=16, choices=CHANNEL_CHOICES, default=CHANNEL_ALL, verbose_name="渠道")
    period = models.CharField(max_length=16, choices=PERIOD_CHOICES, default=PERIOD_MONTHLY, verbose_name="周期")
    request_limit = models.PositiveIntegerField(default=0, verbose_name="请求上限")
    token_limit = models.PositiveIntegerField(default=0, verbose_name="Token 上限")
    enabled = models.BooleanField(default=True, verbose_name="启用")
    remark = models.CharField(max_length=255, blank=True, verbose_name="备注")
    created_at = models.IntegerField(db_index=True, blank=True, verbose_name="创建时间")
    updated_at = models.IntegerField(db_index=True, blank=True, verbose_name="修改时间")

    def save(self, *args, **kwargs):
        now = int(time.time())
        if not self.created_at:
            self.created_at = now
        self.updated_at = now
        super().save(*args, **kwargs)


class GatewayUserDailyUsage(models.Model):
    SOURCE_GATEWAY_USER_USE_COUNT = "gateway_user_use_count"

    user = models.ForeignKey(User, related_name="gateway_daily_usages", on_delete=models.CASCADE)
    stat_date = models.DateField(db_index=True, verbose_name="统计日期")
    request_count = models.PositiveIntegerField(default=0, verbose_name="累计请求数")
    source = models.CharField(max_length=64, default=SOURCE_GATEWAY_USER_USE_COUNT, verbose_name="来源")
    created_at = models.IntegerField(db_index=True, blank=True, verbose_name="创建时间")
    updated_at = models.IntegerField(db_index=True, blank=True, verbose_name="修改时间")

    class Meta:
        unique_together = ("user", "stat_date")

    def save(self, *args, **kwargs):
        now = int(time.time())
        if not self.created_at:
            self.created_at = now
        self.updated_at = now
        super().save(*args, **kwargs)

    @classmethod
    def upsert_snapshot(cls, user, stat_date, request_count, source=SOURCE_GATEWAY_USER_USE_COUNT):
        obj = cls.objects.filter(user=user, stat_date=stat_date).first()
        if obj:
            obj.request_count = max(int(request_count or 0), int(obj.request_count or 0))
            obj.source = source
            obj.save(update_fields=["request_count", "source", "updated_at"])
            return obj

        obj = cls(
            user=user,
            stat_date=stat_date,
            request_count=max(int(request_count or 0), 0),
            source=source,
        )
        obj.save()
        return obj


class VisitLog(models.Model):
    # user = models.ForeignKey(User, db_constraint=False, on_delete=models.SET_NULL, null=True)
    username = models.CharField(max_length=150, verbose_name="用户名")
    chatgpt_username = models.CharField(max_length=150, null=True, verbose_name="chatgpt")
    log_type = models.CharField(max_length=20, verbose_name="登录类型")
    created_at = models.IntegerField(verbose_name="登录时间")
    ip = models.GenericIPAddressField(verbose_name="登录IP")
    user_agent = models.TextField(verbose_name="User-Agent")

    @classmethod
    def save_data(cls, data):
        obj = cls.objects.create(**data)
        return obj

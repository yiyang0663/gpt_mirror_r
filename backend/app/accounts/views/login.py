from django.contrib.auth import authenticate
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from app.accounts.models import User
from app.accounts.serializers import UserRegisterSerializer
from app.settings import ADMIN_USERNAME, FREE_ACCOUNT_USERNAME
from app.settings import ALLOW_FREE_LOGIN, ALLOW_REGISTER
from app.utils import save_visit_log


class UserFreeLoginView(APIView):
    def post(self, request):
        if not ALLOW_FREE_LOGIN:
            raise ValidationError({"message": "当前系统未开启免费体验"})

        user = User.objects.filter(username=FREE_ACCOUNT_USERNAME, is_active=True, status=User.STATUS_ACTIVE).first()
        if not user:
            raise ValidationError({"message": "当前系统无免费账号可用"})
        request.user = user

        token, created = Token.objects.get_or_create(user=user)
        save_visit_log(request, "login")

        return Response({'admin_token': token.key})


class AccountLogin(ObtainAuthToken):

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data['user']
        if not user.is_active or user.status == User.STATUS_DISABLED:
            raise ValidationError({"message": "账号已停用"})
        if user.status == User.STATUS_EXPIRED:
            raise ValidationError({"message": "账号已过期"})
        if user.expired_date and user.expired_date <= timezone.now().date():
            user.status = User.STATUS_EXPIRED
            user.save(update_fields=["status"])
            raise ValidationError({"message": "账号已过期"})

        user.last_login = timezone.now()
        user.save()

        token, created = Token.objects.get_or_create(user=user)
        request.user = user

        save_visit_log(request, "login")

        result = {'admin_token': token.key}
        if user.username == ADMIN_USERNAME:
            result.update({"is_admin": True})
        return Response(result)


class AccountRegister(APIView):
    def post(self, request, *args, **kwargs):
        if not ALLOW_REGISTER:
            raise ValidationError({"message": "当前系统禁止注册账号"})

        serializer = UserRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        user = User.objects.filter(username=payload["username"]).first()
        if user and not authenticate(username=payload["username"], password=payload["password"]):
            raise ValidationError({"message": "账号已存在"})

        email_owner = User.objects.filter(email=payload["email"]).exclude(username=payload["username"]).first()
        if email_owner:
            raise ValidationError({"message": "邮箱已存在"})

        user, created = User.objects.get_or_create(username=payload["username"])
        user.email = payload["email"]
        user.status = User.STATUS_ACTIVE
        user.pool_mode = User.POOL_MODE_PUBLIC
        user.email_verified = False
        user.set_password(payload["password"])
        user.last_login = timezone.now()
        user.save()

        token, created = Token.objects.get_or_create(user=user)
        return Response({"admin_token": token.key})

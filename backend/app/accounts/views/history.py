import time
from datetime import datetime

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from app.accounts.models import User
from app.chatgpt.models import ChatConversation, ChatConversationMessage
from app.chatgpt.serializers import (
    CreateChatConversationSerializer,
    ShowChatConversationDetailSerializer,
    ShowChatConversationSerializer,
    SyncChatConversationSerializer,
)


def validate_user_access(user):
    if not user or not user.is_active or user.status == User.STATUS_DISABLED:
        raise ValidationError({"message": "账号已停用"})
    if user.status == User.STATUS_EXPIRED:
        raise ValidationError({"message": "账号已过期"})
    if user.expired_date and user.expired_date <= datetime.now().date():
        raise ValidationError({"message": "账号已过期"})


def build_conversation_title(messages, fallback="新对话"):
    for item in messages:
        if item["role"] != ChatConversationMessage.ROLE_USER:
            continue
        text = " ".join(str(item.get("content") or "").split()).strip()
        if not text:
            continue
        if len(text) > 36:
            return f"{text[:36].rstrip()}..."
        return text
    return fallback or "新对话"


def build_preview_text(messages):
    for item in reversed(messages):
        text = " ".join(str(item.get("content") or "").split()).strip()
        if text:
            if len(text) > 120:
                return f"{text[:120].rstrip()}..."
            return text
    return ""


def get_conversation(user, conversation_id):
    validate_user_access(user)
    return get_object_or_404(
        ChatConversation.objects.prefetch_related("messages"),
        id=conversation_id,
        user=user,
    )


class CurrentUserConversationListView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        validate_user_access(request.user)
        queryset = ChatConversation.objects.filter(user=request.user).order_by("-updated_time", "-id")
        serializer = ShowChatConversationSerializer(instance=queryset, many=True)
        return Response({"results": serializer.data})

    def post(self, request):
        validate_user_access(request.user)
        serializer = CreateChatConversationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        now = int(time.time())
        conversation = ChatConversation.objects.create(
            user=request.user,
            title=serializer.validated_data.get("title") or "新对话",
            model_name=serializer.validated_data.get("model_name") or "",
            preview_text="",
            message_count=0,
            last_message_at=0,
            created_time=now,
            updated_time=now,
        )
        return Response(ShowChatConversationSerializer(instance=conversation).data)


class CurrentUserConversationDetailView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, conversation_id):
        conversation = get_conversation(request.user, conversation_id)
        serializer = ShowChatConversationDetailSerializer(instance=conversation)
        return Response(serializer.data)

    @transaction.atomic
    def put(self, request, conversation_id):
        conversation = get_conversation(request.user, conversation_id)
        serializer = SyncChatConversationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        payload_messages = serializer.validated_data.get("messages", [])
        now = int(time.time())
        title = serializer.validated_data.get("title") or conversation.title
        title = build_conversation_title(payload_messages, fallback=title or "新对话")

        conversation.messages.all().delete()
        ChatConversationMessage.objects.bulk_create(
            [
                ChatConversationMessage(
                    conversation=conversation,
                    role=item["role"],
                    content=item.get("content", ""),
                    account_label=item.get("account_label", ""),
                    sequence=index,
                    created_time=now,
                    updated_time=now,
                )
                for index, item in enumerate(payload_messages)
            ]
        )

        conversation.title = title
        conversation.model_name = serializer.validated_data.get("model_name") or conversation.model_name
        conversation.message_count = len(payload_messages)
        conversation.preview_text = build_preview_text(payload_messages)
        conversation.last_message_at = now if payload_messages else 0
        conversation.updated_time = now
        conversation.save(
            update_fields=[
                "title",
                "model_name",
                "message_count",
                "preview_text",
                "last_message_at",
                "updated_time",
            ]
        )

        conversation.refresh_from_db()
        serializer = ShowChatConversationDetailSerializer(instance=conversation)
        return Response(serializer.data)

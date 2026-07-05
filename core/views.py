from celery.result import AsyncResult
from django.db import connection
from django.http import JsonResponse
from django_ratelimit.decorators import ratelimit
from rest_framework import viewsets
from rest_framework.decorators import action, api_view
from rest_framework.response import Response

from . import rag
from .models import Conversation, Document, EvalLog, Product
from .serializers import (
    ConversationSerializer,
    DocumentSerializer,
    EvalLogSerializer,
    ProductSerializer,
)
from .tasks import run_agent_chat_task, run_ask_task


def health(request):
    checks = {"database": False, "redis": False}

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        checks["database"] = True
    except Exception:
        pass

    try:
        checks["redis"] = rag.get_redis_client().ping()
    except Exception:
        pass

    status = 200 if all(checks.values()) else 503
    return JsonResponse({"status": "ok" if status == 200 else "degraded", "checks": checks}, status=status)


@api_view(["POST"])
@ratelimit(key="user", rate="20/m", method="POST", block=True)
def ask(request):
    question = request.data.get("question", "").strip()
    if not question:
        return Response({"detail": "question is required"}, status=400)

    conversation = Conversation.objects.create(user=request.user, question=question)
    task = run_ask_task.delay(conversation.id, question)
    conversation.task_id = task.id
    conversation.save(update_fields=["task_id"])

    return Response({"conversation_id": conversation.id, "task_id": task.id, "status": "pending"}, status=202)


@api_view(["POST"])
@ratelimit(key="user", rate="15/m", method="POST", block=True)
def agent_chat(request):
    message = request.data.get("message", "").strip()
    if not message:
        return Response({"detail": "message is required"}, status=400)

    conversation_id = request.data.get("conversation_id")
    if conversation_id:
        try:
            conversation = Conversation.objects.get(id=conversation_id, user=request.user)
        except Conversation.DoesNotExist:
            return Response({"detail": "conversation not found"}, status=404)
    else:
        conversation = Conversation.objects.create(user=request.user, question=message)

    task = run_agent_chat_task.delay(conversation.id, message)
    conversation.task_id = task.id
    conversation.save(update_fields=["task_id"])

    return Response({"conversation_id": conversation.id, "task_id": task.id, "status": "pending"}, status=202)


class DocumentViewSet(viewsets.ModelViewSet):
    queryset = Document.objects.all().order_by("-created_at")
    serializer_class = DocumentSerializer


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all().order_by("-created_at")
    serializer_class = ProductSerializer


class ConversationViewSet(viewsets.ModelViewSet):
    serializer_class = ConversationSerializer

    def get_queryset(self):
        return Conversation.objects.filter(user=self.request.user).order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=["get"])
    def result(self, request, pk=None):
        conversation = self.get_object()
        if not conversation.task_id:
            return Response({"detail": "no task associated with this conversation"}, status=404)

        async_result = AsyncResult(conversation.task_id)
        payload = {"status": async_result.status}
        if async_result.successful():
            payload["result"] = async_result.result
        elif async_result.failed():
            payload["error"] = str(async_result.result)
        return Response(payload)


class EvalLogViewSet(viewsets.ModelViewSet):
    queryset = EvalLog.objects.all().order_by("-created_at")
    serializer_class = EvalLogSerializer

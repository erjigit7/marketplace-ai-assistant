import time

from django.http import JsonResponse
from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response

from . import agent, rag
from .models import Conversation, Document, EvalLog, Product
from .serializers import (
    ConversationSerializer,
    DocumentSerializer,
    EvalLogSerializer,
    ProductSerializer,
)


def health(request):
    return JsonResponse({"status": "ok"})


@api_view(["POST"])
def ask(request):
    question = request.data.get("question", "").strip()
    if not question:
        return Response({"detail": "question is required"}, status=400)

    started_at = time.monotonic()
    result = rag.generate_answer(question)
    latency_ms = (time.monotonic() - started_at) * 1000

    conversation = Conversation.objects.create(
        user=request.user, question=question, answer=result["answer"]
    )
    EvalLog.objects.create(
        conversation=conversation,
        prompt=question,
        response=result["answer"],
        latency_ms=latency_ms,
    )

    return Response(
        {
            "conversation_id": conversation.id,
            "answer": result["answer"],
            "sources": result["sources"],
        }
    )


@api_view(["POST"])
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

    started_at = time.monotonic()
    result = agent.run_agent(thread_id=conversation.id, user_message=message)
    latency_ms = (time.monotonic() - started_at) * 1000

    conversation.question = message
    conversation.answer = result["answer"]
    conversation.save(update_fields=["question", "answer"])
    EvalLog.objects.create(
        conversation=conversation,
        prompt=message,
        response=result["answer"],
        latency_ms=latency_ms,
    )

    return Response(
        {
            "conversation_id": conversation.id,
            "answer": result["answer"],
            "tool_calls": result["tool_calls"],
        }
    )


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


class EvalLogViewSet(viewsets.ModelViewSet):
    queryset = EvalLog.objects.all().order_by("-created_at")
    serializer_class = EvalLogSerializer

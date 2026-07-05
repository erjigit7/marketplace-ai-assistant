from django.http import JsonResponse
from rest_framework import viewsets

from .models import Conversation, Document, EvalLog, Product
from .serializers import (
    ConversationSerializer,
    DocumentSerializer,
    EvalLogSerializer,
    ProductSerializer,
)


def health(request):
    return JsonResponse({"status": "ok"})


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

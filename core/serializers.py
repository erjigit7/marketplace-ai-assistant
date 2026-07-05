from rest_framework import serializers

from .models import Conversation, Document, EvalLog, Product


class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ["id", "title", "source", "content", "created_at"]
        read_only_fields = ["id", "created_at"]


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ["id", "name", "category", "price", "attributes", "description", "created_at"]
        read_only_fields = ["id", "created_at"]


class ConversationSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Conversation
        fields = ["id", "user", "question", "answer", "created_at"]
        read_only_fields = ["id", "user", "created_at"]


class EvalLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = EvalLog
        fields = [
            "id",
            "conversation",
            "prompt",
            "response",
            "tokens_used",
            "latency_ms",
            "cost_usd",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

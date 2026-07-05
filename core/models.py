from django.conf import settings
from django.db import models
from pgvector.django import HnswIndex, VectorField

EMBEDDING_DIMENSIONS = 1024  # bge-m3 (local, via Ollama); text-embedding-3-small is 1536


class Document(models.Model):
    class Source(models.TextChoices):
        WILDBERRIES = "wildberries", "Wildberries"
        OZON = "ozon", "Ozon"
        OTHER = "other", "Other"

    title = models.CharField(max_length=255)
    source = models.CharField(max_length=20, choices=Source.choices, default=Source.OTHER)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Chunk(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="chunks")
    chunk_index = models.PositiveIntegerField()
    content = models.TextField()
    token_count = models.PositiveIntegerField()
    embedding = VectorField(dimensions=EMBEDDING_DIMENSIONS, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["document_id", "chunk_index"]
        constraints = [
            models.UniqueConstraint(fields=["document", "chunk_index"], name="unique_chunk_per_document")
        ]
        indexes = [
            HnswIndex(
                name="chunk_embedding_hnsw",
                fields=["embedding"],
                m=16,
                ef_construction=64,
                opclasses=["vector_cosine_ops"],
            )
        ]

    def __str__(self):
        return f"{self.document.title} #{self.chunk_index}"


class Product(models.Model):
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    attributes = models.JSONField(default=dict, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Conversation(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="conversations"
    )
    question = models.TextField()
    answer = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} @ {self.created_at:%Y-%m-%d %H:%M}"


class EvalLog(models.Model):
    conversation = models.ForeignKey(
        Conversation, on_delete=models.SET_NULL, null=True, blank=True, related_name="eval_logs"
    )
    prompt = models.TextField()
    response = models.TextField(blank=True)
    tokens_used = models.PositiveIntegerField(default=0)
    latency_ms = models.FloatField(default=0)
    cost_usd = models.DecimalField(max_digits=10, decimal_places=6, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"EvalLog #{self.pk}"

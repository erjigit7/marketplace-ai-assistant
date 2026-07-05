from django.contrib import admin

from .models import Chunk, Conversation, Document, EvalLog, Product


class ChunkInline(admin.TabularInline):
    model = Chunk
    extra = 0
    fields = ["chunk_index", "token_count", "content"]
    readonly_fields = ["chunk_index", "token_count", "content"]
    can_delete = False


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ["title", "source", "created_at"]
    list_filter = ["source"]
    inlines = [ChunkInline]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["name", "category", "price", "created_at"]


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ["user", "question", "created_at"]


@admin.register(EvalLog)
class EvalLogAdmin(admin.ModelAdmin):
    list_display = ["conversation", "tokens_used", "latency_ms", "cost_usd", "created_at"]

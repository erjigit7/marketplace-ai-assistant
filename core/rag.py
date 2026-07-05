import hashlib
import json

import redis
import tiktoken
import torch
from django.conf import settings
from openai import OpenAI
from pgvector.django import CosineDistance
from sentence_transformers import CrossEncoder

from .models import Chunk

RERANK_MODEL = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"  # multilingual, covers Russian
RERANK_CANDIDATES = 20  # how many cosine-similarity candidates to feed the reranker

EMBEDDING_CACHE_TTL_SECONDS = 60 * 60 * 24 * 30  # embeddings for a given model are deterministic

_MODELS_BY_PROVIDER = {
    "openai": {"embedding": "text-embedding-3-small", "chat": "gpt-4o-mini"},
    "ollama": {"embedding": "bge-m3", "chat": "qwen2.5:7b-instruct"},
}

# USD per 1M tokens. Local Ollama models are free (0.0) since they run on our own GPU.
MODEL_PRICING_USD_PER_1M_TOKENS = {
    "text-embedding-3-small": {"input": 0.02, "output": 0.0},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "bge-m3": {"input": 0.0, "output": 0.0},
    "qwen2.5:7b-instruct": {"input": 0.0, "output": 0.0},
}


def estimate_cost_usd(model, input_tokens=0, output_tokens=0):
    pricing = MODEL_PRICING_USD_PER_1M_TOKENS.get(model, {"input": 0.0, "output": 0.0})
    return (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1_000_000

CHUNK_MAX_TOKENS = 400
CHUNK_OVERLAP_TOKENS = 50
RELEVANCE_THRESHOLD = 0.35  # min cosine similarity to trust a chunk (tuned empirically in eval)

_encoding = tiktoken.get_encoding("cl100k_base")
_client = None
_redis_client = None
_reranker = None


def get_redis_client():
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_client


def get_reranker():
    global _reranker
    if _reranker is None:
        _reranker = CrossEncoder(RERANK_MODEL, activation_fn=torch.nn.Sigmoid())
    return _reranker


def _embedding_cache_key(model, text):
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return f"embedding:{model}:{digest}"


def _provider():
    return getattr(settings, "LLM_PROVIDER", "openai")


def get_embedding_model():
    return _MODELS_BY_PROVIDER[_provider()]["embedding"]


def get_chat_model():
    return _MODELS_BY_PROVIDER[_provider()]["chat"]


def get_client():
    global _client
    if _client is None:
        if _provider() == "ollama":
            # Ollama's OpenAI-compatible endpoint ignores the key but the SDK requires one.
            _client = OpenAI(base_url=settings.OLLAMA_BASE_URL, api_key="ollama")
        else:
            _client = OpenAI(api_key=settings.OPENAI_API_KEY)
    return _client


def chunk_text(text, max_tokens=CHUNK_MAX_TOKENS, overlap_tokens=CHUNK_OVERLAP_TOKENS):
    """Split text into token-bounded chunks with overlap, so a sentence cut at
    a chunk boundary still appears whole in at least one neighboring chunk."""
    tokens = _encoding.encode(text)
    if not tokens:
        return []

    chunks = []
    start = 0
    while start < len(tokens):
        end = min(start + max_tokens, len(tokens))
        chunk_tokens = tokens[start:end]
        chunks.append(_encoding.decode(chunk_tokens))
        if end == len(tokens):
            break
        start = end - overlap_tokens
    return chunks


def embed_texts(texts):
    """Embed texts, caching each vector in Redis by hash(model + text) so repeated
    questions/chunks skip the API call entirely (same text always maps to the same
    vector for a given model). Returns (vectors, api_tokens_used) — tokens_used is 0
    when everything was served from cache, since no API call was actually made."""
    if not texts:
        return [], 0

    model = get_embedding_model()
    cache = get_redis_client()
    keys = [_embedding_cache_key(model, text) for text in texts]
    cached_values = cache.mget(keys)

    results = [None] * len(texts)
    missing_indices = [i for i, value in enumerate(cached_values) if value is None]
    for i, value in enumerate(cached_values):
        if value is not None:
            results[i] = json.loads(value)

    api_tokens_used = 0
    if missing_indices:
        missing_texts = [texts[i] for i in missing_indices]
        response = get_client().embeddings.create(model=model, input=missing_texts)
        api_tokens_used = response.usage.total_tokens if response.usage else 0
        pipe = cache.pipeline()
        for idx, item in zip(missing_indices, response.data):
            results[idx] = item.embedding
            pipe.set(keys[idx], json.dumps(item.embedding), ex=EMBEDDING_CACHE_TTL_SECONDS)
        pipe.execute()

    return results, api_tokens_used


def ingest_document(document):
    """(Re)chunk a document and store fresh embeddings for it."""
    document.chunks.all().delete()
    pieces = chunk_text(document.content)
    if not pieces:
        return 0

    embeddings, _ = embed_texts(pieces)
    Chunk.objects.bulk_create(
        [
            Chunk(
                document=document,
                chunk_index=i,
                content=piece,
                token_count=len(_encoding.encode(piece)),
                embedding=embedding,
            )
            for i, (piece, embedding) in enumerate(zip(pieces, embeddings))
        ]
    )
    return len(pieces)


def retrieve(question, top_k=5):
    """Return (chunks, embedding_tokens_used). Two-stage retrieval: pgvector cosine
    similarity narrows the whole corpus down to RERANK_CANDIDATES chunks (cheap,
    index-backed), then a cross-encoder reranker — which looks at the question and
    chunk together instead of comparing two independent vectors — reorders those
    candidates for the final top_k. This fixes cases where cosine similarity ranks
    a superficially-similar chunk from the wrong document above the right one."""
    embeddings, embedding_tokens = embed_texts([question])
    candidates = list(
        Chunk.objects.select_related("document")
        .annotate(distance=CosineDistance("embedding", embeddings[0]))
        .order_by("distance")[:RERANK_CANDIDATES]
    )
    if not candidates:
        return [], embedding_tokens

    scores = get_reranker().predict([(question, chunk.content) for chunk in candidates])
    ranked = sorted(zip(candidates, scores), key=lambda pair: pair[1], reverse=True)[:top_k]
    results = [{"chunk": chunk, "similarity": float(score)} for chunk, score in ranked]
    return results, embedding_tokens


ANSWER_PROMPT_TEMPLATE = """Ты — ассистент для продавцов маркетплейсов. Отвечай на вопрос ТОЛЬКО на основе приведённого контекста.
Если в контексте нет ответа — честно скажи, что не знаешь, не придумывай.
После ответа укажи источники в формате [Документ: <название>].

Контекст:
{context}

Вопрос: {question}
"""


def generate_answer(question, top_k=5):
    results, embedding_tokens = retrieve(question, top_k=top_k)
    relevant = [r for r in results if r["similarity"] >= RELEVANCE_THRESHOLD]
    embedding_cost = estimate_cost_usd(get_embedding_model(), input_tokens=embedding_tokens)

    if not relevant:
        return {
            "answer": "Не знаю — в загруженных документах нет информации по этому вопросу.",
            "sources": [],
            "tokens_used": embedding_tokens,
            "cost_usd": embedding_cost,
        }

    context = "\n\n".join(
        f"[Документ: {r['chunk'].document.title}]\n{r['chunk'].content}" for r in relevant
    )
    prompt = ANSWER_PROMPT_TEMPLATE.format(context=context, question=question)

    response = get_client().chat.completions.create(
        model=get_chat_model(),
        messages=[{"role": "user", "content": prompt}],
    )
    usage = response.usage
    prompt_tokens = usage.prompt_tokens if usage else 0
    completion_tokens = usage.completion_tokens if usage else 0
    chat_cost = estimate_cost_usd(get_chat_model(), input_tokens=prompt_tokens, output_tokens=completion_tokens)

    return {
        "answer": response.choices[0].message.content,
        "sources": [
            {
                "document_id": r["chunk"].document_id,
                "document_title": r["chunk"].document.title,
                "chunk_index": r["chunk"].chunk_index,
                "similarity": round(r["similarity"], 3),
            }
            for r in relevant
        ],
        "tokens_used": embedding_tokens + prompt_tokens + completion_tokens,
        "cost_usd": embedding_cost + chat_cost,
    }

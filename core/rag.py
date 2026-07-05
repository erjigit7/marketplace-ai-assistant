import tiktoken
from django.conf import settings
from openai import OpenAI
from pgvector.django import CosineDistance

from .models import Chunk

_MODELS_BY_PROVIDER = {
    "openai": {"embedding": "text-embedding-3-small", "chat": "gpt-4o-mini"},
    "ollama": {"embedding": "bge-m3", "chat": "qwen2.5:7b-instruct"},
}

CHUNK_MAX_TOKENS = 400
CHUNK_OVERLAP_TOKENS = 50
RELEVANCE_THRESHOLD = 0.35  # min cosine similarity to trust a chunk (tuned empirically in eval)

_encoding = tiktoken.get_encoding("cl100k_base")
_client = None


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
    if not texts:
        return []
    response = get_client().embeddings.create(model=get_embedding_model(), input=texts)
    return [item.embedding for item in response.data]


def ingest_document(document):
    """(Re)chunk a document and store fresh embeddings for it."""
    document.chunks.all().delete()
    pieces = chunk_text(document.content)
    if not pieces:
        return 0

    embeddings = embed_texts(pieces)
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
    """Return the top_k chunks most similar to the question, with a similarity score."""
    query_embedding = embed_texts([question])[0]
    queryset = (
        Chunk.objects.select_related("document")
        .annotate(distance=CosineDistance("embedding", query_embedding))
        .order_by("distance")[:top_k]
    )
    return [{"chunk": chunk, "similarity": 1 - chunk.distance} for chunk in queryset]


ANSWER_PROMPT_TEMPLATE = """Ты — ассистент для продавцов маркетплейсов. Отвечай на вопрос ТОЛЬКО на основе приведённого контекста.
Если в контексте нет ответа — честно скажи, что не знаешь, не придумывай.
После ответа укажи источники в формате [Документ: <название>].

Контекст:
{context}

Вопрос: {question}
"""


def generate_answer(question, top_k=5):
    results = retrieve(question, top_k=top_k)
    relevant = [r for r in results if r["similarity"] >= RELEVANCE_THRESHOLD]

    if not relevant:
        return {
            "answer": "Не знаю — в загруженных документах нет информации по этому вопросу.",
            "sources": [],
        }

    context = "\n\n".join(
        f"[Документ: {r['chunk'].document.title}]\n{r['chunk'].content}" for r in relevant
    )
    prompt = ANSWER_PROMPT_TEMPLATE.format(context=context, question=question)

    response = get_client().chat.completions.create(
        model=get_chat_model(),
        messages=[{"role": "user", "content": prompt}],
    )

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
    }

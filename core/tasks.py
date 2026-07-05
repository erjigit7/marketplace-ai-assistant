import time

import openai
from celery import shared_task

# Only retry on transient failures (network hiccups, timeouts, provider-side
# rate limits) — not on our own bugs, which would just retry forever uselessly.
RETRYABLE_LLM_ERRORS = (openai.APIConnectionError, openai.APITimeoutError, openai.RateLimitError)


@shared_task
def ping():
    return "pong"


@shared_task(bind=True, autoretry_for=RETRYABLE_LLM_ERRORS, retry_backoff=True, retry_backoff_max=60, max_retries=3)
def run_ask_task(self, conversation_id, question):
    from . import rag
    from .models import Conversation, EvalLog

    started_at = time.monotonic()
    result = rag.generate_answer(question)
    latency_ms = (time.monotonic() - started_at) * 1000

    conversation = Conversation.objects.get(id=conversation_id)
    conversation.answer = result["answer"]
    conversation.save(update_fields=["answer"])
    EvalLog.objects.create(
        conversation=conversation,
        request_type="ask",
        prompt=question,
        response=result["answer"],
        latency_ms=latency_ms,
        tokens_used=result["tokens_used"],
        cost_usd=result["cost_usd"],
    )
    return {"conversation_id": conversation_id, "answer": result["answer"], "sources": result["sources"]}


@shared_task(bind=True, autoretry_for=RETRYABLE_LLM_ERRORS, retry_backoff=True, retry_backoff_max=60, max_retries=3)
def run_agent_chat_task(self, conversation_id, message):
    from . import agent
    from .models import Conversation, EvalLog

    started_at = time.monotonic()
    result = agent.run_agent(thread_id=conversation_id, user_message=message)
    latency_ms = (time.monotonic() - started_at) * 1000

    conversation = Conversation.objects.get(id=conversation_id)
    conversation.question = message
    conversation.answer = result["answer"]
    conversation.save(update_fields=["question", "answer"])
    EvalLog.objects.create(
        conversation=conversation,
        request_type="agent_chat",
        prompt=message,
        response=result["answer"],
        latency_ms=latency_ms,
        tokens_used=result["tokens_used"],
        cost_usd=result["cost_usd"],
    )
    return {"conversation_id": conversation_id, "answer": result["answer"], "tool_calls": result["tool_calls"]}

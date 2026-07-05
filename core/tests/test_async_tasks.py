from unittest.mock import patch

import pytest

from core.models import Conversation, EvalLog

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def eager_celery(settings):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True
    settings.CELERY_TASK_STORE_EAGER_RESULT = True


def test_ask_returns_202_then_result_is_pollable(auth_client, user):
    fake_result = {"answer": "14%", "sources": [], "tokens_used": 42, "cost_usd": 0.001}
    with patch("core.rag.generate_answer", return_value=fake_result):
        response = auth_client.post("/api/ask", {"question": "комиссия?"}, format="json")

    assert response.status_code == 202
    conversation_id = response.json()["conversation_id"]

    result_response = auth_client.get(f"/api/conversations/{conversation_id}/result/")
    assert result_response.status_code == 200
    body = result_response.json()
    assert body["status"] == "SUCCESS"
    assert body["result"]["answer"] == "14%"

    conversation = Conversation.objects.get(id=conversation_id)
    assert conversation.answer == "14%"
    assert EvalLog.objects.filter(conversation=conversation).exists()


def test_agent_chat_returns_202_then_result_is_pollable(auth_client, user):
    fake_result = {
        "answer": "850 руб.",
        "tool_calls": [{"tool": "calculate_marketplace_fee", "result": "{}"}],
        "tokens_used": 30,
        "cost_usd": 0.0,
    }
    with patch("core.agent.run_agent", return_value=fake_result):
        response = auth_client.post("/api/agent/chat", {"message": "посчитай"}, format="json")

    assert response.status_code == 202
    conversation_id = response.json()["conversation_id"]

    result_response = auth_client.get(f"/api/conversations/{conversation_id}/result/")
    assert result_response.status_code == 200
    assert result_response.json()["result"]["answer"] == "850 руб."


def test_other_user_cannot_poll_someone_elses_conversation_result(auth_client, django_user_model):
    other_user = django_user_model.objects.create_user(username="other2", password="pw")
    conversation = Conversation.objects.create(user=other_user, question="q", task_id="fake-task-id")

    response = auth_client.get(f"/api/conversations/{conversation.id}/result/")

    assert response.status_code == 404

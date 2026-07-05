import pytest

from core.models import Conversation, Document

pytestmark = pytest.mark.django_db


def test_health_endpoint_is_public(api_client):
    response = api_client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["checks"] == {"database": True, "redis": True}


def test_documents_require_authentication(api_client):
    response = api_client.get("/api/documents/")
    assert response.status_code == 401


def test_auth_client_can_create_document(auth_client):
    response = auth_client.post(
        "/api/documents/",
        {"title": "Return policy", "source": "wildberries", "content": "..."},
        format="json",
    )
    assert response.status_code == 201
    assert Document.objects.count() == 1


def test_conversation_is_scoped_to_request_user(auth_client, user, django_user_model):
    other_user = django_user_model.objects.create_user(username="other", password="pw")
    Conversation.objects.create(user=other_user, question="not mine")
    own = Conversation.objects.create(user=user, question="mine")

    response = auth_client.get("/api/conversations/")
    results = response.json()

    assert response.status_code == 200
    assert [item["id"] for item in results] == [own.id]


def test_creating_conversation_assigns_current_user(auth_client, user):
    response = auth_client.post("/api/conversations/", {"question": "How to return?"}, format="json")
    assert response.status_code == 201
    assert response.json()["user"] == user.id

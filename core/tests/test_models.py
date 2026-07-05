import pytest

from core.models import Conversation, Document, EvalLog, Product

pytestmark = pytest.mark.django_db


def test_document_str():
    doc = Document.objects.create(title="Return policy", content="...")
    assert str(doc) == "Return policy"


def test_product_default_attributes_is_empty_dict():
    product = Product.objects.create(name="Mug", category="home", price="9.99")
    assert product.attributes == {}


def test_conversation_str_includes_user(django_user_model):
    user = django_user_model.objects.create_user(username="seller", password="pw")
    conversation = Conversation.objects.create(user=user, question="How to return an item?")
    assert "seller" in str(conversation)


def test_evallog_defaults():
    log = EvalLog.objects.create(prompt="test prompt")
    assert log.tokens_used == 0
    assert log.cost_usd == 0

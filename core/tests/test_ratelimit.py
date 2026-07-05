from unittest.mock import patch

import pytest

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def eager_celery(settings):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True
    settings.CELERY_TASK_STORE_EAGER_RESULT = True


def test_ask_is_rate_limited_at_20_per_minute(auth_client, user):
    fake_result = {"answer": "x", "sources": [], "tokens_used": 0, "cost_usd": 0}
    with patch("core.rag.generate_answer", return_value=fake_result):
        statuses = [
            auth_client.post("/api/ask", {"question": "q"}, format="json").status_code for _ in range(21)
        ]

    assert statuses[:20] == [202] * 20
    assert statuses[20] == 403

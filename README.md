# Marketplace AI Assistant

Ассистент для продавцов маркетплейсов (Wildberries/Ozon): отвечает на вопросы по политикам площадки (RAG), генерирует структурированные описания товаров и действует как агент, выбирающий нужный инструмент. Портфолио-проект, план — [ROADMAP.md](ROADMAP.md).

## Стек
Django + DRF, PostgreSQL + pgvector, Redis, Celery, LangGraph, OpenAI API, Pydantic, Docker Compose.

## Запуск

```bash
cp .env.example .env
docker compose up -d --build
docker compose exec web python manage.py migrate
```

Проверка: `curl http://localhost:8000/health` → `{"status": "ok"}`.

## Аутентификация

API защищено токенами DRF. Создать пользователя и получить токен:

```bash
docker compose exec web python manage.py createsuperuser
curl -X POST http://localhost:8000/api/auth/token \
  -d "username=<username>&password=<password>"
```

Токен передаётся в заголовке: `Authorization: Token <key>`.

## Эндпоинты

| Метод | Путь | Описание |
|---|---|---|
| GET | `/health` | health-check, без авторизации |
| POST | `/api/ask` | RAG: вопрос → ответ с указанием источника (или "не знаю") |
| CRUD | `/api/documents/` | документы для RAG (политики/правила площадок) |
| CRUD | `/api/products/` | товары продавца |
| CRUD | `/api/conversations/` | история запросов к ассистенту (только свои) |
| CRUD | `/api/eval-logs/` | логи для оценки качества/стоимости |

## RAG: эмбеддинги и LLM

Провайдер переключается переменной `LLM_PROVIDER` в `.env`:

- `LLM_PROVIDER=openai` — использует `OPENAI_API_KEY`, модели `text-embedding-3-small` + `gpt-4o-mini`.
- `LLM_PROVIDER=ollama` — локально через [Ollama](https://ollama.com) (`bge-m3` для эмбеддингов, `qwen2.5:7b-instruct` для генерации), ключ не нужен. Требует запущенный `ollama serve` на хосте; контейнер обращается к нему по `http://host.docker.internal:11434/v1`.

**Важно:** эмбеддинги разных моделей несовместимы по размерности и векторному пространству. При смене `LLM_PROVIDER` весь корпус нужно переиндексировать заново.

Загрузка документов и построение индекса:

```bash
docker compose exec web python manage.py load_seed_documents
docker compose exec web python manage.py ingest_documents
```

Черновой eval (15+ вопросов, сверка топ-источника и ручная проверка ответа):

```bash
docker compose exec web python manage.py run_eval
```

## Тесты

```bash
docker compose exec web pytest -v
```

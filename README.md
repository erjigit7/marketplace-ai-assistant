# Marketplace AI Assistant

Ассистент для продавцов маркетплейсов (Wildberries/Ozon): отвечает на вопросы по политикам площадки (RAG), генерирует структурированные описания товаров и действует как агент, выбирающий нужный инструмент. Портфолио-проект, план — [ROADMAP.md](ROADMAP.md).

## Стек
Django + DRF, PostgreSQL + pgvector, Redis, Celery, LangGraph, OpenAI API, Pydantic, Docker Compose.

## Сервисы (docker-compose)

| Сервис | Назначение |
|---|---|
| `web` | Django + DRF API |
| `worker` | Celery-воркер — выполняет тяжёлые LLM-вызовы вне HTTP-потока |
| `db` | PostgreSQL + pgvector |
| `redis` | брокер/backend Celery (db 1), кэш эмбеддингов (db 0), кэш rate-limit (db 2) |
| `flower` | мониторинг очереди Celery — http://localhost:5555 |

## Запуск

```bash
cp .env.example .env
docker compose up -d --build
docker compose exec web python manage.py migrate
```

Проверка: `curl http://localhost:8000/health` → `{"status": "ok", "checks": {"database": true, "redis": true}}`.

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
| GET | `/health` | health-check (проверяет БД и Redis), без авторизации |
| POST | `/api/ask` | ставит RAG-запрос в очередь Celery, отвечает `202` с `task_id` (лимит 20/мин на пользователя) |
| POST | `/api/agent/chat` | ставит агентский запрос в очередь, `202` с `task_id` (лимит 15/мин) |
| GET | `/api/conversations/<id>/result/` | опрос результата задачи (`PENDING`/`STARTED`/`SUCCESS`/`FAILURE`) |
| CRUD | `/api/documents/` | документы для RAG (политики/правила площадок) |
| CRUD | `/api/products/` | товары продавца |
| CRUD | `/api/conversations/` | история запросов к ассистенту (только свои) |
| CRUD | `/api/eval-logs/` | логи для оценки качества/стоимости |

### Асинхронный flow

`/api/ask` и `/api/agent/chat` сразу отвечают `202 {"conversation_id", "task_id", "status": "pending"}` — сам LLM-вызов уходит в Celery-задачу (`worker`), а не держит HTTP-соединение. Результат забирается отдельным запросом:

```bash
curl -X POST -H "Authorization: Token <key>" -d '{"question": "..."}' http://localhost:8000/api/ask
# -> {"conversation_id": 5, "task_id": "...", "status": "pending"}
curl -H "Authorization: Token <key>" http://localhost:8000/api/conversations/5/result/
# -> {"status": "SUCCESS", "result": {"answer": "...", "sources": [...]}}
```

При сбое LLM API/Ollama задача автоматически повторяется с exponential backoff (1с, 2с, 4с..., до 3 попыток).

## RAG: эмбеддинги и LLM

Провайдер переключается переменной `LLM_PROVIDER` в `.env`:

- `LLM_PROVIDER=openai` — использует `OPENAI_API_KEY`, модели `text-embedding-3-small` + `gpt-4o-mini`.
- `LLM_PROVIDER=ollama` — локально через [Ollama](https://ollama.com) (`bge-m3` для эмбеддингов, `qwen2.5:7b-instruct` для генерации), ключ не нужен. Требует запущенный `ollama serve` на хосте; контейнер обращается к нему по `http://host.docker.internal:11434/v1`.

**Важно:** эмбеддинги разных моделей несовместимы по размерности и векторному пространству. При смене `LLM_PROVIDER` весь корпус нужно переиндексировать заново.

Каждый эмбеддинг кэшируется в Redis по хэшу `(модель, текст)` — повторный одинаковый вопрос не делает нового API-вызова вообще (0 токенов, 0 стоимости на этот вызов).

Загрузка документов и построение индекса:

```bash
docker compose exec web python manage.py load_seed_documents
docker compose exec web python manage.py ingest_documents
```

## Eval и стоимость

`run_eval` прогоняет три типа кейсов из `core/eval_data.py` и печатает scorecard:

```bash
docker compose exec web python manage.py run_eval
```

- **Retrieval accuracy** — топ-источник RAG совпадает с ожидаемым документом
- **Tool selection accuracy** — агент вызвал (или не вызвал) правильный инструмент
- **JSON validity rate** — `generate_product_listing` вернул валидную Pydantic-схему

`analyze_costs` строит в Pandas разбивку по логам (`EvalLog`) — latency p50/p95, стоимость по типу запроса (`ask` vs `agent_chat`), латентность по дням — и сохраняет графики в `reports/`:

```bash
docker compose exec web python manage.py analyze_costs
```

## Агент

`POST /api/agent/chat` с `{"message": "...", "conversation_id": <опционально>}`. Без `conversation_id` создаётся новый разговор; с ним — диалог продолжается с сохранённым контекстом (состояние графа персистится в Postgres через `PostgresSaver`, `thread_id` = id разговора).

Три инструмента, между которыми агент выбирает сам:
- `search_policy_docs` — RAG-поиск по документам (обёртка над `/ask`)
- `calculate_marketplace_fee` — калькулятор комиссии (обычная Python-функция, без LLM)
- `generate_product_listing` — структурированное описание товара (Pydantic-схема: `title`, `bullet_points`, `attributes`, `category`; retry до 2 раз при невалидном JSON)

## Тесты

```bash
docker compose exec web pytest -v
```

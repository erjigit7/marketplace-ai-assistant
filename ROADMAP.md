# Marketplace AI Assistant — Roadmap

Портфолио-проект для перехода в AI Engineer. Источник исходного плана: `AI_ENG_1.PDF`.

## Контекст (важно для темпа объяснений)
- Django/DRF: немного трогал раньше — не нужен разбор с нуля, но нужен рефреш ORM/serializers/views перед стартом кода
- LLM API: делал простые запросы к GPT — embeddings, RAG, function calling, LangGraph объяснять с нуля
- Формат работы: перед каждым практическим шагом — короткое объяснение теории (зачем, как работает), потом код
- Темп: сжатый (больше часов в неделю, ориентир 3-4 недели вместо 6)

## Стек
Django + DRF, PostgreSQL + pgvector, Redis, Celery, LangGraph поверх LangChain, OpenAI (embeddings + function calling), Pydantic, Docker Compose.

## Фаза 0 — Окружение (0.5–1 день)
- Теория: зачем docker-compose связывает Django+Postgres+Redis+Celery одной командой
- Практика: `docker-compose.yml` (django, postgres+pgvector расширение, redis), скелет Django-проекта
- Чекпоint: `docker-compose up` поднимает всё, `/health` отвечает 200

## Фаза 1 — Django/DRF фундамент
- Теория-рефреш: ORM/миграции, ModelViewSet+Router, откуда DRF берёт сериализацию
- Практика: модели `Document`, `Product`, `Conversation`, `EvalLog`; CRUD через DRF; простая аутентификация (JWT/Token); 5–10 pytest-тестов
- Чекпоint: репозиторий на GitHub, README с инструкцией запуска

## Фаза 2 — RAG-ядро
- Теория: эмбеддинги и cosine similarity, зачем чанкинг с overlap, pgvector vs обычный SQL-поиск, откуда галлюцинации и как их лечит fallback "не знаю"
- Практика: 10–20 документов WB/Ozon → чанкинг → эмбеддинги (text-embedding-3-small) → pgvector → retrieval → генерация ответа с указанием источника
- Чекпоint: эндпоинт `/ask`, 15–20 тестовых вопросов с ручной оценкой (черновой eval)

## Фаза 3 — Агент, function calling, structured output
- Теория: агент vs RAG-цепочка, function calling/JSON schema у OpenAI, зачем LangGraph (state graph, узлы, условные переходы, checkpointer для персистентности диалога)
- Практика: инструменты `search_policy_docs`, `calculate_marketplace_fee`, `generate_product_listing`; граф на LangGraph; Pydantic-схема для описания товара; retry на невалидный JSON (до 2 попыток)
- Чекпоint: эндпоинт `/agent/chat`, агент сам выбирает нужный инструмент

## Фаза 4 — Production + Eval + упаковка
- Теория: зачем задачи уходят в очередь (Celery), retry/exponential backoff, что кэшировать в Redis и почему, LLM-as-judge, cost per request
- Практика: LLM-вызов в Celery-задаче, retry-политика, кэш в Redis, логирование (промпт/токены/latency/cost), rate limiting, health-check, eval-датасет 30–50 кейсов (retrieval accuracy, answer correctness, tool selection accuracy, JSON validity, latency p50/p95, cost), анализ в Pandas, финальный docker-compose, README + демо-видео
- Чекпоint: сервис держит параллельные запросы, не падает при недоступности LLM API, есть таблица метрик и демо

## Ресурсы (из исходного плана)
- Django tutorial — docs.djangoproject.com/en/stable/intro/tutorial01/
- LangGraph — langchain-ai.github.io/langgraph
- pgvector — github.com/pgvector/pgvector
- OpenAI function calling / structured outputs — platform.openai.com/docs/guides/function-calling
- Celery + Django — docs.celeryq.dev/en/stable/django
- Правила WB/Ozon для селлеров — seller.wildberries.ru, seller.ozon.ru

## Статус
- [x] Фаза 0 — Окружение
- [x] Фаза 1 — Django/DRF фундамент
- [ ] Фаза 2 — RAG-ядро
- [ ] Фаза 3 — Агент, function calling, structured output
- [ ] Фаза 4 — Production + Eval + упаковка

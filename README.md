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
| CRUD | `/api/documents/` | документы для RAG (политики/правила площадок) |
| CRUD | `/api/products/` | товары продавца |
| CRUD | `/api/conversations/` | история запросов к ассистенту (только свои) |
| CRUD | `/api/eval-logs/` | логи для оценки качества/стоимости |

## Тесты

```bash
docker compose exec web pytest -v
```

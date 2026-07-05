import json

from langchain_core.tools import tool
from pydantic import BaseModel, ValidationError

from . import rag

MAX_LISTING_ATTEMPTS = 3  # first try + up to 2 retries with a clarifying prompt

# Illustrative commission tables (order-of-magnitude, not scraped from live rate
# cards — real tables have hundreds of categories and change often; see the
# ingested Ozon/WB commission documents for the source rules this simplifies).
OZON_CATEGORY_RATES = {
    "electronics": 0.15,
    "clothing": 0.25,
    "home": 0.20,
    "beauty": 0.22,
    "toys": 0.20,
}
WILDBERRIES_CATEGORY_RATES = {
    "electronics": 0.12,
    "clothing": 0.20,
    "home": 0.18,
    "beauty": 0.19,
    "toys": 0.17,
}
DEFAULT_CATEGORY_RATE = 0.20


@tool
def search_policy_docs(query: str) -> str:
    """Найти ответ в загруженных документах о правилах и политиках маркетплейсов
    (Wildberries/Ozon) — возвраты, приёмка, карточка товара, комиссии и т.д.
    Используй для любых вопросов о правилах площадок."""
    result = rag.generate_answer(query)
    if not result["sources"]:
        return result["answer"]
    sources = ", ".join(s["document_title"] for s in result["sources"])
    return f"{result['answer']}\n\n(источники: {sources})"


@tool
def calculate_marketplace_fee(marketplace: str, category: str, price: float) -> dict:
    """Посчитать примерную комиссию маркетплейса (Wildberries или Ozon) для товара
    по цене и категории. marketplace: 'wildberries' или 'ozon'. Возвращает ставку,
    сумму комиссии и сумму к получению продавцом."""
    marketplace = marketplace.strip().lower()

    if marketplace == "ozon":
        if price <= 100:
            rate = 0.14
        elif price <= 300:
            rate = 0.20
        else:
            rate = OZON_CATEGORY_RATES.get(category.strip().lower(), DEFAULT_CATEGORY_RATE)
    elif marketplace == "wildberries":
        rate = WILDBERRIES_CATEGORY_RATES.get(category.strip().lower(), DEFAULT_CATEGORY_RATE)
    else:
        return {"error": f"неизвестный маркетплейс: {marketplace!r}, ожидается 'wildberries' или 'ozon'"}

    commission_amount = round(price * rate, 2)
    return {
        "marketplace": marketplace,
        "category": category,
        "price": price,
        "commission_rate": rate,
        "commission_amount": commission_amount,
        "seller_receives": round(price - commission_amount, 2),
    }


class ProductListing(BaseModel):
    title: str
    bullet_points: list[str]
    attributes: dict[str, str]
    category: str


def _generate_listing_impl(name: str, category: str, attributes: dict) -> ProductListing:
    from .agent import get_chat_llm  # local import: avoids a core.tools <-> core.agent cycle

    structured_llm = get_chat_llm().with_structured_output(ProductListing)
    prompt = (
        "Составь структурированное описание товара для карточки маркетплейса.\n"
        f"Название товара: {name}\n"
        f"Категория: {category}\n"
        f"Атрибуты: {json.dumps(attributes, ensure_ascii=False)}\n"
        "title — короткое цепляющее название (до 60 символов), bullet_points — 3-5 пунктов "
        "с преимуществами, attributes — переданные атрибуты (можно дополнить), "
        "category — категория товара."
    )

    last_error = None
    for attempt in range(1, MAX_LISTING_ATTEMPTS + 1):
        try:
            return structured_llm.invoke(prompt)
        except ValidationError as exc:
            last_error = exc
            prompt += (
                f"\n\nПредыдущая попытка не прошла валидацию схемы: {exc}. "
                "Верни строго валидный JSON по схеме."
            )
    raise ValueError(f"Не удалось получить валидное описание товара после {MAX_LISTING_ATTEMPTS} попыток: {last_error}")


@tool
def generate_product_listing(name: str, category: str, attributes: dict) -> dict:
    """Сгенерировать структурированное описание товара (title, bullet_points,
    attributes, category) для карточки маркетплейса по названию, категории и атрибутам."""
    try:
        listing = _generate_listing_impl(name, category, attributes)
    except ValueError as exc:
        return {"error": str(exc)}
    return listing.model_dump()


AGENT_TOOLS = [search_policy_docs, calculate_marketplace_fee, generate_product_listing]

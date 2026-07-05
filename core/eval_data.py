EVAL_QUESTIONS = [
    {
        "question": "В течение скольких дней Wildberries проводит приёмку товара по количеству и ассортименту?",
        "expected_document": "WB: Правила приёмки и возврата товара (раздел 11)",
    },
    {
        "question": "Какой штраф платит Wildberries продавцу за необоснованный отказ в приёмке?",
        "expected_document": "WB: Правила приёмки и возврата товара (раздел 11)",
    },
    {
        "question": "Через сколько дней товар считается утраченным на складе Wildberries?",
        "expected_document": "WB: Правила приёмки и возврата товара (раздел 11)",
    },
    {
        "question": "Как рассчитывается коэффициент проблемного товара на Wildberries?",
        "expected_document": "WB: Правила приёмки и возврата товара (раздел 11)",
    },
    {
        "question": "В каком разделе портала продавец Wildberries видит заявки на возврат от покупателей?",
        "expected_document": "WB: Возврат товара по заявке покупателя",
    },
    {
        "question": "Какие два решения может принять продавец Wildberries по заявке на возврат от покупателя?",
        "expected_document": "WB: Возврат товара по заявке покупателя",
    },
    {
        "question": "Максимальная длина названия товара в карточке на Wildberries?",
        "expected_document": "WB: Ключевые требования к карточке товара",
    },
    {
        "question": "Можно ли на Wildberries предлагать покупателю деньги за отзыв?",
        "expected_document": "WB: Ключевые требования к карточке товара",
    },
    {
        "question": "Какая минимальная контрастность текста на фото товара для Wildberries?",
        "expected_document": "WB: Ключевые требования к карточке товара",
    },
    {
        "question": "Какая комиссия на Ozon для товаров дешевле 100 рублей?",
        "expected_document": "Ozon: Вознаграждение (комиссия) за продажу товаров",
    },
    {
        "question": "Когда именно списывается комиссия Ozon с продавца — на каком статусе заказа?",
        "expected_document": "Ozon: Вознаграждение (комиссия) за продажу товаров",
    },
    {
        "question": "Сколько дней есть у продавца на Ozon, чтобы принять решение по заявке на возврат?",
        "expected_document": "Ozon: Условия и сроки возврата товара",
    },
    {
        "question": "Кто оплачивает обратную доставку при возврате качественного товара на Ozon?",
        "expected_document": "Ozon: Условия и сроки возврата товара",
    },
    {
        "question": "Что происходит с заявкой на возврат на Ozon, если продавец не отвечает 7 дней?",
        "expected_document": "Ozon: Условия и сроки возврата товара",
    },
    {
        "question": "Кто платит за обратную логистику при невыкупе заказа на Ozon?",
        "expected_document": "Ozon: Расходы продавца при возвратах, невыкупах и отменах",
    },
    {
        "question": "Кто оплачивает возврат бракованного товара на Ozon — продавец или покупатель?",
        "expected_document": "Ozon: Расходы продавца при возвратах, невыкупах и отменах",
    },
    {
        "question": "Какая погода будет завтра в Алматы?",
        "expected_document": None,  # out-of-scope: fallback ("не знаю") is the correct answer
    },
]


# Agent tool-selection cases: for each, we know in advance which tool the agent
# should pick. expected_tool=None means the agent should answer directly with no tool.
AGENT_TOOL_CASES = [
    {
        "message": "Через сколько дней Ozon одобрит возврат, если продавец не ответил?",
        "expected_tool": "search_policy_docs",
    },
    {
        "message": "Можно ли на Wildberries предлагать деньги за отзыв?",
        "expected_tool": "search_policy_docs",
    },
    {
        "message": "Какая максимальная длина названия товара на Wildberries?",
        "expected_tool": "search_policy_docs",
    },
    {
        "message": "Посчитай комиссию для товара категории clothing ценой 1500 рублей на Wildberries",
        "expected_tool": "calculate_marketplace_fee",
    },
    {
        "message": "Сколько я получу, если продам товар за 2000 рублей в категории beauty на Ozon?",
        "expected_tool": "calculate_marketplace_fee",
    },
    {
        "message": "Какая комиссия на Ozon для товара дешевле 100 рублей?",
        "expected_tool": "calculate_marketplace_fee",
    },
    {
        "message": "Сгенерируй описание товара: название 'Разделочная доска бамбук', категория кухня, атрибуты: материал=бамбук, размер=30x20см",
        "expected_tool": "generate_product_listing",
    },
    {
        "message": "Составь карточку для товара 'Рюкзак городской', категория сумки, атрибуты: объём=20л, цвет=серый",
        "expected_tool": "generate_product_listing",
    },
    {
        "message": "Привет! Что ты умеешь?",
        "expected_tool": None,
    },
    {
        "message": "Спасибо, было полезно!",
        "expected_tool": None,
    },
    {
        "message": "Посчитай комиссию для моего товара на Ozon",  # missing price/category
        "expected_tool": None,  # should ask for clarification instead of guessing
    },
]


# Structured-output cases: generate_product_listing must return a value that
# validates against the ProductListing schema (title/bullet_points/attributes/category).
PRODUCT_LISTING_CASES = [
    {
        "name": "Термокружка 500мл",
        "category": "посуда",
        "attributes": {"материал": "нержавеющая сталь", "объем": "500мл", "цвет": "черный"},
    },
    {
        "name": "Разделочная доска бамбук",
        "category": "кухня",
        "attributes": {"материал": "бамбук", "размер": "30x20см"},
    },
    {
        "name": "Рюкзак городской",
        "category": "сумки",
        "attributes": {"объём": "20л", "цвет": "серый"},
    },
    {
        "name": "Силиконовый чехол для телефона",
        "category": "аксессуары",
        "attributes": {"материал": "силикон", "цвет": "прозрачный"},
    },
    {
        "name": "Беспроводные наушники",
        "category": "электроника",
        "attributes": {"тип": "вкладыши", "время работы": "6 часов", "цвет": "белый"},
    },
    {
        "name": "Детская игрушка-пирамидка",
        "category": "игрушки",
        "attributes": {"материал": "дерево", "возраст": "1-3 года"},
    },
]

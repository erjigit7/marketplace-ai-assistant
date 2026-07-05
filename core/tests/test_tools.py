from core.tools import calculate_marketplace_fee


def _call(**kwargs):
    return calculate_marketplace_fee.invoke(kwargs)


def test_ozon_cheap_item_uses_flat_14_percent():
    result = _call(marketplace="ozon", category="toys", price=80)
    assert result["commission_rate"] == 0.14
    assert result["commission_amount"] == 11.2


def test_ozon_mid_price_uses_flat_20_percent_regardless_of_category():
    result = _call(marketplace="ozon", category="electronics", price=200)
    assert result["commission_rate"] == 0.20


def test_ozon_above_300_uses_category_rate():
    result = _call(marketplace="ozon", category="electronics", price=1000)
    assert result["commission_rate"] == 0.15
    assert result["commission_amount"] == 150
    assert result["seller_receives"] == 850


def test_wildberries_uses_category_rate_regardless_of_price():
    result = _call(marketplace="wildberries", category="clothing", price=50)
    assert result["commission_rate"] == 0.20


def test_unknown_category_falls_back_to_default_rate():
    result = _call(marketplace="ozon", category="something-unlisted", price=1000)
    assert result["commission_rate"] == 0.20


def test_unknown_marketplace_returns_error():
    result = _call(marketplace="aliexpress", category="toys", price=100)
    assert "error" in result

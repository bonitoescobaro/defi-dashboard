"""Цены через CoinMarketCap API."""

from __future__ import annotations

import requests

from .env import get

CMC_URL = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"


def get_quotes(symbols: list[str], timeout: int = 15, attempts: int = 3) -> tuple[dict, str | None]:
    """Возвращает ({symbol: {price, change_24h}}, ошибка_или_None)."""
    key = get("CMC_API_KEY")
    if not key:
        return {}, "Не задан CMC_API_KEY в .env"

    payload = None
    last_error: str = ""
    for _ in range(attempts):
        try:
            resp = requests.get(
                CMC_URL,
                params={"symbol": ",".join(symbols), "convert": "USD"},
                headers={"X-CMC_PRO_API_KEY": key, "Accept": "application/json"},
                timeout=timeout,
            )
            resp.raise_for_status()
            payload = resp.json()
            break
        except Exception as exc:  # сеть, ключ, лимиты — пробуем ещё раз
            last_error = str(exc)
    if payload is None:
        return {}, f"CoinMarketCap: {last_error}"

    out: dict[str, dict] = {}
    for symbol, item in (payload.get("data") or {}).items():
        quote = item["quote"]["USD"]
        out[symbol.upper()] = {
            "price": float(quote["price"]),
            "change_24h": float(quote.get("percent_change_24h") or 0.0),
            "market_cap": float(quote.get("market_cap") or 0.0),
        }
    if not out:
        err = (payload.get("status") or {}).get("error_message") or "пустой ответ"
        return {}, f"CoinMarketCap: {err}"
    return out, None


QUOTES_BY_ID_URL = "https://pro-api.coinmarketcap.com/v3/cryptocurrency/quotes/latest"


def get_quotes_by_ids(ids: list[int], timeout: int = 20, attempts: int = 3) -> tuple[dict, str | None]:
    """Цены по id монет: {id: {symbol, price, change_24h, updated}}.

    Один запрос покрывает весь портфель (до 250 монет) и стоит 1 кредит.
    Берём именно id: по тикеру CMC может вернуть несколько разных монет.
    """
    key = get("CMC_API_KEY")
    if not key:
        return {}, "Не задан CMC_API_KEY"
    if not ids:
        return {}, None

    payload = None
    last_error = ""
    for _ in range(attempts):
        try:
            resp = requests.get(
                QUOTES_BY_ID_URL,
                params={"id": ",".join(str(i) for i in ids), "convert": "USD"},
                headers={"X-CMC_PRO_API_KEY": key, "Accept": "application/json"},
                timeout=timeout,
            )
            resp.raise_for_status()
            payload = resp.json()
            break
        except Exception as exc:
            last_error = str(exc)
    if payload is None:
        return {}, f"CoinMarketCap: {last_error}"

    out: dict = {}
    data = payload.get("data") or {}
    # v3 отдаёт список объектов, v1 — словарь по id; поддерживаем оба формата.
    items = data.values() if isinstance(data, dict) else data
    for item in items:
        raw_quote = item.get("quote")
        # v3: quote — список плоских объектов с полем symbol ("USD"), v1: словарь {"USD": {...}}
        if isinstance(raw_quote, list):
            quote = next(
                (q for q in raw_quote
                 if isinstance(q, dict) and q.get("symbol") == "USD" and "price" in q),
                {},
            )
        elif isinstance(raw_quote, dict):
            quote = raw_quote.get("USD") or {}
        else:
            quote = {}
        if "price" not in quote:
            continue
        out[int(item["id"])] = {
            "symbol": item.get("symbol"),
            "price": float(quote["price"]),
            "change_24h": float(quote.get("percent_change_24h") or 0.0),
            "updated": quote.get("last_updated"),
        }
    if not out:
        err = (payload.get("status") or {}).get("error_message") or "пустой ответ"
        return {}, f"CoinMarketCap: {err}"
    return out, None
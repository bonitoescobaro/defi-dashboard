"""Источники данных.

Сейчас только тестовый набор из config.py. Сюда же подключаются реальные источники:
- CoinMarketCap / CoinGecko API — цены и количества;
- DeFiLlama Yields API — доходности пулов;
- Aave v3 subgraph (Arbitrum) — залог, долг и health factor;
- RPC-вызовы — балансы кошелька.
"""

from __future__ import annotations

import pandas as pd

from .config import PORTFOLIO
from .prices import get_quotes_by_ids


def load_portfolio() -> pd.DataFrame:
    """Портфель как DataFrame: token, cluster, chain, cmc_id, qty, value.

    qty — количество монет, value — стоимость на момент снимка (запасной вариант,
    если цену получить не удалось).
    """
    df = pd.DataFrame(
        PORTFOLIO, columns=["token", "cluster", "chain", "cmc_id", "qty", "value"]
    )
    return df


def portfolio_snapshot() -> tuple[pd.DataFrame, float, str | None, str | None]:
    """Портфель, пересчитанный по живым ценам CoinMarketCap.

    Возвращает (df, total, метка_времени_UTC, ошибка). Если цену по монете
    получить не удалось, строка считается по цене из снимка.
    """
    df = load_portfolio()
    quotes, err = get_quotes_by_ids([int(x) for x in df["cmc_id"].tolist()])

    prices, changes, stamps = [], [], []
    for _, row in df.iterrows():
        q = quotes.get(int(row["cmc_id"]))
        if q:
            prices.append(q["price"])
            changes.append(q["change_24h"])
            stamps.append(q["updated"])
        else:
            qty = float(row["qty"]) or 1.0
            prices.append(float(row["value"]) / qty)
            changes.append(0.0)
            stamps.append(None)

    df = df.assign(price=prices, change_24h=changes)
    df["value"] = df["qty"] * df["price"]
    total = float(df["value"].sum())
    stamp = next((s for s in stamps if s), None)
    return df, total, stamp, err


def load_positions_from_csv(path: str) -> pd.DataFrame:
    """Читает позиции из CSV с колонками token,cluster,chain,value.

    Удобно, если портфель ведётся вручную в таблице.
    """
    df = pd.read_csv(path)
    required = {"token", "cluster", "chain", "value"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"В CSV нет колонок: {', '.join(sorted(missing))}")
    return df[["token", "cluster", "chain", "value"]]
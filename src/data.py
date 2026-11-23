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


def load_portfolio() -> pd.DataFrame:
    """Возвращает портфель как DataFrame: token, cluster, chain, value.

    TODO: заменить на реальную загрузку (CMC API или RPC + цены).
    """
    df = pd.DataFrame(PORTFOLIO, columns=["token", "cluster", "chain", "value"])
    return df


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
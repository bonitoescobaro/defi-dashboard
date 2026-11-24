"""Настройки дашборда: тестовые данные портфеля и пороги риска.

Здесь живёт всё, что пользователь может менять руками:
состав портфеля (пока тестовый), параметры займа и пороги предупреждений.
"""

from __future__ import annotations

# Тестовый портфель (снимок CoinMarketCap). Заменяется реальным источником в src/data.py.
PORTFOLIO: list[dict] = [
    {"token": "ETH",   "cluster": "Мейджоры",           "chain": "Ethereum",        "value": 2283.15},
    {"token": "BTC",   "cluster": "Мейджоры",           "chain": "Ethereum",        "value": 787.64},
    {"token": "AERO",  "cluster": "veTokenomics",       "chain": "Base",            "value": 383.19},
    {"token": "HYPE",  "cluster": "DeFi-инфра",         "chain": "Hyperliquid",     "value": 312.51},
    {"token": "CVX",   "cluster": "veTokenomics",       "chain": "Ethereum",        "value": 291.41},
    {"token": "CRV",   "cluster": "veTokenomics",       "chain": "Ethereum",        "value": 240.34},
    {"token": "JUP",   "cluster": "Solana DeFi",        "chain": "Solana",          "value": 153.78},
    {"token": "USDT",  "cluster": "Стейблкоины",        "chain": "Arbitrum",        "value": 100.05},
    {"token": "LDO",   "cluster": "Стейкинг",           "chain": "Ethereum",        "value": 98.75},
    {"token": "PONS",  "cluster": "Robinhood Chain",    "chain": "Robinhood Chain", "value": 97.22},
    {"token": "INDEX", "cluster": "Robinhood Chain",    "chain": "Robinhood Chain", "value": 88.22},
    {"token": "ARB",   "cluster": "L2 / инфра",         "chain": "Arbitrum",        "value": 63.73},
    {"token": "STRK",  "cluster": "L2 / инфра",         "chain": "Starknet",        "value": 59.72},
    {"token": "APT",   "cluster": "L2 / инфра",         "chain": "Aptos",           "value": 18.90},
    {"token": "ZK",    "cluster": "L2 / инфра",         "chain": "zkSync",          "value": 18.89},
    {"token": "PYTH",  "cluster": "Solana DeFi",        "chain": "Solana",          "value": 13.39},
    {"token": "W",     "cluster": "L2 / инфра",         "chain": "Wormhole",        "value": 11.19},
    {"token": "PEPE",  "cluster": "Мемы",               "chain": "Ethereum",        "value": 1.86},
    {"token": "DEGEN", "cluster": "Мемы",               "chain": "Base",            "value": 0.81},
]

# Параметры позиции в Aave (Arbitrum). Значения по умолчанию — текущее состояние.
AAVE_PARAMS: dict = {
    "protocol": "Aave v3",
    "chain": "Arbitrum",
    "collateral": ["ETH", "BTC"],
    "debt_asset": "USDT/USDC",
    "hf": 1.65,
    "lt": 0.80,
    # Ставка займа по стейблам на Aave v3 Arbitrum ≈4,25% (LlamaRisk, ноябрь 2026).
    "borrow_apy": 4.25,
    "farm_apy": 11.0,
}

# Пороги, при которых дашборд ругается.
THRESHOLDS: dict = {
    "max_single_share": 40.0,   # доля одного актива, %
    "min_stable_share": 10.0,   # минимальная доля стейблов, %
    "dust_limit": 100.0,        # позиция «пыль», $
    "min_net_carry": 5.0,       # чистый карри (фарм - займ), п.п.
    "hf_watch": 1.5,            # уровень, на котором принимаем решение
    "hf_action": 1.4,           # уровень, на котором действуем
}
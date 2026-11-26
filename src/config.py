"""Настройки дашборда: тестовые данные портфеля и пороги риска.

Здесь живёт всё, что пользователь может менять руками:
состав портфеля (пока тестовый), параметры займа и пороги предупреждений.
"""

from __future__ import annotations

# Версия приложения: меняется при правках, чтобы Streamlit Cloud точно
# перезапустил процесс, а не только перечитал скрипт (иначе в sys.modules
# остаются старые модули из src/ и падает с TypeError).
APP_VERSION = "1.5.3"

# Портфель: количества из снимка CoinMarketCap + id монет в CMC.
# Цены подтягиваются по id (а не по тикеру) — тикеры в CMC не уникальны.
# value — стоимость на момент снимка, нужна только если цену получить не удалось.
PORTFOLIO: list[dict] = [
    {"token": "ETH",   "cluster": "Мейджоры",        "chain": "Ethereum",        "cmc_id": 1027,  "qty": 1.2963,      "value": 2283.15},
    {"token": "BTC",   "cluster": "Мейджоры",        "chain": "Ethereum",        "cmc_id": 1,     "qty": 0.0127,      "value": 787.64},
    {"token": "AERO",  "cluster": "veTokenomics",    "chain": "Base",            "cmc_id": 29270, "qty": 894.8856,    "value": 383.19},
    {"token": "HYPE",  "cluster": "DeFi-инфра",      "chain": "Hyperliquid",     "cmc_id": 32196, "qty": 4.7675,      "value": 312.51},
    {"token": "CVX",   "cluster": "veTokenomics",    "chain": "Ethereum",        "cmc_id": 9903,  "qty": 241.38,      "value": 291.41},
    {"token": "CRV",   "cluster": "veTokenomics",    "chain": "Ethereum",        "cmc_id": 6538,  "qty": 1285.9283,   "value": 240.34},
    {"token": "JUP",   "cluster": "Solana DeFi",     "chain": "Solana",          "cmc_id": 29210, "qty": 621.0824,    "value": 153.78},
    {"token": "USDT",  "cluster": "Стейблкоины",     "chain": "Arbitrum",        "cmc_id": 825,   "qty": 100.1602,    "value": 100.05},
    {"token": "LDO",   "cluster": "Стейкинг",        "chain": "Ethereum",        "cmc_id": 8000,  "qty": 399.7976,    "value": 98.75},
    {"token": "PONS",  "cluster": "Robinhood Chain", "chain": "Robinhood Chain", "cmc_id": 40938, "qty": 1014.8225,   "value": 97.22},
    {"token": "INDEX", "cluster": "Robinhood Chain", "chain": "Robinhood Chain", "cmc_id": 40859, "qty": 19418.8862,  "value": 88.22},
    {"token": "ARB",   "cluster": "L2 / инфра",      "chain": "Arbitrum",        "cmc_id": 11841, "qty": 551.7749,    "value": 63.73},
    {"token": "STRK",  "cluster": "L2 / инфра",      "chain": "Starknet",        "cmc_id": 22691, "qty": 1845.4883,   "value": 59.72},
    {"token": "APT",   "cluster": "L2 / инфра",      "chain": "Aptos",           "cmc_id": 21794, "qty": 48.0427,     "value": 18.90},
    {"token": "ZK",    "cluster": "L2 / инфра",      "chain": "zkSync",          "cmc_id": 24091, "qty": 2676.7748,   "value": 18.89},
    {"token": "PYTH",  "cluster": "Solana DeFi",     "chain": "Solana",          "cmc_id": 28177, "qty": 254.5627,    "value": 13.39},
    {"token": "W",     "cluster": "L2 / инфра",      "chain": "Wormhole",        "cmc_id": 29587, "qty": 1301.9197,   "value": 11.19},
    {"token": "PEPE",  "cluster": "Мемы",            "chain": "Ethereum",        "cmc_id": 24478, "qty": 347022.5873, "value": 1.86},
    {"token": "DEGEN", "cluster": "Мемы",            "chain": "Base",            "cmc_id": 30096, "qty": 1129.4413,   "value": 0.81},
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
    "pie_dust": 10.0,           # на круговой диаграмме всё дешевле этого уходит в «прочее», $
    "min_net_carry": 5.0,       # чистый карри (фарм - займ), п.п.
    "hf_watch": 1.5,            # уровень, на котором принимаем решение
    "hf_action": 1.4,           # уровень, на котором действуем
}
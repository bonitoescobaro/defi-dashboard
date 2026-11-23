"""Чтение кошелька и позиции Aave напрямую через JSON-RPC.

Без web3: только eth_call и ручная упаковка calldata. Так меньше зависимостей
и понятно, что именно отправляется в сеть.
"""

from __future__ import annotations

import re
from decimal import Decimal

import requests

# Публичные RPC, по несколько на сеть: если первый не ответил, пробуем следующий.
# Свои платные (Alchemy/QuickNode) лучше держать первыми — они стабильнее.
RPC: dict[str, list[str]] = {
    "arbitrum": [
        "https://arb1.arbitrum.io/rpc",
        "https://arbitrum-one-rpc.publicnode.com",
        "https://arbitrum.drpc.org",
    ],
    "ethereum": [
        "https://ethereum-rpc.publicnode.com",
        "https://eth.drpc.org",
    ],
    "base": [
        "https://mainnet.base.org",
        "https://base.drpc.org",
    ],
    "robinhood": [
        "https://rpc.mainnet.chain.robinhood.com",
    ],
    "hyperliquid": [
        "https://rpc.hyperliquid.xyz/evm",
    ],
}

# Aave v3 Pool (одинаковый адрес в Arbitrum и Base — проверять при смене сети).
AAVE_V3_POOL: dict[str, str] = {
    "arbitrum": "0x794a61358D6845594F94dc1DB02A252b5b4814aD",
    "base": "0xA238Dd80C259a72e81d7e4664a9801593F98d1c5",
}

# Селекторы функций
_SEL_BALANCE_OF = "0x70a08231"          # balanceOf(address)
_SEL_ACCOUNT_DATA = "0xbf92857c"        # getUserAccountData(address)

_ADDRESS_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")


def is_address(value: str) -> bool:
    return bool(_ADDRESS_RE.match((value or "").strip()))


def _rpc(urls, method: str, params: list, timeout: int = 10) -> str:
    """Пробует RPC по очереди, пока один не ответит."""
    if isinstance(urls, str):
        urls = [urls]
    last_error: Exception | None = None
    for url in urls:
        try:
            resp = requests.post(
                url,
                json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
                timeout=timeout,
            )
            resp.raise_for_status()
            payload = resp.json()
            if "error" in payload:
                raise RuntimeError(payload["error"].get("message", "RPC error"))
            return payload["result"]
        except Exception as exc:  # таймаут, 429, 5xx — идём к следующему RPC
            last_error = exc
            continue
    raise RuntimeError(f"Все RPC недоступны: {last_error}")


def _pad_address(address: str) -> str:
    return address.lower().replace("0x", "").rjust(64, "0")


def native_balance(address: str, chain: str = "arbitrum") -> Decimal:
    """Баланс нативного токена (ETH) в единицах токена."""
    if not is_address(address):
        raise ValueError("Некорректный адрес кошелька")
    result = _rpc(RPC[chain], "eth_getBalance", [address, "latest"])
    return Decimal(int(result, 16)) / Decimal(10**18)


def erc20_balance(
    token: str, address: str, decimals: int, chain: str = "arbitrum"
) -> Decimal:
    """Баланс ERC-20 через balanceOf."""
    if not is_address(address) or not is_address(token):
        raise ValueError("Некорректный адрес кошелька или токена")
    data = _SEL_BALANCE_OF + _pad_address(address)
    result = _rpc(RPC[chain], "eth_call", [{"to": token, "data": data}, "latest"])
    return Decimal(int(result, 16)) / Decimal(10**decimals)


def aave_account(address: str, chain: str = "arbitrum") -> dict:
    """Данные аккаунта в Aave v3: залог, долг, порог ликвидации, health factor.

    Возвращает значения в человеческих единицах (USD, доля, HF).
    """
    if not is_address(address):
        raise ValueError("Некорректный адрес кошелька")
    pool = AAVE_V3_POOL[chain]
    data = _SEL_ACCOUNT_DATA + _pad_address(address)
    result = _rpc(RPC[chain], "eth_call", [{"to": pool, "data": data}, "latest"])

    raw = result.replace("0x", "")
    words = [int(raw[i : i + 64], 16) for i in range(0, 6 * 64, 64)]
    collateral, debt, _available, lt_bps, _ltv, hf = words

    return {
        "collateral_usd": collateral / 1e8,
        "debt_usd": debt / 1e8,
        "liquidation_threshold": lt_bps / 1e4,
        "health_factor": hf / 1e18,
        "has_debt": debt > 0,
        "chain": chain,
    }
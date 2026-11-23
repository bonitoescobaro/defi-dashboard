"""Нативные балансы по сетям и аккаунт Hyperliquid.

ERC-20 токены сюда пока не входят: список контрактов пришлось бы
подтверждать руками (одинаковые тикеры на разных цепях — частая ловушка).
Нативные ETH/HYPE дают основную часть стоимости без риска ошибиться.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import requests

from .wallet import RPC, _rpc

# Что считается нативным активом сети
NATIVE: dict[str, str] = {
    "arbitrum": "ETH",
    "ethereum": "ETH",
    "base": "ETH",
    "robinhood": "ETH",
    "hyperliquid": "HYPE",
}

HYPERLIQUID_INFO = "https://api.hyperliquid.xyz/info"


def _one(chain: str, symbol: str, address: str) -> dict:
    try:
        raw = _rpc(RPC[chain], "eth_getBalance", [address, "latest"], timeout=6)
        amount = Decimal(int(raw, 16)) / Decimal(10**18)
        error = None
    except Exception as exc:
        amount, error = Decimal(0), str(exc)[:80]
    return {"chain": chain, "symbol": symbol, "address": address,
            "amount": amount, "error": error}


def native_balances(addresses: list[str]) -> list[dict]:
    """Баланс нативного токена по каждому адресу в каждой сети (параллельно)."""
    tasks = [(chain, symbol, address)
             for chain, symbol in NATIVE.items()
             for address in addresses]
    if not tasks:
        return []
    with ThreadPoolExecutor(max_workers=8) as pool:
        return list(pool.map(lambda t: _one(*t), tasks))


def hyperliquid_account(address: str, timeout: int = 10, attempts: int = 2) -> dict:
    """Состояние perp-аккаунта на Hyperliquid (HyperCore).

    Возвращает стоимость аккаунта, доступное к выводу и список позиций.
    """
    last_error: Exception | None = None
    data = None
    for _ in range(attempts):
        try:
            resp = requests.post(
                HYPERLIQUID_INFO,
                json={"type": "clearinghouseState", "user": address},
                timeout=timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            break
        except Exception as exc:  # таймаут — пробуем ещё раз
            last_error = exc
    if data is None:
        raise RuntimeError(f"Hyperliquid API недоступен: {last_error}")
    summary = data.get("marginSummary") or {}
    positions = []
    for item in data.get("assetPositions") or []:
        pos = item.get("position") or {}
        size = float(pos.get("szi") or 0)
        if size == 0:
            continue
        positions.append(
            {
                "coin": pos.get("coin"),
                "size": size,
                "entry_px": pos.get("entryPx"),
                "unrealized_pnl": float(pos.get("unrealizedPnl") or 0),
                "leverage": (pos.get("leverage") or {}).get("value"),
            }
        )
    return {
        "account_value": float(summary.get("accountValue") or 0),
        "margin_used": float(summary.get("totalMarginUsed") or 0),
        "withdrawable": float(data.get("withdrawable") or 0),
        "positions": positions,
    }


def hyperliquid_totals(addresses: list[str]) -> dict:
    total = 0.0
    accounts = []
    errors = []
    for address in addresses:
        try:
            acc = hyperliquid_account(address)
            acc["address"] = address
            accounts.append(acc)
            total += acc["account_value"]
        except Exception as exc:
            errors.append(f"{address[:10]}…: {exc}")
    return {"total_value": total, "accounts": accounts, "errors": errors}
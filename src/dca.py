"""DCA-калькулятор: раскладка бюджета по уровням просадки.

Логика простая и явная:
- уровни задаются как падение от стартовой цены (10%, 20%, …);
- бюджет делится между уровнями по выбранной схеме (равномерно или с усилением
  на глубоких уровнях);
- уровень считается пройденным, если текущая цена уже ниже его цены;
- сумма пройденных уровней — «купить сейчас», остальное — резерв.

Ничего не округляется втихую: все числа возвращаются как есть, а форматирование
делает интерфейс.
"""

from __future__ import annotations

SCHEMES: dict[str, list[float]] = {
    "равномерно": [1.0, 1.0, 1.0, 1.0, 1.0],
    "с усилением на глубоких": [1.0, 1.5, 2.0, 3.0, 4.0],
}


def parse_levels(text: str) -> list[float]:
    """«10, 20, 30, 50, 70» → [10.0, 20.0, 30.0, 50.0, 70.0] (по возрастанию)."""
    out: list[float] = []
    for chunk in str(text).replace(";", ",").split(","):
        chunk = chunk.strip().rstrip("%").strip()
        if not chunk:
            continue
        try:
            value = float(chunk)
        except ValueError:
            continue
        if 0 < value < 100:
            out.append(value)
    return sorted(set(out))


def _weights(scheme: str, n: int) -> list[float]:
    """Нормированные веса под количество уровней."""
    base = SCHEMES.get(scheme) or SCHEMES["равномерно"]
    if n <= 0:
        return []
    if n <= len(base):
        raw = base[:n]
    else:  # больше уровней, чем в шаблоне — добиваем последним весом
        raw = base + [base[-1]] * (n - len(base))
    total = sum(raw)
    return [w / total for w in raw]


def dca_plan(
    start_price: float,
    current_price: float,
    budget: float,
    drops: list[float],
    scheme: str = "равномерно",
) -> dict:
    """План докупки.

    Возвращает словарь: уровни, сумму «купить сейчас», резерв, среднюю цену,
    количество монет и текущую просадку от стартовой цены.
    """
    if start_price <= 0 or current_price <= 0:
        raise ValueError("Цены должны быть больше нуля")
    if budget <= 0:
        raise ValueError("Бюджет должен быть больше нуля")

    drops = sorted(set(d for d in drops if 0 < d < 100))
    weights = _weights(scheme, len(drops))

    levels: list[dict] = []
    spend_now = 0.0
    for drop, weight in zip(drops, weights):
        price = start_price * (1 - drop / 100)
        allocation = budget * weight
        passed = current_price <= price
        if passed:
            spend_now += allocation
        levels.append(
            {
                "drop_pct": drop,
                "price": price,
                "allocation": allocation,
                "qty": allocation / price,
                "passed": passed,
                # сколько ещё должна упасть цена, чтобы уровень сработал
                "distance_pct": max(0.0, (current_price - price) / current_price * 100),
                "share_pct": weight * 100,
            }
        )

    coins_total = sum(l["qty"] for l in levels)
    avg_price = budget / coins_total if coins_total else 0.0

    return {
        "levels": levels,
        "budget": budget,
        "start_price": start_price,
        "current_price": current_price,
        "scheme": scheme,
        "spend_now": spend_now,
        "reserve": budget - spend_now,
        "qty_total": coins_total,
        "avg_price": avg_price,
        "current_drop_pct": (start_price - current_price) / start_price * 100,
    }


def average_after_add(
    qty: float, avg_price: float, add_usd: float, price: float
) -> dict:
    """Новая средняя цена после покупки на add_usd по цене price."""
    if qty < 0 or avg_price <= 0 or price <= 0:
        raise ValueError("Количество должно быть ≥ 0, цены — больше нуля")
    spend = qty * avg_price
    added_qty = add_usd / price if add_usd > 0 else 0.0
    new_qty = qty + added_qty
    new_avg = (spend + add_usd) / new_qty if new_qty else 0.0
    return {
        "qty": new_qty,
        "added_qty": added_qty,
        "avg_price": new_avg,
        "avg_change": new_avg - avg_price,
        "spend": spend + add_usd,
        "value": new_qty * price,
    }


def add_options(
    qty: float,
    avg_price: float,
    price: float,
    amounts: tuple[float, ...] = (300, 500, 1000, 1500, 2000),
) -> list[dict]:
    """Варианты долива: что станет со средней при разных суммах."""
    rows = []
    for amount in amounts:
        res = average_after_add(qty, avg_price, amount, price)
        rows.append({"amount": amount, **res})
    return rows
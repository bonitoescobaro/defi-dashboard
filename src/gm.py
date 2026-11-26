"""GM-калькулятор: продажа пуловых токенов (GM) по уровням цены.

Логика уровней:
- уровни задаются в процентах от входной цены и работают в обе стороны
  (рост — лестница фиксации, падение — сокращение риска);
- схема «кумулятивно»: к уровню X% продано суммарно X% исходной позиции
  (между уровнями продаётся разница);
- схема «равными долями»: на каждом уровне продаётся 1/n исходной позиции.

Текущая цена нужна, чтобы показать, какие уровни уже пройдены.
"""

from __future__ import annotations

SCHEMES = ("кумулятивно", "равными долями")


def gm_ladder(
    entry_price: float,
    current_price: float,
    qty: float,
    levels: list[float],
    direction: str = "рост",
    scheme: str = "кумулятивно",
) -> dict:
    """План продажи GM по уровням.

    Возвращает строки по уровням и итоги: сколько продать сейчас, что осталось,
    средняя цена продажи по пройденным уровням.
    """
    if entry_price <= 0 or current_price <= 0:
        raise ValueError("Цены должны быть больше нуля")
    if qty <= 0:
        raise ValueError("Количество GM должно быть больше нуля")

    levels = sorted(set(l for l in levels if 0 < l < 100))
    if not levels:
        raise ValueError("Нужен хотя бы один уровень, например: 10, 30, 50, 70")

    step = 100.0 / len(levels)
    rows: list[dict] = []
    prev_share = 0.0

    for level in levels:
        price = entry_price * (1 + level / 100 if direction == "рост" else 1 - level / 100)

        if scheme == "равными долями":
            share = step
        else:  # кумулятивно
            share = level - prev_share

        share = max(0.0, min(share, 100.0 - prev_share))
        sell_qty = qty * share / 100
        passed = (
            current_price >= price if direction == "рост" else current_price <= price
        )
        rows.append(
            {
                "level": level,
                "price": price,
                "share_pct": share,
                "cumulative_pct": prev_share + share,
                "sell_qty": sell_qty,
                "sold_cum": qty * (prev_share + share) / 100,
                "remaining": qty * (1 - (prev_share + share) / 100),
                "revenue": sell_qty * price,
                "pnl": sell_qty * (price - entry_price),
                "passed": passed,
            }
        )
        prev_share += share

    passed_rows = [r for r in rows if r["passed"]]
    sell_now = sum(r["sell_qty"] for r in passed_rows)
    revenue_now = sum(r["revenue"] for r in passed_rows)
    qty_sold_now = sell_now
    avg_sell = revenue_now / qty_sold_now if qty_sold_now else 0.0

    return {
        "rows": rows,
        "entry_price": entry_price,
        "current_price": current_price,
        "qty": qty,
        "direction": direction,
        "scheme": scheme,
        "sell_now": sell_now,
        "remaining_now": qty - qty_sold_now,
        "revenue_now": revenue_now,
        "avg_sell_price": avg_sell,
        "sold_pct": qty_sold_now / qty * 100,
        "change_pct": (current_price / entry_price - 1) * 100,
    }
"""Сценарный анализ: что будет с health factor при падении залога.

HF пропорционален стоимости залога при неизменном долге:
    HF_new = HF * (1 − drop * доля_актива_в_залоге)
Поэтому считаем не «на глаз», а одной формулой и показываем таблицей.
"""

from __future__ import annotations

# Зоны риска: (верхняя граница HF, название, что делать)
ZONES: list[tuple[float, str, str]] = [
    (1.0, "🔴 ликвидация", "HF ниже 1.0 — позицию закрывают"),
    (1.2, "🟠 критично", "гасить долг немедленно"),
    (1.4, "🟡 действовать", "порог правила: гасим часть долга или докидываем залог"),
    (1.5, "🟡 внимание", "готовим план, следим за ценой"),
    (float("inf"), "🟢 норма", "в запасе"),
]


def zone(hf: float) -> tuple[str, str]:
    """Возвращает (метка зоны, что делать) для текущего HF."""
    for limit, label, action in ZONES:
        if hf < limit:
            return label, action
    return "🟢 норма", "в запасе"


def hf_after_drop(hf: float, drop_pct: float, share: float = 1.0) -> float:
    """HF после падения залога на drop_pct процентов.

    share — какая доля залога (0..1) зависит от этого актива.
    При share=1 падает весь залог, при 0.5 — только половина.
    """
    factor = 1 - (drop_pct / 100.0) * share
    return hf * factor if factor > 0 else 0.0


def eth_shock_table(
    hf: float,
    eth_price: float,
    btc_price: float | None = None,
    share: float = 1.0,
    drops: tuple[int, ...] = (10, 20, 30, 40, 50),
) -> list[dict]:
    """Строки для таблицы: падение, цены ETH и BTC на этом уровне, новый HF, зона.

    BTC считается падающим на тот же процент, что и ETH — так таблица отвечает
    на вопрос «где окажется цена и HF, если крипто-часть залога просядет на X%».
    """
    rows: list[dict] = []
    for drop in drops:
        new_hf = hf_after_drop(hf, drop, share)
        label, action = zone(new_hf)
        row = {
            "Падение": f"−{drop}%",
            "Цена ETH": f"${eth_price * (1 - drop / 100):,.0f}",
        }
        if btc_price:
            row["Цена BTC"] = f"${btc_price * (1 - drop / 100):,.0f}"
        row.update(
            {
                "Новый HF": f"{new_hf:.2f}",
                "Зона": label,
                "Что делать": action,
            }
        )
        rows.append(row)
    return rows


def critical_drops(hf: float, share: float = 1.0) -> dict[str, float | None]:
    """На каком падении HF дойдёт до 1.5 / 1.4 / 1.2 / 1.0 (в процентах)."""
    out: dict[str, float | None] = {}
    for target in (1.5, 1.4, 1.2, 1.0):
        if hf <= target:
            out[f"hf_{target}"] = 0.0  # уже там
            continue
        drop = (1 - target / hf) * 100 / share if share > 0 else None
        out[f"hf_{target}"] = round(drop, 1) if drop is not None else None
    return out
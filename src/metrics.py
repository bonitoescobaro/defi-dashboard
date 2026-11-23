"""Расчёты: доли, риск лендинга, карри."""

from __future__ import annotations

import pandas as pd


def allocations(df: pd.DataFrame) -> tuple[pd.DataFrame, float]:
    """Добавляет колонку share_pct и возвращает (df, total)."""
    out = df.copy()
    total = float(out["value"].sum())
    out["share_pct"] = out["value"] / total * 100 if total else 0.0
    return out.sort_values("value", ascending=False).reset_index(drop=True), total


def cluster_summary(df_with_share: pd.DataFrame) -> pd.DataFrame:
    """Сумма по кластерам в деньгах и процентах."""
    g = (
        df_with_share.groupby("cluster", as_index=False)
        .agg(value=("value", "sum"), share_pct=("share_pct", "sum"))
        .sort_values("value", ascending=False)
    )
    return g.reset_index(drop=True)


def drop_to_hf(hf: float, target: float) -> float:
    """На сколько процентов должен упасть залог, чтобы HF дошёл до target."""
    if hf <= 0:
        return 0.0
    return max(0.0, (1 - target / hf) * 100)


def health_factor_report(hf: float, lt: float) -> dict:
    """Ключевые числа по позиции в лендинге."""
    return {
        "hf": hf,
        "lt": lt,
        "debt_to_collateral_pct": lt / hf * 100,  # долг как % от залога
        "drop_to_liquidation_pct": drop_to_hf(hf, 1.0),
        "drop_to_15_pct": drop_to_hf(hf, 1.5),
        "drop_to_14_pct": drop_to_hf(hf, 1.4),
    }


def carry_report(farm_apy: float, borrow_apy: float) -> dict:
    """Чистый карри: доходность фарма минус стоимость займа."""
    net = farm_apy - borrow_apy
    return {
        "farm_apy": farm_apy,
        "borrow_apy": borrow_apy,
        "net_apy": net,
        "positive": net > 0,
        "gross_yield_on_debt_month": farm_apy / 12,
        "cost_of_debt_month": borrow_apy / 12,
    }


def dust(df_with_share: pd.DataFrame, limit: float) -> pd.DataFrame:
    """Позиции дешевле порога — «пыль»."""
    return df_with_share[df_with_share["value"] < limit].sort_values("value")
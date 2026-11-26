"""DeFi Dashboard — цены, портфель на кошельках, Aave, Hyperliquid, карри.

Запуск:  streamlit run app.py
"""

from __future__ import annotations

import os
import re
from datetime import datetime, timedelta, timezone

import altair as alt
import pandas as pd
import streamlit as st

from src.chains import hyperliquid_totals, native_balances
from src.config import AAVE_PARAMS, APP_VERSION, THRESHOLDS
from src.data import portfolio_snapshot
from src.env import get
from src.metrics import (
    allocations,
    carry_report,
    dust,
    health_factor_report,
)
from src.prices import get_quotes_by_ids
from src.scenarios import critical_drops, eth_shock_table, hf_after_drop
from src.wallet import RPC, aave_account, is_address

MAIN_ASSETS = ("BTC", "ETH", "HYPE")
MAIN_ASSET_IDS = (1, 1027, 32196)  # id монет в CoinMarketCap

st.set_page_config(page_title="DeFi Dashboard", page_icon="📊", layout="wide")


# ------------------------------------------------------------------ секреты
def seed_env_from_secrets() -> None:
    """На Streamlit Cloud нет .env — значения приходят из st.secrets."""
    try:
        secrets = dict(st.secrets)
    except Exception:
        return
    for key in ("CMC_API_KEY", "WALLET_ADDRESSES", "APP_PASSWORD"):
        if secrets.get(key) and not os.environ.get(key):
            os.environ[key] = str(secrets[key])


seed_env_from_secrets()


# ------------------------------------------------------------------ пароль
def require_password() -> None:
    """Простая защита: если в secrets задан APP_PASSWORD, просим его ввести."""
    try:
        expected = st.secrets.get("APP_PASSWORD", "")
    except Exception:
        expected = ""
    if not expected:
        return
    if st.session_state.get("authed"):
        return
    st.title("DeFi Dashboard")
    entered = st.text_input("Пароль", type="password")
    if st.button("Войти"):
        if entered == expected:
            st.session_state["authed"] = True
            st.rerun()
        st.error("Неверный пароль")
    st.stop()


require_password()


# ------------------------------------------------------------------ кэш
@st.cache_data(ttl=1800, show_spinner=False)
def cached_quotes(ids: tuple[int, ...]) -> tuple[dict, str | None]:
    """Цены главных активов по id, разложенные по тикерам."""
    raw, err = get_quotes_by_ids(list(ids))
    return ({v["symbol"]: v for v in raw.values()}, err)


@st.cache_data(ttl=300, show_spinner=False)
def cached_native(addresses: tuple[str, ...]) -> list[dict]:
    return native_balances(list(addresses))


@st.cache_data(ttl=60, show_spinner=False)
def cached_hl(addresses: tuple[str, ...]) -> dict:
    return hyperliquid_totals(list(addresses))


@st.cache_data(ttl=30, show_spinner=False)
def cached_aave(address: str, chain: str) -> dict:
    return aave_account(address, chain)


st.title("DeFi Dashboard")

# ------------------------------------------------------------------ цены
quotes, price_error = cached_quotes(MAIN_ASSET_IDS)
if price_error:
    st.warning(price_error)

if quotes:
    cols = st.columns(len(MAIN_ASSETS))
    for col, symbol in zip(cols, MAIN_ASSETS):
        q = quotes.get(symbol)
        if not q:
            col.metric(symbol, "—")
            continue
        col.metric(symbol, f"${q['price']:,.2f}", f"{q['change_24h']:+.2f}% за 24ч")
    st.caption("Цены — CoinMarketCap, кэш 30 минут.")

# ------------------------------------------------------------------ сайдбар
with st.sidebar:
    st.header("Кошельки")
    default_addresses = get("WALLET_ADDRESSES") or get("WALLET_ADDRESS")
    raw_addresses = st.text_area(
        "Адреса (по одному в строке)",
        value=default_addresses.replace(",", "\n"),
        height=90,
        help="Публичные EVM-адреса. Приватные ключи не нужны и не запрашиваются.",
    )
    parsed = [a.strip() for a in re.split(r"[\s,;]+", raw_addresses) if a.strip()]
    addresses = [a for a in parsed if is_address(a)]
    if bad := [a for a in parsed if not is_address(a)]:
        st.warning(f"Похоже на опечатку: {', '.join(bad)}")

    chain = st.selectbox("Сеть для Aave", options=list(RPC.keys()), index=0)
    use_chain = st.checkbox("Брать HF и суммы из сети", value=bool(addresses))

    st.header("Параметры позиции")
    hf_manual = st.number_input(
        "Health factor (вручную)", min_value=1.0, max_value=10.0,
        value=float(AAVE_PARAMS["hf"]), step=0.01, disabled=use_chain and bool(addresses),
    )
    lt_manual = st.number_input(
        "Liquidation threshold", min_value=0.50, max_value=0.95,
        value=float(AAVE_PARAMS["lt"]), step=0.005, disabled=use_chain and bool(addresses),
    )
    borrow_apy = st.number_input(
        "Ставка займа, % годовых", min_value=0.0, max_value=100.0,
        value=float(AAVE_PARAMS["borrow_apy"]), step=0.1,
    )
    farm_apy = st.number_input(
        "Доходность фарма, % годовых", min_value=0.0, max_value=300.0,
        value=float(AAVE_PARAMS["farm_apy"]), step=0.1,
    )
    st.divider()
    st.caption(
        f"{AAVE_PARAMS['protocol']} · {AAVE_PARAMS['chain']}  \n"
        f"Залог: {', '.join(AAVE_PARAMS['collateral'])}  \n"
        f"Долг: {AAVE_PARAMS['debt_asset']}"
    )

# ------------------------------------------------------------------ данные с сети
native_rows: list[dict] = []
aave_rows: list[dict] = []
hl = {"total_value": 0.0, "accounts": [], "errors": []}

if addresses:
    try:
        native_rows = cached_native(tuple(addresses))
    except Exception as exc:
        st.error(f"Балансы: {exc}")

    try:
        hl = cached_hl(tuple(addresses))
    except Exception as exc:
        st.warning(f"Hyperliquid: {exc}")

    if use_chain:
        for address in addresses:
            try:
                acc = cached_aave(address, chain)
                acc["address"] = address
                aave_rows.append(acc)
            except Exception as exc:
                st.sidebar.error(f"Aave {address[:8]}…: {exc}")

with_debt = [r for r in aave_rows if r["has_debt"]]
collateral_usd = sum(r["collateral_usd"] for r in aave_rows)
debt_usd = sum(r["debt_usd"] for r in aave_rows)

if with_debt:
    hf = min(r["health_factor"] for r in with_debt)
    lt = next(r["liquidation_threshold"] for r in with_debt if r["health_factor"] == hf)
else:
    hf, lt = hf_manual, lt_manual

# ------------------------------------------------------------------ кошельки
wallet_usd = 0.0
if native_rows:
    prices = {k: v["price"] for k, v in quotes.items()}
    for r in native_rows:
        if r["amount"] <= 0:
            continue
        wallet_usd += float(r["amount"]) * prices.get(r["symbol"], 0.0)

total = wallet_usd + collateral_usd + float(hl.get("total_value") or 0)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Всего", f"${total:,.0f}")
m2.metric("Залог в Aave", f"${collateral_usd:,.0f}")
m3.metric("Долг в Aave", f"${debt_usd:,.0f}")
m4.metric("Hyperliquid", f"${hl.get('total_value', 0):,.2f}")

if hl.get("positions"):
    with st.expander(f"Позиции Hyperliquid: {len(hl['positions'])}"):
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Монета": p["coin"],
                        "Размер": p["size"],
                        "Вход": p["entry_px"],
                        "PnL": f"${p['unrealized_pnl']:,.2f}",
                        "Плечо": p["leverage"],
                    }
                    for p in hl["positions"]
                ]
            ),
            hide_index=True,
            width="stretch",
        )
for err in hl.get("errors", []):
    st.caption(f"Hyperliquid: {err}")

# ------------------------------------------------------------------ лендинг
hfr = health_factor_report(hf, lt)
carry = carry_report(farm_apy, borrow_apy)

st.subheader("Позиция в лендинге")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Health factor", f"{hf:.2f}", f"запас до 1.0: −{hfr['drop_to_liquidation_pct']:.0f}%")
c2.metric("Долг / залог", f"{hfr['debt_to_collateral_pct']:.0f}%")
c3.metric("Залог", f"${collateral_usd:,.0f}" if aave_rows else "—", f"долг ${debt_usd:,.0f}" if aave_rows else "нет адреса", delta_color="off")
c4.metric(
    "Чистый карри",
    f"{carry['net_apy']:+.1f} п.п.",
    "фарм минус займ",
    delta_color="normal" if carry["positive"] else "inverse",
)

if aave_rows:
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Кошелёк": f"{r['address'][:6]}…{r['address'][-4:]}",
                    "Залог": f"${r['collateral_usd']:,.0f}",
                    "Долг": f"${r['debt_usd']:,.0f}",
                    "LT": f"{r['liquidation_threshold']:.2f}",
                    "HF": f"{r['health_factor']:.2f}" if r["has_debt"] else "—",
                }
                for r in aave_rows
            ]
        ),
        hide_index=True,
        width="stretch",
    )

if hf < THRESHOLDS["hf_watch"]:
    st.error(
        f"HF {hf:.2f} ниже рабочего уровня {THRESHOLDS['hf_watch']}: "
        f"до HF {THRESHOLDS['hf_action']} осталось −{hfr['drop_to_14_pct']:.0f}% по залогу. "
        "Пора гасить часть долга или докидывать залог."
    )

if not carry["positive"]:
    st.error("Карри отрицательный: фарм даёт меньше, чем стоит долг. Конструкция тихо теряет деньги.")
elif carry["net_apy"] < THRESHOLDS["min_net_carry"]:
    st.warning(
        f"Чистый карри {carry['net_apy']:.1f} п.п. ниже порога "
        f"{THRESHOLDS['min_net_carry']:.0f} п.п. — риск не окупается доходностью."
    )
else:
    st.success(f"Карри {carry['net_apy']:.1f} п.п. — конструкция работает в плюс.")

st.subheader("Расстояние до ликвидации")
l1, l2, l3 = st.columns(3)
l1.metric("До HF 1.0", f"−{hfr['drop_to_liquidation_pct']:.0f}%")
l2.metric("До HF 1.5", f"−{hfr['drop_to_15_pct']:.0f}%")
l3.metric("До HF 1.4", f"−{hfr['drop_to_14_pct']:.0f}%")
st.caption(
    "Проценты — падение стоимости залога, при котором HF дойдёт до уровня. "
    "Долг считается как LT / HF от залога."
)

# ------------------------------------------------------------------ сценарий ETH
st.subheader("Сценарий: ETH и BTC падают")
st.caption(
    "HF = HF × (1 − падение × доля крипто-части залога). Оба актива считаются "
    "падающими на одинаковый процент, долг — неизменным."
)

eth_price_default = float((quotes.get("ETH") or {}).get("price") or 1700.0)
btc_price_default = float((quotes.get("BTC") or {}).get("price") or 60000.0)
sc1, sc2 = st.columns([1, 3])
with sc1:
    eth_price = st.number_input(
        "Текущая цена ETH", min_value=1.0, value=eth_price_default, step=10.0,
        help="Подставляется из CoinMarketCap, можно поправить вручную.",
    )
    btc_price = st.number_input(
        "Текущая цена BTC", min_value=1.0, value=btc_price_default, step=100.0,
        help="В таблице BTC падает на тот же процент, что и ETH.",
    )
    eth_share_pct = st.slider(
        "Доля крипто-части в залоге, %", min_value=10, max_value=100, value=100, step=5,
        help="Если в залоге только ETH и WBTC — 100%. Если половина залога в стейблах — ~50%.",
    )

with sc2:
    try:
        rows = eth_shock_table(hf, eth_price, btc_price, eth_share_pct / 100)
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    except Exception as exc:  # блок не должен ронять всю страницу
        st.error(f"Сценарий не посчитался: {exc}")

    crit = critical_drops(hf, eth_share_pct / 100)
    parts = []
    for target, label in ((1.5, "HF 1.5"), (1.4, "HF 1.4"), (1.0, "ликвидации")):
        value = crit.get(f"hf_{target}")
        if value is None:
            continue
        parts.append(f"{label} — падение на {value:.0f}%" if value > 0 else f"{label} — уже пройден")
    note = " · ".join(parts)
    st.caption(
        f"До {note}. При доле крипто-части {eth_share_pct}% остальное в залоге "
        "(стейблы) считается устойчивым."
    )

    chart = pd.DataFrame(
        {
            "Падение ETH, %": [10, 20, 30, 40, 50],
            "HF": [hf_after_drop(hf, d, eth_share_pct / 100) for d in (10, 20, 30, 40, 50)],
        }
    ).set_index("Падение ETH, %")
    st.line_chart(chart, height=260)

# ------------------------------------------------------------------ портфель (живые цены CMC)
@st.cache_data(ttl=10800, show_spinner=False)
def cached_portfolio() -> tuple[pd.DataFrame, float, str | None, str | None]:
    """Портфель с ценами CoinMarketCap. Кэш 3 часа: несколько обновлений в сутки."""
    return portfolio_snapshot()


def _msk_stamp(value: str | None) -> str:
    """Время CMC (UTC) → «25.11 14:20 МСК»."""
    if not value:
        return "—"
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(
            timezone(timedelta(hours=3))
        )
        return dt.strftime("%d.%m %H:%M МСК")
    except Exception:
        return str(value)


@st.fragment(run_every="3h")
def render_portfolio() -> None:
    raw, total, stamp, err = cached_portfolio()
    if err:
        st.warning(err)

    df, total = allocations(raw)

    head, btn = st.columns([5, 1])
    head.subheader(f"Портфель по CoinMarketCap — ${total:,.0f}")
    btn.button("Обновить", on_click=cached_portfolio.clear, width="stretch")
    st.caption(
        f"Считается как количество × цена CMC, обновление раз в 3 часа. "
        f"Данные на {_msk_stamp(stamp)}."
    )

    left, right = st.columns([3, 2])
    with left:
        view = df.assign(
            Цена=df["price"].map(lambda x: f"${x:,.6f}" if x < 1 else f"${x:,.2f}"),
            Δ24ч=df["change_24h"].map(lambda x: f"{x:+.1f}%"),
            Стоимость=df["value"].map(lambda x: f"${x:,.2f}"),
            Доля=df["share_pct"].map(lambda x: f"{x:.1f}%"),
        )[["token", "cluster", "chain", "Цена", "Δ24ч", "Стоимость", "Доля"]]
        view.columns = ["Токен", "Кластер", "Сеть", "Цена", "Δ24ч", "Стоимость", "Доля"]
        st.dataframe(view, hide_index=True, width="stretch", height=430)

    with right:
        pie_src = df[["token", "cluster", "value", "share_pct"]].copy()
        pie = (
            alt.Chart(pie_src)
            .mark_arc(innerRadius=48, outerRadius=148)
            .encode(
                theta=alt.Theta("value:Q"),
                color=alt.Color(
                    "token:N",
                    legend=alt.Legend(title=None, orient="bottom", columns=3),
                ),
                tooltip=[
                    alt.Tooltip("token:N", title="Токен"),
                    alt.Tooltip("cluster:N", title="Кластер"),
                    alt.Tooltip("value:Q", title="Стоимость, $", format=",.2f"),
                    alt.Tooltip("share_pct:Q", title="Доля, %", format=".1f"),
                ],
            )
            .properties(height=430, title="Доли по токенам")
        )
        st.altair_chart(pie, width="stretch")

    d = dust(df, THRESHOLDS["dust_limit"])
    st.caption(f"Пыль: {len(d)} позиций на ${d['value'].sum():,.0f}.")


render_portfolio()

st.divider()
st.caption(
    f"Версия {APP_VERSION}. Нативные балансы — RPC (Arbitrum, Ethereum, Base, "
    "Robinhood Chain, HyperEVM); HF и залог — Aave v3; перпы — Hyperliquid API."
)
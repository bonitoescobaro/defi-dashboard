# DeFi Dashboard

Дашборд для одной задачи: видеть, что происходит с портфелем, позицией в Aave и
экономикой «занял стейблы → зафармил», без Excel и ручных подсчётов.

## Запуск локально

```bash
cd ~/projects/defi-dashboard
./.venv/Scripts/python -m streamlit run app.py
```

http://localhost:8501

Секреты берутся из `.env` (локально) или из Streamlit Secrets (в облаке):

```
CMC_API_KEY=...
WALLET_ADDRESSES=0x...,0x...
APP_PASSWORD=...      # если задан — приложение спросит пароль
```

## Структура

```
defi-dashboard/
├─ app.py                    # одна страница: вёрстка и порядок блоков
├─ requirements.txt
├─ .streamlit/
│  ├─ config.toml            # тёмная тема, порт, без телеметрии
│  └─ secrets.toml.example   # шаблон секретов (не коммитить настоящий)
└─ src/
   ├─ config.py              # пороги риска, параметры Aave, снимок портфеля
   ├─ env.py                 # чтение .env без внешних библиотек
   ├─ prices.py              # CoinMarketCap: цены BTC/ETH/HYPE
   ├─ wallet.py              # JSON-RPC: баланс, ERC-20, Aave getUserAccountData
   ├─ chains.py              # нативные балансы по 5 сетям, Hyperliquid perp
   ├─ data.py                # портфель из CSV/конфига (снимок CMC)
   └─ metrics.py             # доли, HF, дистанция до ликвидации, карри, пыль
```

Правило: **config — что считаем, data/prices/wallet/chains — откуда берём,
metrics — как считаем, app — как показываем**. Новый источник подключается в
своём модуле, формулы и вёрстка не трогаются.

## Что считается

- цены BTC, ETH, HYPE (CoinMarketCap, кэш 60 с);
- нативные балансы ETH/HYPE по Arbitrum, Ethereum, Base, Robinhood Chain, HyperEVM
  (параллельные RPC-запросы, фолбэк на резервные узлы);
- позиция Aave v3: залог, долг, liquidation threshold, health factor — напрямую
  из контракта Pool (`getUserAccountData`), по каждому кошельку отдельно;
- Hyperliquid: стоимость perp-аккаунта и открытые позиции (публичный info API);
- долг как % от залога: `LT / HF`;
- дистанция до ликвидации: `1 − 1/HF`, и до рабочих уровней HF 1.5 / 1.4;
- чистый карри: `доходность фарма − ставка займа`;
- снимок портфеля из config.py — для сверки, с кластерами и «пылью».

## Ограничения (честно)

- **ERC-20 токены с кошельков пока не читаются.** Нужен источник списка токенов:
  Blockscout/Arbiscan API с ключом или ручной список контрактов. Поэтому сумма
  на экране меньше снимка CMC — разница это AERO/CRV/CVX/JUP и прочие токены.
- Публичные RPC иногда отвечают медленно; для стабильности лучше свой
  Alchemy/QuickNode, он ставится первым в списке `src/wallet.py`.
- Ставка займа и доходность фарма вводятся руками: Aave-ставку можно получить
  из `getReserveData`, доходность фарма — из DeFiLlama Yields.

## Деплой на Streamlit Community Cloud

1. Создать приватный репозиторий на GitHub и запушить:
   ```bash
   cd ~/projects/defi-dashboard
   git remote add origin https://github.com/<логин>/defi-dashboard.git
   git push -u origin main
   ```
2. Зайти на https://share.streamlit.io → **New app** → выбрать репозиторий,
   ветку `main`, файл `app.py`.
3. **Advanced settings → Secrets** — вставить:
   ```toml
   CMC_API_KEY = "..."
   WALLET_ADDRESSES = "0x...,0x..."
   APP_PASSWORD = "..."
   ```
4. Deploy. Ссылка вида `https://<имя>.streamlit.app` открывается с телефона и с
   рабочего компьютера. Пароль спрашивается на входе.

`.env` и `.streamlit/secrets.toml` в `.gitignore` — ключи в репозиторий не попадут.

## Дальше по плану

- ERC-20 сознательно не подключаем: решили жить на нативных балансах плюс снимок
  CMC (список контрактов пришлось бы подтверждать руками);
- автоставка займа из Aave `getReserveData` и доходность пула из DeFiLlama;
- калькулятор «ETH −20% → HF»;
- таблица «кто платит холдерам»: механизм, порог участия, дата выплаты.
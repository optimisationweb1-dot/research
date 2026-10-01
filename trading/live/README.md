# TSMOM 1d — бот для форвард-теста на BingX

Стратегия заморожена в том виде, в каком её тестировали (`strategies/trend_momentum.py::tsmom`, K=72, z0=0,5). Параметры не менять, иначе форвард-тест теряет смысл.

## Правила
- Раз в сутки после закрытия дневной свечи (00:00 UTC) для каждой монеты:
  - σ — стандартное отклонение дневных лог-доходностей за 30 дней;
  - z = ln(C_t / C_{t−72}) / (σ·√72).
- Нет позиции и z > 0,5 → лонг; z < −0,5 → шорт.
- Стоп = цена закрытия ∓ σ·√7 (обычно 6–15%). Сразу ставится на бирже как STOP_MARKET reduce-only.
- Выход: лонг при z < 0, шорт при z > 0 или через 60 дней — рыночный reduce-only ордер.
- Размер: риск RISK_PCT от капитала = qty × |вход − стоп|.
- Ограничители: суммарный риск открытых позиций ≤ MAX_OPEN_RISK_PCT; при просадке от пика > DD_HALT_PCT новые входы прекращаются; файл `live/state/STOP` отключает новые входы.

## Запуск на сервере
```bash
cd ~/research/trading
pip install ccxt
cp live/.env.example live/.env && nano live/.env        # ключи BingX и Telegram
python3 -m live.tsmom_bot --check                        # только чтение: рынки, свечи, баланс, позиции, режим позиций
python3 -m live.tsmom_bot --mode paper                   # бумажная торговля
# реальные деньги: LIVE_CONFIRM=YES в .env, затем
python3 -m live.tsmom_bot --mode live
```
Cron (00:07 UTC каждый день, плюс повтор в 00:37 — повторный запуск ничего не дублирует):
```
7,37 0 * * * cd $HOME/research/trading && /usr/bin/python3 -m live.tsmom_bot --mode live >> live/state/cron.log 2>&1
```
Paper и live можно гонять параллельно, у них разные файлы состояния.

Файлы: `live/state/state_<mode>.json` (позиции), `trades_<mode>.csv` (сделки с R), `bot.log`.

## Что проверено и что нет
- Проверено: z совпадает с бэктестом до 6 знаков; режимы check и paper на публичных данных BingX 30.09.2026; идемпотентный повторный запуск; лимит риска портфеля.
- **Не проверено**: реальные ордера (нет ключей в тестовой среде). Первый live-запуск делать с 1–2 монетами (`SYMBOLS=BTC ETH`) и проверить в интерфейсе BingX, что стоп-ордер появился.
- Если в BingX включён hedge mode, поставить `HEDGE_MODE=1`.
- Стоп срабатывает на бирже по mark price (так ставит ccxt по умолчанию). В бэктесте — по high/low свечи.

---

# Бот «позиции толпы» 4h (только бумага)

Стратегия C_level 4h из `strategies/funding_positioning.py::rcrowd` (src=level, pct=0,9). Параметры заморожены.

Правила:
- На закрытии каждой 4h-свечи берётся ln(Binance global long/short **account** ratio) — последний 5-минутный снимок, не позже чем за 6 минут до закрытия.
- Считается его процентиль среди предыдущих 180 значений (30 дней).
- Первая свеча с процентилем ≥ 0,90 (толпа сильно в лонге) → **шорт**. Первая с процентилем ≤ 0,10 → **лонг**.
- Вход по открытию следующей 4h-свечи. Стоп 2×ATR14(4h), цель 2R, максимум 18 свечей (72 ч).
- Бумажные сделки считаются на свечах BingX так же, как в движке бэктеста.

Проверка `python3 -m live.test_crowd_bot` (на истории 2024–2026, BTC/ETH/SOL):
- сигналы бота совпадают со стратегией бэктеста **один в один** (282/303/342 сигнала, 0 расхождений);
- R сделок совпадает с движком до 5e-5.

Запуск на сервере (Binance отдаёт long/short ratio только не с американских IP):
```bash
python3 -m live.crowd_bot                 # один прогон
# cron: каждые 4 часа в :07
7 */4 * * * cd $HOME/research/trading && /usr/bin/python3 -m live.crowd_bot >> live/state/crowd_cron.log 2>&1
```
Переменные `.env`: `CROWD_RISK_PCT=0.25`, `PAPER_EQUITY=1000`, Telegram — общие с TSMOM. Сделки пишутся в `live/state/trades_crowd_paper.csv`.

Если бот стартовал на середине истории (первый запуск), он обрабатывает только последнюю закрытую свечу. Сигналы начнут появляться, когда наберётся история ratio: бот сам скачивает последние 30 дней.

# Логгеры (сбор истории, которой нет бесплатно)

| Логгер | Что пишет | Как запускать |
|---|---|---|
| `live/loggers/gex_logger.py` | GEX-уровни Deribit BTC/ETH (all/0DTE/1DTE, топ-40 страйков) и **IBIT** (CBOE, с задержкой 15 мин, страйки пересчитаны в цену BTC) → `state/gex/YYYY-MM.jsonl` | cron каждые 15 мин |
| `live/loggers/hl_whales_logger.py` | Позиции топ-100 кошельков Hyperliquid (on-chain, публично) + сводка по монетам: нетто лонг/шорт китов → `state/hl/` | cron каждые 15 мин (~45 с на прогон) |
| `live/loggers/liq_logger.py` | Ликвидации OKX (все), Bybit (все по списку монет), Binance (крупнейшая в секунду) → `state/liq/liq_YYYY-MM-DD.csv` | постоянный процесс (systemd) |

```bash
pip install websockets
crontab -e
*/15 * * * * cd $HOME/research/trading && /usr/bin/python3 -m live.loggers.gex_logger >> live/state/gex_cron.log 2>&1
3-59/15 * * * * cd $HOME/research/trading && /usr/bin/python3 -m live.loggers.hl_whales_logger >> live/state/hl_cron.log 2>&1
```
systemd для ликвидаций (`/etc/systemd/system/liq-logger.service`):
```
[Unit]
Description=liquidations logger
After=network-online.target
[Service]
WorkingDirectory=/root/research/trading
ExecStart=/usr/bin/python3 -m live.loggers.liq_logger
Restart=always
RestartSec=10
[Install]
WantedBy=multi-user.target
```
`systemctl daemon-reload && systemctl enable --now liq-logger`

Проверено 01.10.2026 из облака:
- GEX Deribit + IBIT работает. IBIT GEX $182M/1% против Deribit $218M/1% — сопоставимы, без IBIT видна только половина рынка.
- Hyperliquid: 100 кошельков за ~45 с. В топ-100 много маркет-мейкеров и vault-ов (нетто-шорт ETH −$807M, BTC −$590M), поэтому для «китов» адреса придётся фильтровать.
- OKX ликвидации пишутся.
- **Не проверено:** Bybit и Binance — блокируют US-IP, проверить на сервере. Для OKX `qty` в контрактах (USD не пересчитан). Условия использования CBOE delayed JSON — проверить.

Объём данных [оценка]:
- GEX — около 30 КБ на снимок, ~90 МБ/мес;
- Hyperliquid — ~1–2 МБ на прогон, ~5 ГБ/мес (уменьшить `HL_TOP_N` при нехватке места);
- ликвидации — десятки МБ в месяц.

Через 2–3 месяца проверяем на этой истории: GEX-уровни как поддержки и сопротивления, нетто-позиции китов как сигнал, каскады ликвидаций.

# options_expiry GEX logger — запуск по cron

Скрипт: `trading/strategies/options_expiry_gex_logger.py`. Он использует `trading/gex_levels.py` как библиотеку и не меняет его.

## Что пишет

Каждый запуск делает один снимок по BTC и ETH с публичного API Deribit (`public/get_book_summary_by_currency`, ключи не нужны).

1. `trading/data/ext/options_expiry/gex_log.parquet`. По одной строке на пару (валюта, режим), режимы `all`, `0dte`, `1dte`. Колонки:
   - `ts` — время снимка, UTC;
   - `currency`, `mode`, `spot`, `expiry` (для 0DTE/1DTE);
   - `n_options`, `oi_total`, `net_gex_usd_per_1pct`, `regime`;
   - уровни `zero_gamma`, `call_wall`, `put_wall`;
   - `top_strikes` (JSON).
2. `trading/data/ext/options_expiry/oi_snapshots/<CUR>/<YYYY-MM-DD>.parquet` — сырой OI и mark IV по каждому опциону: `ts, expiry, strike, cp, oi, mark_iv, spot`. Это главное. Бесплатной истории **OI по страйкам до экспирации** нет: Deribit отдаёт OI бесплатно только на момент поставки, а Tardis хранит 4 ГБ в день (см. `results/options_expiry.md`). Архив из этих снимков позволит через 3–6 месяцев честно проверить уровни GEX, max pain и пиннинг на данных, которые были известны **до** экспирации.

Объём [оценка]: ~1 400 инструментов × 24 снимка × 2 валюты ≈ 70 тыс. строк в день, около 1–2 МБ parquet в день. Одновременные запуски защищены lock-файлом `.gex_logger.lock`. Запись атомарная: сначала tmp-файл, потом rename.

## Установка на сервере (Hetzner VPS)

```bash
cd /opt/research            # путь к клону репозитория — подставьте свой
python3 -m pip install --user pandas pyarrow
python3 trading/strategies/options_expiry_gex_logger.py          # пробный запуск
python3 trading/strategies/options_expiry_gex_logger.py --show 6 # последние строки
```

Запись для cron (`crontab -e`), раз в час на 5-й минуте:

```cron
5 * * * * cd /opt/research/trading && /usr/bin/python3 strategies/options_expiry_gex_logger.py >> data/ext/options_expiry/gex_logger.log 2>&1
```

Дополнительно можно снимать за 5 минут до расчёта: в 07:55 UTC OI истекающих 0DTE-опционов ещё открыт.

```cron
55 7 * * * cd /opt/research/trading && /usr/bin/python3 strategies/options_expiry_gex_logger.py >> data/ext/options_expiry/gex_logger.log 2>&1
```

Проверить, что cron на сервере работает в UTC: `date -u` и `timedatectl`. Если сервер живёт в другой зоне, в crontab нужно указать `CRON_TZ=UTC`.

## Флаги
- `--currencies BTC ETH` — список валют;
- `--no-raw` — не писать сырой OI (писать только уровни);
- `--show N` — показать последние N строк лога.

## Оговорки
- GEX — это модель, а не факт. Классическая конвенция «дилеры long calls / short puts» нигде не проверена (проверить). Позиции дилеров Deribit не публикует.
- API Deribit из РФ/РБ и некоторых облаков может быть недоступен; из этого облака он работал 30.09.2026. Если сервер в Hetzner (DE/FI), доступ проверить отдельно.
- Сетевая ошибка по одной валюте не останавливает запись по другой. Код выхода 1 — только если не записалось ничего.

# bt — движок бэктестов

- `bt/data.py` — кэш истории Binance USD-M (5m свечи с taker buy volume, OI и long/short ratio с 2024-01, funding) и Deribit DVOL. `python3 -m bt.data download`.
- `bt/engine.py` — симулятор: контракт стратегии, консервативное исполнение, комиссии, `check_lookahead()`.
- `bt/features.py` — причинные индикаторы (значение в строке t зависит только от строк ≤ t).
- `bt/runner.py` — перебор параметров, выбор **только** на in-sample (< 2025-01-01), отчёт на out-of-sample (2025-01…2026-08) при базовых и жёстких издержках.
- `python3 -m bt.test_engine` — тесты движка.

Издержки: base = taker 0,05% / maker 0,02% / проскальзывание 0,02%; harsh = 0,06% / 0,04% / 0,05% [оценка — сверить с тарифами BingX/Bitunix].

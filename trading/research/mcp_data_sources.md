# MCP-серверы и источники данных для торгового бота

Дата: 27.09.2026. Личный трейдинг владельца, не бизнес-направление проекта (ТЗ — `notes/trading-bot/spec.md`, код — `trading/`). Это исследование, а не финансовая консультация. Аккаунты не создавались, подписки не оформлялись, формы не отправлялись.

Широкая таблица продублирована в CSV: `trading/research/mcp_data_sources.csv` (связь по ID).

**Метки источников.**
- [офиц.] — госорган (CFTC).
- [provider docs] — документация или справка самого провайдера.
- [вендор] — ценовая или маркетинговая страница провайдера.
- [пресса].
- [агрегатор] — сторонние обзоры и каталоги. Доступность сервиса они не доказывают.
- [комьюнити] — сторонний код на GitHub или npm.
- [каталог claude.ai] — поиск SearchMcpRegistry 27.09.2026.
- [тест 27.09] — наш curl-запрос 27.09.2026 из Google Cloud (Айова, США, IP 34.172.54.233). **Это не Hetzner.**
- [оценка] — расчёт или суждение, формула приведена.

Все страницы открыты 27.09.2026, если не указано иное. «Проверить» — не подтверждено первоисточником.

---

## 0. Допущения по умолчанию

Вопросы пользователю не задавались: задача пришла из скрипта. Поэтому работаю по допущениям ниже.

1. Сервер Hetzner стоит в ЕС (Германия или Финляндия), точный дата-центр неизвестен. Как это проверить — шаг 0 в разделе 6.
2. Агенты флота запускают Claude Code в терминале под аккаунтом claude.ai. В таком режиме коннекторы из каталога claude.ai подтягиваются в Claude Code автоматически ([provider docs](https://code.claude.com/docs/en/mcp), раздел «How connectors reach Claude Code»). Если агенты работают по API-ключу, коннекторов не будет — только `claude mcp add`. **Проверить**, как авторизован флот.
3. Бюджет на данные:
   - сейчас — $0;
   - ≤ $50/мес — только после того, как бэктест покажет пользу источника;
   - премиум — только под доказанное преимущество.
4. Таймфрейм бота — 1–15m (стратегии A–D из ТЗ). Золото, серебро и FX — следующий этап, здесь только отмечены источники под них.

---

## 1. Коротко

1. **MCP нужен агентам, а не боту.** Через MCP агенты исследуют, разбирают рынок, пишут код и отвечают на разовые вопросы. Сам бот должен читать WebSocket и REST напрямую, своим кодом. Так результат детерминирован, воспроизводится в бэктесте и не ждёт ответа LLM. Все «боевые» данные ниже подключаются кодом, MCP — дополнительный слой для агентов.
2. **Почти всё про «китов» и деривативы бесплатно доступно у первоисточников**:
   - Hyperliquid: адреса и позиции любых кошельков публичны;
   - Deribit и OKX: опционные цепочки с греками, из них считается GEX;
   - Bybit: поток **всех** ликвидаций;
   - биржи и Coinalyze: OI и funding;
   - CFTC: отчёты COT;
   - экономический календарь.
3. **Главная дыра текущего GEX — IBIT.** По прессе, опционы IBIT составляют около половины открытого интереса по BTC-опционам: 52% в январе 2026 ([пресса, CoinDesk 13.01.2026](https://www.coindesk.com/markets/2026/01/13/bitcoin-options-open-interest-extends-dominance-over-futures-damping-btc-volatility), цифра из выдержки — проверить). Значит, `gex_levels.py`, который считает только по Deribit, видит часть рынка.
   - У IBIT экспирации в понедельник, среду и пятницу: 28.09, 30.09, 02.10 [тест 27.09], то есть 0DTE/1DTE есть и там.
   - Бесплатный источник цепочки — CBOE delayed JSON (условия использования проверить).
   - Платный — Massive Options Starter за $29/мес.
4. **Платные агрегаторы нужны прежде всего для истории (бэктестов), а не для live-данных.**
   - CoinGlass Hobbyist ($29): интервал ≥ 4h, для 5m бесполезен. Карта ликвидаций (heatmap) есть только в Professional за $699 ([provider docs](https://docs.coinglass.com/reference/liquidation-heatmap)).
   - Tardis.dev — лучший источник тиковой истории опционных цепочек, но стоит от $350 до $700+ в месяц. Бесплатно — только 1-е число каждого месяца.
5. **TradingView — только для глаз.** Условия TradingView прямо запрещают использовать алерты и вебхуки для автоматической торговли ([provider docs](https://www.tradingview.com/policies/)).
6. **Гео.** Из облака в США [тест 27.09]:
   - Binance отвечает 451 («restricted location»), Bybit — 403 (CloudFront);
   - OKX, BingX, Bitunix, Deribit и Hyperliquid — 200.

   С Hetzner нужно проверить (шаг 0). Bybit global с 01.07.2026 не обслуживает резидентов ЕЭЗ ([пресса](https://crypto.news/bybit-limits-eea-access-as-mica-deadline-closes-in/)). Пользователь резидент Молдовы, но IP сервера — немецкий или финский. Спросить поддержку биржи; местоположение не маскировать.
7. **Bitunix нет в CCXT** (`ts/src/bitunix.ts` → 404 [тест 27.09]). Для Bitunix нужен свой клиент поверх официального REST/WS. BingX есть в CCXT со статусом «Certified», а у самого BingX есть официальный набор AI-skills для Claude Code.

### Про «предугадывать будущее»

Больше факторов — не значит больше точности. Рынок — это соревнование, и каждый новый источник данных — новая гипотеза. Чем больше вариантов перебираем, тем больше ложных «открытий» на истории. Наши собственные цифры (`trading/README.md`):
- SMC-схема дала ≈ +0,12R на сделку при стандартной ошибке ≈ 0,15R;
- объёмные сигналы не перекрывают комиссию.

Правило для этого стека [оценка]: источник остаётся, только если на out-of-sample и после издержек он улучшает результат с поправкой на число испробованных вариантов. Сначала бесплатные данные и собственная история, платить — за то, что прошло этот фильтр.

---

## 2. Что есть в каталоге коннекторов claude.ai (27.09.2026)

Поиск SearchMcpRegistry по словам crypto, trading, market data, exchange, blockchain, on-chain, news, finance, options, coingecko, polygon, alpha vantage, dune, arkham, nansen, tradingview, glassnode, deribit, hyperliquid, macro, calendar. Ни один коннектор у пользователя не подключён: в организации есть только незавершённый Google Drive.

| Коннектор | Что даёт | Авторизация | Польза для бота [оценка] |
|---|---|---|---|
| **Coinversa Pulse** | Hyperliquid: трейдеры, когорты, позиции, карта ликвидаций, стакан L4 | OAuth + ключ Coinversa; бесплатный ключ открывает только публичные маршруты ([README](https://github.com/Coinversaa/mcp-server)) | Высокая: «киты» Hyperliquid для агентов |
| **Alpha Vantage** | Акции, FX, сырьё (золото, серебро), макроиндикаторы, NEWS_SENTIMENT | OAuth, бесплатный ключ: 25 запросов в день ([вендор](https://www.alphavantage.co/premium/)) | Средняя: макро и новости, этап «металлы» |
| **Tavily** | Веб-поиск и извлечение текста | Ключ: 1 000 кредитов в месяц бесплатно ([вендор](https://www.tavily.com/pricing)) | Средняя: новости для фильтра режима |
| **Exa** | Веб-поиск | Ключ: $10 в месяц бесплатно, около 1 400 поисков ([provider docs](https://exa.ai/docs/admin/pricing)) | Средняя |
| **Parallel Search** | Веб-поиск и загрузка страниц | Без авторизации, «free» по описанию в каталоге | Средняя: бесплатный поиск новостей |
| **LunarCrush** | Соцсети: крипта и акции | Платно: Individual $90/мес ([вендор](https://lunarcrush.com/pricing), по заголовку страницы) | Низкая для 5m |
| **FMP** | Экономический календарь, COT, сырьё, FX | Ключ, цены — проверить | Средняя: календарь и COT |
| **Twelve Data** | Цены акций, FX, крипты; индикаторы | Ключ | Низкая |
| **CoinDesk** | Спот, индексы, OHLCV, стаканы | Бесплатный уровень закрыт 21.05.2026 ([вендор](https://data.coindesk.com/blogs/changes-to-coindesk-data-indices-api-free-tier-access)) | Низкая |
| **Crypto.com** | Цены и сделки биржи Crypto.com | Без авторизации | Низкая: не наша биржа |
| **Blockscout** | Адреса, транзакции, токены EVM-сетей | Без авторизации | Низкая–средняя: разбор кошельков агентами |
| **Gemini** | Рынки Gemini, prediction markets, счёт | OAuth (read-only) | Низкая |
| MT Newswires, Bigdata.com, LSEG, FactSet, Oxford Economics, Meltwater | Институциональные новости и данные | Enterprise-контракты | Не для этого бюджета |

**В каталоге не найдены:** CoinGecko, CoinMarketCap, CoinGlass, Glassnode, CryptoQuant, Nansen, Arkham, Dune, Santiment, Deribit, Laevitas, Massive (Polygon), Whale Alert, официальный Hyperliquid, Binance, Bybit, OKX, BingX, Bitunix. У многих из них есть свой официальный MCP (раздел 3). Подключаются они как пользовательский коннектор по URL в claude.ai или командой `claude mcp add`.

---

## 3. Источники: таблица

### 3A. Что даёт и сколько стоит

| ID | Источник | Данные (real-time?) | MCP | Цена 2026 | Бесплатно | Метка |
|---|---|---|---|---|---|---|
| E1 | **BingX API** | OI, funding, стакан, сделки; WS — да | Официальные AI-skills ([GitHub BingX-API](https://github.com/BingX-API/api-ai-skills)); MCP только от комьюнити | $0 | Публичные данные без ключа | [provider docs] |
| E2 | **Bitunix API** | Тикеры, стакан, funding; WS — да. REST 10 запросов/с на IP, WS 5 сообщений/с ([docs](https://openapidoc.bitunix.com/doc/market/get_kline.html), по выдержке) | Только комьюнити (LobeHub) | $0 | Публичные данные | [provider docs] — проверить |
| E3 | **CCXT MCP** (`ccxt-mcp` 0.1.3, 25.08.2026) | Биржи из CCXT: тикеры, стакан, OHLCV, сделки, WS-подписки | **Официальный**, stdio; торговля выключена по умолчанию ([docs](https://docs.ccxt.com/docs/mcp)) | $0 | Да | [provider docs] |
| E4 | **Binance** публичный API + data.binance.vision | Сделки, aggTrades, OI, L/S, funding, ликвидации (1 в секунду); история — годы | Официальный Binance MCP (Agent OS, 20.08.2026) — нужен аккаунт Binance и «Agentic sub-account» ([объявление](https://www.binance.com/en/support/announcement/detail/07d45cdd3831498f8a4ff339031a8480)) | $0 | Да | [provider docs] |
| E5 | **Bybit** публичный API | Все ликвидации (500 мс), OI, funding, опционы | **Официальный** `bybit-official-trading-server` 2.1.22: 384 инструмента, 23 рыночных работают без ключа ([GitHub](https://github.com/bybit-exchange/trading-mcp)) | $0 | Да | [provider docs] |
| E6 | **OKX** публичный API | OI, funding, опционы с греками, ликвидации (не все) | **Официальный** Agent Trade Kit, `okx-trade-mcp` 1.2.8 ([docs](https://www.okx.com/docs-v5/agent_en/)) | $0 | Да | [provider docs] |
| E7 | **Hyperliquid** info API + WS | Позиции **любого адреса** (`clearinghouseState`), сделки с адресами покупателя и продавца, OI, funding — real-time | Официального нет. В каталоге — Coinversa Pulse, есть и комьюнити-серверы | $0 | Да: 1 200 единиц веса в минуту на IP ([docs](https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/rate-limits-and-user-limits)) | [provider docs] |
| E8 | **Deribit** публичный API | Опционы: OI по страйкам, греки, DVOL; история сделок (history.deribit.com) | Только комьюнити (например, freeeverett/deribit-mcp) | $0 | Лимит на IP ([docs](https://docs.deribit.com/articles/rate-limits)) | [provider docs] |
| D1 | **Coinalyze API** | OI, funding, прогноз funding, ликвидации, L/S, OHLCV по многим биржам | Нет | $0 | 40 вызовов в минуту на ключ. Внутридневная история — 1 500–2 000 точек, дневная хранится полностью ([docs](https://api.coinalyze.net/v1/doc/)) | [provider docs] |
| D2 | **CoinGlass API** | Агрегированные OI, funding, ликвидации, ETF, max pain, стаканы, heatmap | **Официальный**, remote, beta: `api-mcp.coinglass.com/mcp` ([docs](https://docs.coinglass.com/reference/mcp-service)) | Hobbyist $29 (30 в минуту), Startup $79, Standard $299 (коммерческое использование), Professional $699 ([вендор](https://www.coinglass.com/pricing)) | Нет | [provider docs] |
| D3 | **Laevitas** | Деривативы 15+ бирж, GEX, поверхности волатильности, Hyperliquid | **Официальный**: `apiv2.laevitas.ch/api/v1/mcp`, 80+ инструментов, «Requires an Enterprise API key» ([docs](https://apiv2.laevitas.ch/mcp/)) | Premium $50/мес (UI, CSV, 1 год истории), Enterprise $500/мес (API с историей) ([вендор](https://www.laevitas.ch/)). x402: $0.001 за запрос, пакет из 100 запросов ([docs](https://apiv2.laevitas.ch/x402/)) | Free: 1 неделя истории в UI | [provider docs] |
| D4 | **Amberdata** | GEX с анализом агрессора сделок, деривативы | Не найден | Цена по запросу ([вендор](https://www.amberdata.io/pricing)) | Нет | [вендор] |
| D5 | **Greeks.live** | Блоки, поток опционов | Не найден | Публичного API не нашли | — | нет данных |
| D6 | **Velo** | Фьючерсы, опционы, спот 5 бирж | Нет | Premium API $199/мес (по выдержке поиска) — проверить | Триал по email | [агрегатор] |
| D7 | **Tardis.dev** | Тиковая история: стаканы, сделки, `options_chain`, ликвидации. Deribit — с 30.03.2019 ([docs](https://docs.tardis.dev/historical-data-details/deribit)) | Нет | Опционы и перпетуалы: Academic $350 (оплата за квартал или год), Solo $700, Pro $1 000, Business $3 000 в месяц; все биржи — от $650 ([вендор](https://tardis.dev/)) | CSV за **1-е число каждого месяца** без ключа ([docs](https://docs.tardis.dev/downloadable-csv-files)) | [provider docs] |
| D8 | **CBOE delayed quotes** (IBIT) | Цепочка IBIT: OI, IV, греки; задержка 15 минут | Нет | $0 | JSON без ключа [тест 27.09: 2 582 контракта] | [тест], условия — проверить |
| D9 | **Massive** (бывший Polygon.io) | Опционы США (OPRA), CME-фьючерсы, FX | **Официальный** `mcp_massive`, stdio ([GitHub](https://github.com/massive-com/mcp_massive)) | Options Starter $29 (задержка 15 минут, греки, 2 года истории). Futures Starter $29 (CME, COMEX; задержка 10 минут). Currencies Starter $49 (real-time) ([вендор](https://massive.com/pricing)) | Basic: конец дня, 5 вызовов в минуту | [вендор] |
| D10 | **Databento** | CME (включая опционы на золото), OPRA | Нет | CME Standard $199, OPRA Standard $199; $125 бесплатных кредитов (по выдержкам [блога](https://databento.com/blog/updates-to-subscription-pricing)) | $125 кредитов | [provider docs] — проверить |
| O1 | **Whale Alert** | Крупные переводы 14 сетей, биржевая атрибуция, эмиссия и сжигание стейблкоинов | Нет | Alerts API $29.95/мес (WS, «personal use only»). Enterprise $699/мес: 90 дней истории, 500 вызовов в минуту ([docs](https://developer.whale-alert.io/api-account/documentation)) | Триал 7 дней | [provider docs] |
| O2 | **Arkham** | Атрибуция кошельков, потоки сущностей | Инструкция MCP для Claude от 27.04.2026 | API — «by application» ([вендор](https://info.arkm.com/announcements/how-to-use-the-arkham-api-with-ai-agents)) | Веб-интерфейс | [provider docs] |
| O3 | **Nansen** | Smart money, перпы Hyperliquid, профили кошельков | **Официальный**: `mcp.nansen.ai/ra/mcp` ([docs](https://docs.nansen.ai/mcp/connecting)) | Pro $49/мес (при оплате за год) или $69 (помесячно), 2 000 кредитов ([docs](https://docs.nansen.ai/getting-started/credits)) | 100 кредитов + пополнение до 10 в день | [provider docs] |
| O4 | **Glassnode** | Ончейн, ETF, фьючерсы, опционы | **Официальный**, beta; без ключа — только последние 30 дней ([docs](https://docs.glassnode.com/integrations-and-tools/glassnode-mcp-server)) | Advanced $49/мес (при оплате за год): «API Light» — 14 дней истории, дневное разрешение, 50 вызовов в день. Professional — API до 10 минут, цена по конфигурации ([вендор](https://studio.glassnode.com/pricing)) | MCP без ключа (30 дней) | [provider docs] |
| O5 | **CryptoQuant** | Биржевые потоки, майнеры, деривативы | **Официальный**, beta; «Research and QuickTakes… free in beta» ([docs](https://userguide.cryptoquant.com/api/mcp-server-beta)) | Advanced $29, Professional $99, Premium $799 в месяц при оплате за год — только из поиска, страница цен не отрисовалась. Проверить | Частично | [агрегатор] |
| O6 | **Dune** | SQL по 100+ сетям | **Официальный**: `api.dune.com/mcp/v1` ([docs](https://docs.dune.com/api-reference/agents/mcp)) | Analyst ≈ $65–75, Plus ≈ $349 в месяц ([агрегатор](https://comparedge.com/tools/dune-analytics/pricing)) — проверить | **API на бесплатном плане нет** («view-only», [docs](https://docs.dune.com/api-reference/overview/rate-limits)) | [provider docs] |
| O7 | **Santiment** | Соц- и ончейн-метрики, тренды | **Официальный**: `api.santiment.net/mcp`, OAuth ([docs](https://academy.santiment.net/mcp-connector/)) | Цены планов — на [app.santiment.net/pricing](https://app.santiment.net/pricing), не извлечены | Free: 1 000 вызовов в месяц, 1 год истории, **задержка 30 дней** ([docs](https://academy.santiment.net/products-and-plans/sanapi-plans/)) | [provider docs] |
| O8 | **mempool.space, Blockscout, DefiLlama** | BTC-мемпул и блоки; EVM-адреса; предложение стейблкоинов | Blockscout — в каталоге | $0 | Да [тест 27.09: 200] | [тест] |
| M1 | **CoinGecko** | Цены, биржи, ончейн (GeckoTerminal) | **Официальный**, remote, **без ключа**: `mcp.api.coingecko.com/mcp` ([docs](https://docs.coingecko.com/ai-integration/mcp-server)) | Basic $35 ($29 при оплате за год), Analyst $129 ([вендор](https://www.coingecko.com/en/api/pricing)) | Demo: 10 000 кредитов в месяц | [provider docs] |
| M2 | **CoinMarketCap** | Цены, листинги | **Официальный**: `mcp.coinmarketcap.com/mcp`, 12 инструментов ([вендор](https://coinmarketcap.com/api/mcp/)) | Builder $29/мес при оплате за год, Startup $79 (с WS) ([вендор](https://coinmarketcap.com/api/pricing/)) | Basic free; 10 000 кредитов по [академии CMC](https://coinmarketcap.com/academy/article/best-free-crypto-api-in-2026-free-tier-comparison), в другом источнике 15 000 — проверить | [вендор] |
| N1 | **CryptoPanic** | Лента крипто-новостей | Нет | Бесплатный Developer API закрыт 01.04.2026; Growth $199/мес — по выдержке поиска, страница не отрисовалась ([вендор](https://cryptopanic.com/developers/api/plans)). Проверить | Нет | [агрегатор] |
| N2 | **LunarCrush** | Соцметрики | Официальный, в каталоге | Individual $90, Builder $300 в месяц | Discover (UI) | [вендор] |
| N3 | **Tavily / Exa / Parallel Search** | Веб-поиск новостей | Все три в каталоге claude.ai | Tavily PAYG $0.008 за кредит; Exa $7 за 1 000 поисков | Tavily — 1 000 кредитов в месяц; Exa — $10 в месяц; Parallel — без ключа | [вендор] / [каталог claude.ai] |
| K1 | **CFTC COT** (Socrata) | Позиции по категориям: CME Bitcoin (TFF `gpe5-46if`), золото COMEX (Disaggregated `72hh-3qpy`); раз в неделю | Нет | $0 | Да [тест 27.09: отчёт за 22.09.2026] | [офиц.] |
| K2 | **FRED** | Макроряды США | Только комьюнити | $0, бесплатный ключ ([docs](https://fred.stlouisfed.org/docs/api/api_key.html)); 120 запросов в минуту — по выдержке, проверить | Да | [provider docs] |
| K3 | **ForexFactory JSON** (`nfs.faireconomy.media`) | Календарь недели: важность, прогноз, предыдущее значение | Нет | $0 | Да [тест 27.09: 141 событие]; **неофициальный** фид, условия — проверить | [тест] |
| K4 | **Trading Economics** | Календарь, консенсус, 196 стран | Нет | Standard ≈ $149, Professional ≈ $299 в месяц при оплате за год ([агрегатор](https://apis.io/plans/tradingeconomics/tradingeconomics-plans-pricing/)) — проверить | Триал; guest:guest закрыт в 2026 | [агрегатор] |
| K5 | **Alpha Vantage** | Акции, FX, сырьё, макро, NEWS_SENTIMENT | **Официальный**, remote `mcp.alphavantage.co/mcp` (OAuth), в каталоге ([README](https://github.com/alphavantage/alpha_vantage_mcp)) | $49.99/мес — 75 запросов в минуту ([вендор](https://www.alphavantage.co/premium/)) | 25 запросов в день | [provider docs] |
| K6 | **FMP** | Экономический календарь ([docs](https://site.financialmodelingprep.com/developer/docs/stable/economics-calendar)), COT, сырьё, FX | В каталоге | Страница цен отдала 403; Ultimate ≈ $149/мес при оплате за год, лимиты 300/750/3 000 в минуту — по выдержкам поиска. Проверить | Есть (проверить) | [агрегатор] |
| V1 | **TradingView** | Графики, Pine, алерты | Комьюнити-MCP через скрейпинг или десктоп — **нарушают условия** | — | — | [provider docs] |

### 3B. Доступ, подключение, польза

Польза: 5 — ядро, 1 — не нужен [оценка по стратегиям A–D из ТЗ]. Здесь только ключевые строки; полная версия со всеми ID — в CSV.

| ID | Из облака США [тест 27.09] | Молдова, ЕС, Hetzner | Подключение | Роль | Польза | Оговорки |
|---|---|---|---|---|---|---|
| E1 | 200 | Аккаунт уже верифицирован (MD). CFD BingX недоступен в Германии и ещё ряде стран, Молдова в списке не названа ([BingX, 04.08.2026](https://bingx.com/en/support/articles/17088995856271)) — важно для этапа «металлы» | Код через CCXT; агентам — CCXT MCP и skills | Исполнение, live-данные | 5 | Разрешён ли API-доступ с IP в DE/FI для аккаунта резидента MD — спросить поддержку |
| E2 | 200 | MD и DE нет в списке ограничений, Франция есть ([Bitunix](https://www.bitunix.com/hub/helpcenter/article/bitunix-restricted-regions-and-user-eligibility-notice?id=146)). Лицензии CASP (MiCA) нет — «серая зона ЕС» ([агрегатор](https://www.datawallet.com/crypto/bitunix-restricted-countries)) | Свой клиент REST/WS; **в CCXT нет** | Исполнение | 5 | Надёжность биржи — см. ТЗ, «Проверить» |
| E3 | Зависит от биржи | — | `claude mcp add ccxt -- npx -y ccxt-mcp` (stdio) | Агенты: чтение | 4 | Торговлю через MCP не включать |
| E4 | **451** (fapi, eapi); data.binance.vision — 200 | Ограничены США, Малайзия, Онтарио ([условия](https://www.binance.com/en/terms), по выдержке — проверить). С Hetzner — шаг 0 | Код (WS/REST); история — vision | Live-данные, история | 5 | Поток ликвидаций отдаёт **1 ликвидацию в секунду** на символ ([docs](https://developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams/All-Market-Liquidation-Order-Streams)) |
| E5 | **403**; public.bybit.com — 200 | Global с 01.07.2026 не обслуживает резидентов ЕЭЗ ([пресса](https://crypto.news/bybit-limits-eea-access-as-mica-deadline-closes-in/)). Публичные данные с IP ЕС — шаг 0 | Код (WS `allLiquidation`); агентам — `npx -y bybit-official-trading-server@latest` | Ликвидации, OI | 5 | — |
| E6 | 200 | — | Код; агентам — `okx-trade-mcp` | Опционы для GEX, OI | 4 | Поток ликвидаций «doesn't represent the total number» ([docs](https://www.okx.com/docs-v5/en/)) |
| E7 | 200 | Публичные данные ключа не требуют | Код (POST `/info`, WS); агентам — Coinversa (каталог) | **Киты** | 5 | Лидерборд — неофициальный эндпоинт. В топе по капиталу — служебные адреса и хранилища (vaults) |
| E8 | 200 | — | Код (уже есть `gex_levels.py`) | GEX | 5 | Это только часть рынка BTC-опционов (IBIT, CME) |
| D1 | 401 без ключа (сервер жив) | — | Код, заголовок `api_key` | OI, ликвидации по биржам | 4 | Внутридневную историю собирать самим каждый день |
| D2 | 200 | — | `claude mcp add --transport http coinglass https://api-mcp.coinglass.com/mcp --header "CG-API-KEY: …"` | Агенты, история | 2 на Hobbyist, 4 на Standard и выше | Интервал истории: Hobbyist ≥ 4h, Startup ≥ 30m (по таблице на [странице эндпоинта](https://docs.coinglass.com/reference/aggregated-liquidation-history) — трактовку проверить). Ордера ликвидаций — со Standard |
| D3 | 200 | Оплата x402 в USDC на Base или Solana | `claude mcp add laevitas-derivatives --transport http https://apiv2.laevitas.ch/api/v1/mcp --header "apikey: …"` | История GEX и деривативов | 3–4 | Расхождение: страница MCP требует Enterprise-ключ, страница x402 пишет, что x402 работает «with REST endpoints and MCP tool calls alike». Проверить на малой сумме |
| D7 | 200; не 1-е число — 401 | Оплата картой, инвойс — от $6 000 | Код (`pip install tardis-dev`, CSV) | Бэктест GEX и ликвидаций | 5 для бэктестов | Месячная подписка даёт доступ только к **4 месяцам** истории, квартальная или годовая — к 4 годам (по выдержке [FAQ](https://docs.tardis.dev/faq/billing-and-subscriptions) — проверить) |
| D8 | 200 (редирект на cdn-api.cboe.com) | — | Код | GEX по IBIT | 4 | Условия CBOE для задержанных данных — проверить до использования в боте |
| D9 | — | Лицензия «Individual use only» — нам подходит | `claude mcp add massive -e MASSIVE_API_KEY=… -- mcp_massive` | GEX по IBIT, история, позже металлы и FX | 4 | Задержка 15 минут; OI опционов всё равно обновляется раз в день |
| D10 | — | — | Код | Металлы: опционы CME | 2 сейчас, 4 на этапе «металлы» | Цены по выдержкам |
| O1 | — | — | Код (WS) | Алерты о переводах | 2 | Для 5m — слабый сигнал [оценка]: перевод не равен сделке |
| O3 | — | Оплата x402 или картой | `claude mcp add --transport http nansen https://mcp.nansen.ai/ra/mcp --header "NANSEN-API-KEY: …"` | Агенты: smart money, Hyperliquid | 3 | Кредиты расходуются быстро |
| O4 | — | — | `claude mcp add --transport http glassnode https://mcp.glassnode.com` (URL из `npx add-mcp` в docs — проверить путь) | Агенты: ончейн-контекст | 2 | Без ключа — 30 дней, дневное разрешение |
| O6 | — | — | `claude mcp add --scope user --transport http dune https://api.dune.com/mcp/v1` | Агенты | 1–2 | Бесплатно API нет |
| O7 | — | — | `claude mcp add santiment --transport http https://api.santiment.net/mcp` (OAuth) | Агенты: соцметрики | 2 | Задержка 30 дней на бесплатном плане |
| M1 | 200 | — | `claude mcp add --transport http coingecko https://mcp.api.coingecko.com/mcp` | Агенты: справка по рынку | 2 | — |
| K1 | 200 | — | Код (Socrata JSON) | Режим недели: фонды на CME, золото | 3 | Раз в неделю, данные по вторник — только фильтр |
| K3 | 200 | — | Код | Фильтр «не входить вокруг новостей» | 4 | Неофициальный; только текущая неделя — сохранять самим |
| V1 | — | — | Pine — только визуально | Глаза владельца | 1 для бота | Условия: «any form of automated trading… algorithmic decision-making» запрещены, вебхуки прямо названы |

---

## 4. Рекомендуемый стек: три уровня

### Уровень 0 — бесплатно, сейчас ($0)

| Задача | Источник | Как подключить |
|---|---|---|
| Киты: позиции | Hyperliquid: лидерборд → топ-N адресов → `clearinghouseState`; WS `trades` с адресами | Код (раздел 6, п. 1) |
| Киты: крупные сделки на CEX | WS сделок Bybit, OKX, BingX; история — aggTrades из data.binance.vision | Код |
| GEX | Deribit + OKX (+ Bybit и Binance, если доступны с Hetzner) + IBIT через CBOE delayed | Расширить `gex_levels.py` (п. 2) |
| Ликвидации | Bybit `allLiquidation` (все); OKX (часть); Binance (1 в секунду) | WS-сборщик (п. 3) |
| OI и funding | REST бирж + Coinalyze (бесплатный ключ) | Код (п. 3) |
| Макро и календарь | CFTC COT, FRED, ForexFactory JSON | Код (п. 5) |
| Новости для агентов | Parallel Search (каталог, без ключа), Tavily free, Exa free | Коннекторы claude.ai (п. 5) |
| Биржи для агентов | CCXT MCP (только чтение), BingX AI-skills, CoinGecko без ключа | `claude mcp add` (п. 4) |
| Ончейн для агентов | Glassnode без ключа (30 дней), Santiment free, Nansen free, Blockscout | По желанию, по одному |
| История для бэктестов | data.binance.vision, public.bybit.com, history.deribit.com, Tardis за 1-е число месяца, **собственный сборщик с сегодняшнего дня** | Раздел 5 |

### Уровень 1 — дёшево (до $50 в месяц в сумме)

Рекомендация: **Massive Options Starter за $29 + Laevitas x402 примерно на $10 ≈ $39 в месяц** [оценка: 10 000 запросов × $0.001 = $10]. Подключать по одному и только после того, как бесплатный вариант покажет пользу в бэктесте.

| Источник | Цена | Зачем | Когда брать |
|---|---|---|---|
| Massive Options Starter | $29/мес | Цепочки IBIT с греками и **2 года истории** → бэктест GEX по IBIT без самостоятельного сбора | Если GEX по Deribit и OKX хоть как-то работает как фильтр |
| Laevitas x402 | $0.001 за запрос | История деривативов и GEX от агрегатора без подписки | Для сверки своего GEX и исторических OI и funding |
| Nansen Pro | $49/мес (при оплате за год) | Smart money и перпы Hyperliquid с атрибуцией | Если своего сбора Hyperliquid окажется мало |
| Whale Alert Alerts API | $29.95/мес | WS-алерты крупных переводов | Низкий приоритет |
| Massive Futures Starter / Currencies Starter | $29 / $49 в месяц | COMEX (золото, серебро) с задержкой 10 минут / FX в реальном времени | Этап «металлы и FX» |

Не брать: CoinGlass Hobbyist ($29, история ≥ 4h), CoinGecko Basic и CMC Builder (цены и так бесплатны у бирж), LunarCrush Individual ($90).

### Уровень 2 — премиум (только под доказанное преимущество)

| Источник | Цена | Что даёт сверх бесплатного |
|---|---|---|
| Tardis.dev Solo (опционы или перпетуалы) | $700/мес; 4 года истории — только при оплате за квартал или год | Тиковая история опционных цепочек Deribit с 2019, ликвидации, стаканы → честный бэктест GEX и каскадов |
| CoinGlass Standard / Professional | $299 / $699 в месяц | Ордера ликвидаций, крупные лимитные заявки / heatmap, коммерческая лицензия |
| Laevitas Enterprise | $500/мес | Полный MCP и API с историей |
| Databento CME / OPRA Standard | $199/мес каждый | Опционы CME на золото и серебро (GEX металлов), OPRA в реальном времени |
| Glassnode Professional + API, CryptoQuant Professional | Цена по конфигурации / ≈ $99 при оплате за год (проверить) | Ончейн-потоки с разрешением 10 минут — 1 час |
| Amberdata, Velo | По запросу / $199 (проверить) | GEX с учётом агрессора сделок; сводные деривативы |

---

## 5. Данные для бэктестов: что даёт историю

| Данные | Источник | Глубина | Цена | Метка |
|---|---|---|---|---|
| 5m-свечи с taker buy, OI и L/S (5m), funding | data.binance.vision — уже в `trading/data`, метрики с 2024-01 | Годы | $0 | [тест 27.09] |
| aggTrades (крупные сделки), bookDepth, bookTicker | data.binance.vision, `futures/um/daily/*` | Годы | $0 | [тест 27.09] |
| Сделки Bybit | public.bybit.com/trading | Годы | $0 | [тест 27.09] |
| Сделки опционов Deribit с IV | history.deribit.com | Годы (минимум с 2025-01, проверено запросом) | $0 | [тест 27.09] |
| Снимки опционных цепочек → **история GEX** | Tardis `options_chain` | Deribit с 2019; бесплатно только 1-е число месяца (12 дней в году) | $0 / $350–700+ в месяц | [provider docs] |
| Цепочки IBIT с греками | Massive Options Starter | 2 года | $29/мес | [вендор] |
| Агрегированные ликвидации, OI, funding | Coinalyze: дневные — полностью, внутридневные — ≈ 5 дней при 5m [оценка: 1 500 × 5 мин ≈ 125 ч]. CoinGlass Hobbyist — ≥ 4h | Коротко | $0 / $29 | [provider docs] |
| Позиции китов Hyperliquid | Бесплатной готовой истории нет → **собирать с сегодняшнего дня**. Исторические инструменты Coinversa — с платного тарифа; S3-архив Hyperliquid — проверить | С даты запуска сборщика | $0 | [provider docs] |
| COT | CFTC | Годы | $0 | [офиц.] |
| Календарь | ForexFactory JSON — только текущая неделя, архивировать каждую неделю. TE и FMP — платно | С даты запуска | $0 | [тест 27.09] |

Как не обмануть себя большим числом бэктестов [оценка, дополняет `trading/bt/README.md`]:
1. Каждая новая фича — отдельная гипотеза. Вести журнал проверенных вариантов, их число поправляет порог значимости.
2. Параметры выбирать только на in-sample (< 2025-01-01, как в `bt/runner.py`), результат смотреть на out-of-sample и на walk-forward окнах.
3. GEX, «киты» и ликвидации сначала проверять как **фильтр** для уже существующих сигналов, а не как самостоятельный вход.
4. Для своих собранных данных (GEX, Hyperliquid) честный out-of-sample появится только через 2–3 месяца сбора. Запускать сборщик нужно сразу.

---

## 6. Топ-5: точные шаги подключения

Все команды — на сервере Hetzner. Ключи хранить в `.env` (`chmod 600`), не в git и не в чате. Для бота и для агентов — **разные** ключи; ключи агентов только на чтение.

### Шаг 0. Геопроверка сервера (5 минут)

```bash
curl -s ipinfo.io/country; echo
for u in \
  https://fapi.binance.com/fapi/v1/time \
  https://eapi.binance.com/eapi/v1/time \
  https://api.bybit.com/v5/market/time \
  https://www.okx.com/api/v5/public/time \
  https://open-api.bingx.com/openApi/swap/v2/server/time \
  "https://fapi.bitunix.com/api/v1/futures/market/tickers?symbols=BTCUSDT" \
  https://www.deribit.com/api/v2/public/get_time ; do
  printf '%s %s\n' "$(curl -s -m 15 -o /dev/null -w '%{http_code}' "$u")" "$u"
done
```

- 200 — доступно.
- 451 или 403 — блок по IP. Данные этой биржи не брать: VPN и прокси «под другую страну» — в исключениях `CLAUDE.md`. Заменить другой биржей.
- Для торговых аккаунтов BingX и Bitunix письменно спросить поддержку, допустим ли API-доступ с сервера в DE/FI для аккаунта резидента Молдовы.

### 1. Hyperliquid — «киты» (бесплатно, без ключа)

```bash
# 1) Лидерборд (неофициальный эндпоинт веб-интерфейса, ~39 МБ, 46 983 строки на 27.09)
curl -s https://stats-data.hyperliquid.xyz/Mainnet/leaderboard -o hl_leaderboard.json
# 2) Позиции кошелька (официальный info API; вес 2 из 1 200 в минуту на IP)
curl -s -X POST https://api.hyperliquid.xyz/info -H 'Content-Type: application/json' \
  -d '{"type":"clearinghouseState","user":"0xADDRESS"}'
# 3) Поток сделок: у каждой сделки есть users: [buyer, seller]
#    wss://api.hyperliquid.xyz/ws  →  {"method":"subscribe","subscription":{"type":"trades","coin":"BTC"}}
```

1. Раз в 6 часов выбирать топ-N адресов из лидерборда по капиталу и PnL, **исключив служебные адреса и хранилища**. Первый по капиталу адрес на 27.09 держит $16,2 млрд — это почти наверняка системное хранилище (проверить).
2. Раз в минуту опрашивать `clearinghouseState` для топ-200 адресов: 200 × 2 = 400 единиц веса из 1 200 [оценка].
3. Лимиты WS: 10 соединений, 1 000 подписок, не больше 10 уникальных пользователей в пользовательских подписках ([docs](https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/rate-limits-and-user-limits)). Поэтому позиции брать опросом, а сделки — через WS.
4. Признаки для бэктеста [оценка]:
   - нетто-позиция топ-N по монете и её изменение за 15 минут;
   - кластеры `liquidationPx`;
   - крупные сделки адресов из топа.

   Всё сохранять в Parquet.
5. Для агентов (по желанию): коннектор Coinversa Pulse из каталога claude.ai или `claude mcp add --transport http coinversa https://mcp.coinversa.ai/mcp` (OAuth, ключ Coinversa; бесплатный ключ открывает только публичные маршруты).

### 2. GEX по нескольким площадкам + IBIT

```bash
# OKX: греки по каждому опциону и OI по страйкам (на 27.09 — 3 630 строк OI)
curl -s "https://www.okx.com/api/v5/public/opt-summary?uly=BTC-USD"
curl -s "https://www.okx.com/api/v5/public/open-interest?instType=OPTION&uly=BTC-USD"
# Bybit (только с Hetzner; из США 403): тикеры опционов с OI — наличие гаммы в ответе проверить
curl -s "https://api.bybit.com/v5/market/tickers?category=option&baseCoin=BTC"
# IBIT: цепочка CBOE с задержкой 15 минут, с OI и гаммой (условия CBOE проверить)
curl -sL https://cdn.cboe.com/api/global/delayed_quotes/options/IBIT.json -o ibit.json
# Проверка своего расчёта по истории: Tardis, бесплатно только 1-е число месяца
curl -sO https://datasets.tardis.dev/v1/deribit/options_chain/2026/09/01/OPTIONS.csv.gz
```

1. Добавить в `gex_levels.py` источники OKX, Bybit и IBIT. Перевод страйков IBIT в цену BTC — через отношение цен IBIT/BTC в момент снимка [оценка]; фиксированную константу не брать.
2. Каждые 5 минут сохранять снимок: страйк, экспирация, OI, гамма, площадка → Parquet. Так появится своя история GEX.
3. Отметить в отчётах, что GEX по OI — [оценка]: знак зависит от предположения о позиции дилеров. Amberdata, например, учитывает агрессора сделок ([вендор](https://blog.amberdata.io/gamma-exposure-a-key-indicator-for-crypto-trading-strategy)).
4. Уровень 1 (если п. 1–3 покажут пользу): Massive Options Starter за $29.

   ```bash
   uv tool install "mcp_massive @ git+https://github.com/massive-com/mcp_massive@v0.10.0"
   claude mcp add massive -e MASSIVE_API_KEY=$MASSIVE_API_KEY -- mcp_massive
   ```

   Для бота — REST-снимок цепочки опционов. Путь эндпоинта после переименования Polygon в Massive — проверить в документации.

### 3. Ликвидации, OI и funding

```text
Bybit   wss://stream.bybit.com/v5/public/linear
        {"op":"subscribe","args":["allLiquidation.BTCUSDT","allLiquidation.ETHUSDT"]}   # все ликвидации, 500 мс
OKX     wss://ws.okx.com:8443/ws/v5/public
        {"op":"subscribe","args":[{"channel":"liquidation-orders","instType":"SWAP"}]}  # не все
Binance wss://fstream.binance.com/ws/!forceOrder@arr                                  # 1 в секунду на символ
```

```bash
# Coinalyze: бесплатный ключ (регистрирует сам пользователь), 40 вызовов в минуту
curl -s -H "api_key: $COINALYZE_KEY" https://api.coinalyze.net/v1/future-markets -o markets.json   # коды символов
# далее: /v1/open-interest-history, /v1/funding-rate-history, /v1/liquidation-history (параметры — в docs)
```

- Каскад ликвидаций для стратегии C: сумма ликвидаций за 1–5 минут в сторону движения по Bybit + OKX + Binance. Binance и OKX занижают объём — считать нижней границей [оценка].
- Coinalyze забирать каждый день: внутридневная история хранится только ≈ 5 дней при шаге 5m.

### 4. Доступ агентов к биржам: только чтение

```bash
# Официальный CCXT MCP (stdio). Торговля выключена по умолчанию — не включать.
claude mcp add ccxt -- npx -y ccxt-mcp
# Ключи — только READ-ONLY и отдельные от бота. В docs пример BINANCE_APIKEY / BINANCE_SECRET;
# для BingX по аналогии BINGX_APIKEY / BINGX_SECRET — проверить. Конфиг: ~/.config/ccxt-mcp/config.json
# Официальные AI-skills BingX — чтобы агенты писали код клиента бота:
#   в Claude Code: /plugin marketplace add BingX-API/api-ai-skills  →  /plugin install bingx-ai-skills
# Справка по рынку без ключа:
claude mcp add --transport http coingecko https://mcp.api.coingecko.com/mcp
```

- Bitunix: в CCXT нет. Бот работает через официальный REST/WS (openapidoc.bitunix.com). Комьюнити-MCP с торговлей не ставить.
- Для флота завести `--scope project` → `.mcp.json` в репозитории каждой роли. Каждому агенту — только нужные MCP: описания инструментов занимают контекст.

### 5. Макро и новости — фильтр режима

```bash
# COT: Bitcoin CME (TFF) и золото COMEX (Disaggregated); последний отчёт на 27.09 — за 22.09.2026
curl -s "https://publicreporting.cftc.gov/resource/gpe5-46if.json?\$where=market_and_exchange_names%20like%20'BITCOIN%25'&\$order=report_date_as_yyyy_mm_dd%20DESC&\$limit=4"
curl -s "https://publicreporting.cftc.gov/resource/72hh-3qpy.json?\$where=market_and_exchange_names%20like%20'GOLD%25'&\$order=report_date_as_yyyy_mm_dd%20DESC&\$limit=4"
# Календарь недели (неофициальный фид): архивировать каждую неделю
curl -s https://nfs.faireconomy.media/ff_calendar_thisweek.json -o "ff_$(date +%G-W%V).json"
```

- Правило для бота [оценка, предложение]: не открывать новые позиции за ±N минут до и после событий `impact == High` по USD. N подобрать бэктестом.
- Новости — агентам, через коннекторы claude.ai (claude.ai → Settings → Connectors → Browse): **Parallel Search** (без ключа), **Tavily** (ключ, 1 000 кредитов в месяц), **Alpha Vantage** (NEWS_SENTIMENT и макро, 25 запросов в день). В Claude Code на сервере они появятся сами, если выполнено допущение 2.
- Роль новостей — фильтр режима, а не триггер входа (как в ТЗ).

---

## 7. Безопасность

- Торговлю через MCP не включать. Агент, который читает новости из интернета, может получить внедрённую инструкцию (prompt injection); с правом торговли это прямой риск. Торгует только детерминированный код бота.
- Ключ бота: чтение + фьючерсная торговля, **вывод средств выключен**, IP-белый список — сервер Hetzner (как в ТЗ).
- Для x402 (Laevitas, Nansen) нужен горячий кошелёк USDC на сервере. Держать на нём не больше месячного бюджета.
- Комьюнити-MCP (Apify-скрейперы CoinGlass, TradingView-MCP) не ставить: это нарушение условий источников и неизвестный код.

---

## 8. Ловушки и тупики

| Ловушка | Доказательство |
|---|---|
| CoinGlass Hobbyist за $29 «для ликвидаций» | Внутридневная история с интервалом ≥ 4h, heatmap — только Professional за $699 ([docs](https://docs.coinglass.com/reference/liquidation-heatmap), [docs](https://docs.coinglass.com/reference/aggregated-liquidation-history)) |
| Считать ликвидации по Binance полными | «only the latest one liquidation order within 1000ms» ([docs](https://developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams/All-Market-Liquidation-Order-Streams)); OKX — «doesn't represent the total» |
| TradingView-вебхук как триггер бота | Условия запрещают «automated trading… algorithmic decision-making», вебхуки названы прямо ([policies](https://www.tradingview.com/policies/)) |
| GEX только по Deribit | IBIT — около половины OI по BTC-опционам ([пресса](https://www.coindesk.com/markets/2026/01/13/bitcoin-options-open-interest-extends-dominance-over-futures-damping-btc-volatility)) |
| Бесплатные API новостей и ончейна «как раньше» | CoinDesk закрыл бесплатный уровень 21.05.2026, CryptoPanic — 01.04.2026 (по выдержке), в Dune API на бесплатном плане нет |
| Верхушка лидерборда Hyperliquid = «киты» | В топе служебные адреса и хранилища ($16,2 млрд у первого адреса на 27.09); эндпоинт неофициальный и может измениться |
| Внутридневная история Coinalyze | 1 500–2 000 точек, остальное удаляется каждый день |
| Tardis на один месяц «скачать всё» | Месячная оплата даёт доступ к 4 месяцам истории (по выдержке FAQ — проверить) |
| Подборки «лучших крипто-API» | Не доказывают ни доступность, ни цены; в этом отчёте цены взяты со страниц провайдеров, где их удалось открыть |
| Смена IP сервера ради доступа к бирже | Исключения `CLAUDE.md`: VPN «под чужую страну». Bybit global — не для ЕЭЗ с 01.07.2026; CFD BingX недоступен в Германии |

---

## 9. Что не удалось проверить

- Какие биржи отвечают с Hetzner (все сетевые тесты — из облака в США). Нужен шаг 0.
- Как авторизованы агенты флота: аккаунт claude.ai или API-ключ. От этого зависит, подтянутся ли коннекторы каталога.
- Разрешён ли API-доступ с IP в DE/FI для аккаунтов BingX и Bitunix резидента Молдовы. Ответ — в поддержке бирж.
- Цены со страниц, которые не отрисовались или отдали 403, взяты из поисковых выдержек:
  - CryptoQuant, FMP, Dune (Analyst, Plus), Trading Economics, CryptoPanic, Velo, Databento;
  - CMC Basic (10 000 или 15 000 кредитов).
- Laevitas: работает ли x402 для MCP без Enterprise-ключа — страницы противоречат друг другу.
- Условия CBOE для delayed quotes и ForexFactory-фида (`nfs.faireconomy.media`) при использовании в автоматической системе.
- Bybit: содержит ли ответ `market/tickers?category=option` гамму. Официальный список ограничений Bybit не открывали.
- Условия Binance («Restricted Location»: США, Малайзия, Онтарио) — по выдержке.
- Имена переменных окружения CCXT MCP для BingX (`BINGX_APIKEY`) и схема `config.json`.
- Точный URL MCP Glassnode для `claude mcp add`: в docs указан только `npx add-mcp https://mcp.glassnode.com`.
- Путь эндпоинта снимка опционной цепочки у Massive после переименования.
- Тарифы Coinversa (Starter, Pro): цен на страницах нет.
- Лимит FRED 120 запросов в минуту — по выдержке.
- Доли IBIT, Deribit и CME в BTC-опционах: цифры из выдержек прессы расходятся по месяцам (IBIT 52% в 01.2026; в 04.2026 IBIT $27,61 млрд против $26,9 млрд у Deribit; в 05.2026 Deribit $31,3 млрд против $27 млрд у IBIT). Нужен первоисточник.
- Наш тест: OI BTC-опционов на Deribit 27.09 — 347 749 BTC ≈ $29,4 млрд при $84 600 [оценка: сумма `open_interest` × цена]. С прессой не сверялось.
- Есть ли бесплатный публичный API у Greeks.live; цены Amberdata.
- Принадлежность GitHub-организации `BingX-API` бирже BingX: совпадает с официальным адресом документации bingx-api.github.io, но отдельно не подтверждена.
- S3-архив Hyperliquid (исторические данные) и его стоимость (requester pays).

---

## 10. Источники

Все открыты 27.09.2026. Дата публикации указана, если она есть на странице.

**Claude и MCP**
- Каталог коннекторов claude.ai — SearchMcpRegistry, 27.09.2026 [каталог claude.ai]
- https://code.claude.com/docs/en/mcp — коннекторы claude.ai в Claude Code [provider docs]
- https://docs.ccxt.com/docs/mcp ; https://www.npmjs.com/package/ccxt-mcp (0.1.3, создан 25.08.2026) ; https://github.com/ccxt/ccxt (README) [provider docs]

**Биржи**
- https://github.com/BingX-API/api-ai-skills [provider docs]
- https://bingx.com/en/support/articles/17088995856271 (04.08.2026) [provider docs]
- https://openapidoc.bitunix.com/doc/market/get_kline.html (по выдержке) [provider docs]
- https://www.bitunix.com/hub/helpcenter/article/bitunix-restricted-regions-and-user-eligibility-notice?id=146 [provider docs]
- https://www.binance.com/en/support/announcement/detail/07d45cdd3831498f8a4ff339031a8480 (20.08.2026) [provider docs]
- https://developers.binance.com/en/docs/agent-native/mcp-server (изм. 25.09.2026) [provider docs]
- https://developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams/All-Market-Liquidation-Order-Streams [provider docs]
- https://github.com/bybit-exchange/trading-mcp ; npm `bybit-official-trading-server` 2.1.22 (22.09.2026) [provider docs]
- https://bybit-exchange.github.io/docs/v5/websocket/public/all-liquidation [provider docs]
- https://crypto.news/bybit-limits-eea-access-as-mica-deadline-closes-in/ [пресса]
- https://www.okx.com/docs-v5/agent_en/ ; https://www.okx.com/docs-v5/en/ ; npm `okx-trade-mcp` 1.2.8 (17.06.2026) [provider docs]
- https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/rate-limits-and-user-limits [provider docs]
- https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/websocket/subscriptions [provider docs]
- https://github.com/Coinversaa/mcp-server (0.12.0, 21.09.2026) [provider docs]
- https://docs.deribit.com/articles/rate-limits [provider docs]

**Деривативы и опционы**
- https://api.coinalyze.net/v1/doc/ [provider docs]
- https://www.coinglass.com/pricing ; https://docs.coinglass.com/reference/mcp-service ; https://docs.coinglass.com/reference/liquidation-heatmap ; https://docs.coinglass.com/reference/aggregated-liquidation-history ; https://docs.coinglass.com/reference/liquidation-order [provider docs]
- https://www.laevitas.ch/ ; https://apiv2.laevitas.ch/mcp/ ; https://apiv2.laevitas.ch/x402/ [provider docs]
- https://www.amberdata.io/pricing ; https://blog.amberdata.io/gamma-exposure-a-key-indicator-for-crypto-trading-strategy [вендор]
- https://tardis.dev/ ; https://docs.tardis.dev/downloadable-csv-files ; https://docs.tardis.dev/historical-data-details/deribit ; https://docs.tardis.dev/faq/billing-and-subscriptions [provider docs]
- https://massive.com/pricing ; https://github.com/massive-com/mcp_massive [вендор / provider docs]
- https://databento.com/blog/updates-to-subscription-pricing (по выдержке) [provider docs]
- https://www.coindesk.com/markets/2026/01/13/bitcoin-options-open-interest-extends-dominance-over-futures-damping-btc-volatility (13.01.2026) [пресса]
- https://www.kucoin.com/blog/Blackrock-IBIT-Options-Growth-Overtakes-Deribit-in-2026 [пресса / биржевой блог]

**Ончейн и киты**
- https://developer.whale-alert.io/api-account/documentation ; https://whale-alert.io/faq.html [provider docs]
- https://info.arkm.com/announcements/how-to-use-the-arkham-api-with-ai-agents (27.04.2026) [provider docs]
- https://docs.nansen.ai/getting-started/credits ; https://docs.nansen.ai/mcp/connecting [provider docs]
- https://docs.glassnode.com/integrations-and-tools/glassnode-mcp-server ; https://studio.glassnode.com/pricing [provider docs]
- https://userguide.cryptoquant.com/api/mcp-server-beta [provider docs]
- https://docs.dune.com/api-reference/agents/mcp ; https://docs.dune.com/api-reference/overview/rate-limits [provider docs]
- https://comparedge.com/tools/dune-analytics/pricing [агрегатор]
- https://academy.santiment.net/mcp-connector/ ; https://academy.santiment.net/products-and-plans/sanapi-plans/ [provider docs]

**Рынок и новости**
- https://docs.coingecko.com/ai-integration/mcp-server ; https://www.coingecko.com/en/api/pricing [provider docs]
- https://coinmarketcap.com/api/mcp/ ; https://coinmarketcap.com/api/pricing/ [вендор]
- https://data.coindesk.com/blogs/changes-to-coindesk-data-indices-api-free-tier-access (17.04.2026) [provider docs]
- https://www.tavily.com/pricing ; https://exa.ai/docs/admin/pricing ; https://lunarcrush.com/pricing [вендор]
- https://cryptopanic.com/developers/api/plans (не отрисовалась, данные — из выдержки поиска) [агрегатор]

**Макро**
- https://publicreporting.cftc.gov (наборы `gpe5-46if`, `72hh-3qpy`) [офиц., тест 27.09]
- https://fred.stlouisfed.org/docs/api/api_key.html [provider docs]
- https://nfs.faireconomy.media/ff_calendar_thisweek.json [тест 27.09]
- https://github.com/alphavantage/alpha_vantage_mcp ; https://www.alphavantage.co/premium/ [provider docs]
- https://apis.io/plans/tradingeconomics/tradingeconomics-plans-pricing/ [агрегатор]

**Условия использования**
- https://www.tradingview.com/policies/ [provider docs]

**Наши тесты 27.09.2026** (облако Google, США)
- fapi.binance.com и eapi.binance.com — 451; api.bybit.com — 403.
- okx.com, open-api.bingx.com, fapi.bitunix.com, deribit.com, api.hyperliquid.xyz, api.coingecko.com, data.binance.vision, public.bybit.com, history.deribit.com, publicreporting.cftc.gov, nfs.faireconomy.media, cdn.cboe.com (редирект), mempool.space, api.llama.fi — 200.
- datasets.tardis.dev: 01.09.2026 — 200, 02.09.2026 — 401.
- stats-data.hyperliquid.xyz/Mainnet/leaderboard — 200, 46 983 строки.

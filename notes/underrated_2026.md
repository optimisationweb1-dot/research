# Недооценённые онлайн-ниши 2025–2026: данные, API, тендеры, открытые данные, сервисы для продавцов

Дата: 26.09.2026. Поток «underrated niches» мастер-плана. ID кандидатов — UN-01…UN-10. Копия таблицы — `notes/underrated_2026.csv`.
Только исследование: аккаунты не создавались, формы не отправлялись, ничего не покупалось. Открытые API (MTender, World Bank, TED, USAspending, Prozorro, dataset.gov.md, WordPress.org) читались без регистрации.
Это исследование, а не юридическая или налоговая консультация. Пункты «к юристу / бухгалтеру / MITP» — для специалистов.

**Метки:** [official] — закон, госорган, официальный открытый API/портал; [provider docs] — справка или условия самого провайдера; [provider data] — выгрузка из публичного API/страниц провайдера; [press]; [vendor] — сайт продавца или конкурента; [forum]; [интерпретация]; [оценка] — с формулой; [база] — уже проверено в проекте, здесь не перепроверялось.

**Метод и ограничения (важно).**
- Бюджет WebSearch этой сессии исчерпан (200/200) до начала потока. Google без JS не отдаёт выдачу, DuckDuckGo даёт капчу, Brave — 429, Mojeek — 403. Bing через curl работает **частично**: часть запросов он «обрезает» до первого слова (выдача про слово «best»). Поэтому:
  - тест недооценённости сделан по **выдаче Bing (US), а не Google**; для запроса «best online business ideas 2026» использован близкий запрос «profitable online business ideas 2026» (раздел 1);
  - всё остальное — прямые запросы к известным URL и открытым API. Отсюда пробелы — раздел 6.
- Цены конкурентов DevelopmentAid, devex, dgMarket, Termene.ro, fundsforNGOs, FMCSA-страницы закрыты Cloudflare/403 — не прочитаны.

**Допущения по умолчанию** (вопросы не задавались; решение пользователя 26.09 — «сначала доход, налоги потом»):
1. Крипто-выплата (USDC/USDT на свой KYC-аккаунт Bybit/BingX или свой кошелёк) достаточна. Крипту получает **владелец лично**; Global Web SRL получает только фиат (SRL не может принимать крипту — [база] `crypto_rails_2026.md`, TL;DR п. 3).
2. Рельсы [база]: Creem → USDC (Polygon), 2%, минимум $50, выплаты 1-го и 15-го, холд 7–12 дней; x402 → USDC на свой адрес; банк: SWIFT/SEPA на OTP (входящие для компаний бесплатны, банк просит договор и счёт). AWS/Snowflake/Datarade проверены здесь заново (раздел 2.1).
3. Курс: 1 USD = 17.7706 MDL, 1 EUR = 20.2078 MDL (НБМ 25.09.2026, [база]); **1 EUR ≈ 5 RON — допущение, не проверено**; 1 EUR ≈ 1.137 USD.
4. Часы владельца = решения, проверка RO/RU, письменная переписка. Работу делает флот.

---

## TL;DR

1. **Тест недооценённости пройден только темами «госзакупки/тендеры», «открытые госданные», «гео-данные» и «инструменты для продавцов конкретного маркетплейса» (eMAG).** В 21 прочитанной статье из топ-10 Bing по трём запросам нет ни одного упоминания tender/procurement, open data, GIS [provider data: страницы, 26.09.2026]. Зато там есть: «Job board and newsletter curator» (Whop #40), «Collect and sell data» (Whop #98), «Sell templates», «Sell Lesson Plans» (Penny Hoarder #9), «Translating business» (Whop #72), «Website accessibility auditing» (Whop #47), «Online Tools Directory» (Startupill #35), «Grant writing» (Whop #68). **Поэтому исключены:** нишевые джоб-борды, каталоги с платным размещением, шаблоны для профессий (в т. ч. «planificări» для учителей RO/MD), пакеты локализации (раздел 1.3).
2. **Маркетплейсы данных для Молдовы почти закрыты.** AWS Marketplace / Data Exchange: платные продукты — только продавцы из списка юрисдикций, Молдовы нет [provider docs]. Snowflake Marketplace: платные листинги — только 20 стран, выплата через Stripe Express, Молдовы нет [provider docs]. **Datarade — единственный рабочий:** бесплатный план $0 + 30% комиссии, 3 листинга, 3 запроса, только зарегистрированные компании (Global Web SRL подходит); сделку и оплату провайдер ведёт сам [provider docs, 26.09.2026].
3. **Тендерная аналитика — «недооценена в списках», но не на рынке.** Молдова: Notis.md уже шлёт фильтрованные уведомления MTender/инсолвентности/разрешений в Telegram и анонсирует «Tender Intelligence — în curând»; achizitii.md (Simpals) даёт бесплатный поиск и берёт 35 лей за лот при участии [vendor]. Румыния: licitatia.ro — 70–162 лей/мес без НДС (годовой план), SicapRadar (licitatii-publice.ro) — 30 дней бесплатно, **Licitatii.AI** — «lansăm în curând» (270 000+ операторов, 17 000+ годовых планов закупок в индексе на 05.08.2026) [vendor]. Окно для «ИИ-аналитики тендеров RO/MD» закрывается в 2026.
4. **Где пусто по проверке:** (а) ИИ-разбор документации конкретной процедуры (caiet de sarcini) поштучно; (б) тендеры, которые молдавская IT-компания **имеет право** выиграть в ЕС (Молдова — сторона GPA ВТО с 14.07.2016 [official]) + ИТ-заказы ООН/ВБ в Молдове; (в) тендеры ЕС, где **WCAG — требование**: в TED 178 уведомлений за 2024, 303 за 2025 и 432 за 2026 по 26.09 [official: TED API]; (г) платный API реестра юрлиц Молдовы (открытый еженедельный файл ASP: 302 952 записи, 169 447 без даты ликвидации) — платного API-конкурента не найдено, но и спроса не найдено.
5. **Главные новые факты для мастер-плана:**
   - **Creem ограничивает** «Job boards», «Advertising in newsletters, on websites…», «API resellers» и «Services of any kind» — только с подтверждённой историей платежей в другом процессоре [provider docs]. Это ставит под вопрос рельс Creem → USDC у CA-04 (джоб-борд) и CA-10 (платные профили каталога).
   - **Рынок WooCommerce в Молдове крошечный:** плагин maib — 200 активных установок, Victoriabank — 30, maib MIA — 10; всё бесплатно и поддерживается [provider data: api.wordpress.org; GitHub]. Платные плагины для MD — тупик.
   - **Синтетические датасеты от Claude для обучения ИИ продавать нельзя:** Commercial Terms (с 17.06.2025) D.4 запрещают «train competing AI models», Usage Policy (с 15.09.2025) — «Utilization of inputs and outputs to train an AI model… without prior authorization» [provider docs: Anthropic].
6. **Итог [оценка, раздел 4]:** все 10 кандидатов слабее ниши №1 (Upwork + Apify): лучший балл UN-07 ≈ 20 против 140 у N7 в `niches_b2b_services.md`. Рекомендация: **не запускать отдельно, а строить UN-07 и UN-03 как внутренние ленты заказов для самой Global Web SRL** (WCAG-тендеры ЕС; ИТ-RFQ ПРООН/ВБ в Молдове), и продавать подписку, только если лента соберёт аудиторию. UN-01 — единственный «продукт на продажу» с проверенной платёжеспособностью рынка (RO-фирмы уже платят за мониторинг), но конкуренты с ИИ выходят прямо сейчас.

---

## 1. Тест недооценённости

### 1.1 Что проверяли (Bing US, 26.09.2026)

| Запрос | Топ-10 (домен) | Прочитано | Не открылось |
|---|---|---|---|
| «best online business ideas 2026» → Bing отдал словари по слову «best»; взят близкий запрос **«profitable online business ideas 2026»** | whop.com, ideaproof.io, 99businessideas.com, xero.com, startupill.com, shopify.com (ecommerce ideas), omnisend.com, shopify.com (online business ideas), fundwell.com, marketingscoop.com | 9 | ideaproof.io (JS) |
| «side hustles 2026» | dailyremote.com, forbes.com, money.usnews.com, jobright.ai, thepennyhoarder.com, inc.com, forbes.com (2), blog.theinterviewguys.com, sidehustlenation.com, journeybee.io | 6 | Forbes ×2, Inc (403), US News (обрыв), SHN (блок) |
| «passive income ideas 2026» | investopedia.com, thecollegeinvestor.com, wellkeptwallet.com, ramseysolutions.com, finance.yahoo.com (перепечатка Penny Hoarder), sidehustlenation.com/passive-income, dollarsmartguides.com, thepennyhoarder.com, marksinsights.com | 6 | Investopedia (402), College Investor (403), marksinsights (блок) |

Итого прочитана 21 страница из 29. **Отклонение от задания:** Google недоступен, использован Bing.

### 1.2 Правило классификации
- **L1 — провал:** в списке есть та же модель **и** та же тема/клиент (например, «Sell lesson plans» → пакеты для учителей).
- **L2 — пограничный (флаг ⚠):** в списке только общая модель без темы («Sell SaaS», «Collect and sell data», «micro-SaaS… freemium API access»). Кандидат допускается с флагом.
- **L3 — проходит:** ни модели, ни темы в списках нет.

Подсчёт упоминаний по ключам в 21 странице [provider data, 26.09.2026]: «tender|procurement|government contract|RFP» — **0**; «open data|public data|government data» — **0**; «GIS|geospatial|map data» — **0**; «job board» — Whop, DailyRemote, Jobright, InterviewGuys, Journeybee; «lesson plan» — Penny Hoarder/Yahoo, SHN, 99businessideas; «template» — почти везде.

### 1.3 Исключено тестом (L1) — с доказательствами

| Идея из задания | Где найдена в топ-10 | Решение |
|---|---|---|
| Нишевые джоб-борды | Whop #40 «Job board and newsletter curator»; уже `content_affiliate_2026.md` CA-04 | Исключено |
| B2B-каталоги с платным размещением | Startupill #35 «Online Tools Directory»; уже CA-10, CA-13 | Исключено (+ ограничения Creem, раздел 2.6) |
| Пакеты документов/шаблонов для профессий RO/RU (в т. ч. «planificări calendaristice» для учителей) | Penny Hoarder #9 «Teachers (or Not): Sell Lesson Plans»; SHN — Teachers Pay Teachers; Whop #22 «Sell templates»; Startupill #2, #6, #7; DailyRemote #22 | Исключено. Юридические/бухгалтерские шаблоны ещё и попадают под исключение «юридические советы» |
| Пакеты локализации | Whop #72 «Translating business», #65 «AI video dubbing and localization»; Shopify #19 «Become a translator»; уже N11, CN-10 | Исключено |
| Продажа списков лидов (новые фирмы MD, новые перевозчики FMCSA) | Whop #82 «Lead generation»; WellKeptWallet #14 «Start a Lead Generation Website» | Исключено (и ловушка, раздел 5) |

Пограничные (L2): «продукты данных» (Whop #98 «Collect and sell data»), «ниша API» (99businessideas #4 «freemium API access»), инструменты для продавцов маркетплейсов (Startupill #41: KDP Wizard / Merch Wizard «for Amazon sellers»), дайджест грантов (Whop #68 «Grant writing» — смежно), тендеры по доступности (Whop #47 «Website accessibility auditing» — смежно).

---

## 2. Находки

### 2.1 Маркетплейсы данных: выплата в Молдову

| Площадка | Молдова | Детали | Источник |
|---|---|---|---|
| AWS Marketplace / AWS Data Exchange (платные) | **Нет** | «You must be a permanent resident or citizen in an eligible jurisdiction, or a business entity organized or incorporated» там же. Список: Australia, Bahrain, Colombia, EU, Hong Kong, India (только внутри Индии), Israel, Japan, New Zealand, Norway, Qatar, South Korea, Switzerland, UAE, UK, US. Нужен банковский счёт со SWIFT «in an eligible jurisdiction» | [provider docs: docs.aws.amazon.com, прочитано 26.09.2026, дата страницы не указана] |
| Snowflake Marketplace (paid listings) | **Нет** | Только если billing address в одной из 20 стран (Australia, Canada, Colombia, Finland, France, Germany, Ireland, Israel, Italy, Japan, KSA, Mexico, Netherlands, New Zealand, Norway, Singapore, Sweden, Switzerland, UK, US). Выплата — «Stripe Express connected account» | [provider docs: docs.snowflake.com/collaboration/provider-becoming, 26.09.2026] |
| Datarade | **Да, косвенно** | «We welcome legally registered businesses… We do not onboard individual providers with unregistered businesses». Планы: Commission-only $0/год + **30%**, 3 листинга, 3 запроса, 5 предложений; Bronze $6 000/год + 20%; Silver $12 000/год + 15%. Datarade — витрина и лиды; договор и оплату ведёт провайдер → рельс свой (SWIFT/SEPA на SRL или USDC-инвойс) [интерпретация] | [provider docs: providers.datarade.ai/apply, 26.09.2026] |

Вывод: «данные на маркетплейсах» для Молдовы = только Datarade или свой сайт (Creem/x402). Спрос Datarade подтверждается лишь фразой самого Datarade «thousands of companies use Datarade every month» [vendor].

### 2.2 Госзакупки: объёмы и конкуренты

**Молдова (MTender).**
- Открытый OCDS API работает без ключа: `public.mtender.gov.md/tenders/?offset=…`. За 01–07.09.2026 — **2 287 обновлённых записей** (не только новые тендеры, но и смены статуса) [official: MTender API, 26.09.2026].
- achizitii.md (Simpals): бесплатный поиск тендеров, контрактов, планов; поставщик платит **35 лей (с НДС) за лот** дороже 2 000 лей, для первых 15 лотов процедуры; госорганы — техподдержка **3 000 MDL/год или 500 MDL/мес** [vendor: achizitii.md/info/payment, 26.09.2026]. Это доказательство, что молдавские госорганы платят за мелкие подписки.
- Notis.md: мониторинг законодательства, коммерческих торгов, госзакупок, инсолвентностей, разрешений по IDNO; Telegram-алерты; «Tender Intelligence — În curând: repere și intervale de preț, loturi și concurenți comparabili, istoricul furnizorilor și autorităților» [vendor: notis.md, 26.09.2026]. Совпадает с выводом `telegram_2026.md` (Notis уже занял уведомления).
- openmoney.md — бесплатная связка компаний, контрактов, тендеров [vendor].

**Румыния (SEAP/SICAP).**
- licitatia.ro: START 90 лей/мес (70 лей без НДС при годовом плане, 1 сфера, 1 e-mail, «decriptare documentații»), BUSINESS 133/108 лей, MEGA 216/162 лей; пакет SEAP (аккаунт, электронная подпись) 400 → 200 лей + НДС [vendor: licitatia.ro/abonamente.html, 26.09.2026].
- licitatii-publice.ro (SicapRadar): мониторинг 24/7, похожие процедуры, история автора закупки, QuickSource (цены продуктов из SICAP), 30 дней бесплатно; цены на странице нет [vendor].
- **Licitatii.AI** — лист ожидания, «Lansăm în curând»: мониторинг по профилю фирмы, реальные конкуренты процедуры, годовые планы закупок. «270.000+ operatori economici indexați, 240.000+ documente constatatoare, 17.000+ planuri anuale… la data de 5 august 2026» [vendor: licitatii.ai, 26.09.2026]. sicap.ai существует (Vercel checkpoint, 429) — содержимое не прочитано.
- Разбор документации конкретной процедуры ИИ (caiet de sarcini → требования, критерии, риски, чек-лист) у licitatia.ro и SicapRadar не заявлен; у Licitatii.AI — «documentația atașată și termenele deja calculate» [наблюдение по 3 сайтам, другие не проверялись].
- Объём SICAP за 2025–2026 — **нет данных** (data.gov.ro рвал соединение).

**Украина, Молдова — МФИ и доноры.**
- World Bank procurement notices API [official, 26.09.2026]:

  | Страна | 2025: IFB / REOI / Contract Award | 2026 по 26.09: IFB / REOI / Contract Award |
  |---|---|---|
  | Moldova | 21 / 27 / 535 | 17 / 21 / 237 |
  | Ukraine | 91 / 107 / 463 | 80 / 102 / 142 |

- ПРООН: на странице активных уведомлений 1 001 объявление, из них **13 — UNDP-MDA/MOLDOVA** и **23 — UNDP-UKR** (26.09.2026). Среди молдавских — «Web Application and GIS Developer», «Backend, Integration and Data Migration Developer», «Development of the Data Warehouse System for the MoLSP», «Cybersecurity Readiness Assessment», ИТ-оборудование [official: procurement-notices.undp.org].
- Ukraine Facility: «entered into force on 1 March 2024 and covers the years 2024 to 2027, offers up to €50 billion» [official: enlargement.ec.europa.eu; программа 2024 г. действует].
- Prozorro public API работает без ключа (`public-api.prozorro.gov.ua/api/2.5/tenders`) [official, 26.09.2026].
- UNGM: подписка «UNGM Pro» с Tender Alert Service существует; цена на странице не показана → **нет данных** [official: ungm.org].
- DevelopmentAid, devex, dgMarket — платные подписки на донорские тендеры (известные игроки), но страницы цен отдали 403 → **нет данных**.

**Доступ молдавских фирм к тендерам ЕС.** Молдова — сторона Соглашения ВТО о госзакупках (GPA) с **14.07.2016**, Украина — с 18.05.2016 [official: wto.org]. Значит, на тендеры ЕС, покрытые GPA (выше порогов, покрытые заказчики), молдавский поставщик допускается [интерпретация; конкретные тендеры — проверять условия участия].

**WCAG как требование в тендерах.** TED API, полнотекстовый поиск «WCAG» [official, 26.09.2026]: 178 уведомлений в 2024, **303 в 2025**, **432 в 2026 по 26.09** (рост ×1.8 за 9 мес. к прошлому году). «web accessibility» — 14, «accessibility audit» — 8 (с 2025): аудит отдельно закупают редко, WCAG вшит в тендеры на сайты и ИТ-системы. США (USAspending, контракты с ключом «Section 508»): 78 в 2025, 61 в 2026 по 25.09 [official].

### 2.3 Открытые данные Молдовы: реестр юрлиц
- ASP публикует на dataset.gov.md **еженедельный XLSX** «Date din Registrul de stat al unităților de drept…»; последняя версия — 21.09.2026, 404 ресурса (архив недель), лицензия «License Not Specified» [official: dataset.gov.md].
- Файл 21.09.2026: **302 952 записи**, из них **169 447 без даты ликвидации** (121 649 SRL, 27 301 ÎI); зарегистрировано в 2025 — 9 780, в 2026 по 21.09 — 6 469 [official, подсчёт по файлу].
- Поля: IDNO, дата регистрации, название, форма, адрес, код CUATM, **список руководителей и учредителей (ФИО)**, CAEM (нелицензируемые и лицензируемые виды), дата ликвидации. ФИО — персональные данные → риск (раздел 5).
- Бесплатные сайты поиска: srl.md (ссылается на тот же датасет), firme.md (AdSense), openmoney.md, idno.md (за Cloudflare) [vendor]. Платного API для разработчиков не найдено (проверка ограничена 15 доменами, поисковика не было).

### 2.4 Инструменты для продавцов маркетплейсов (eMAG)
- eMAG Marketplace: **«peste 64.000 de selleri» в 2024**; >10 000 румынских продавцов в cross-border (BG, HU), их экспорт — 552 млн лей в 2024; 28 млн офферов в RO, 15 млн в BG, 17 млн в HU [press/official-корп.: about.emag.ro, 04.06.2025]. На Sellers’ Day 24.09.2025 — «cei peste 64.000 de selleri», eMAG запускает **свои** ИИ-инструменты (Project Mira — виртуальный ассистент продавца) и финансирование eMAG Capital [about.emag.ro, 24.09.2025].
- easySales (мультиканальный SaaS для eMAG и др.): от **35 €/мес**; Accelerator 107 €/мес при годовой оплате (119 € помесячно), до 1 500 заказов; Smart 179 €/мес; репрайсинг, ИИ-заполнение атрибутов, переводы, e-Factura [vendor: easy-sales.com/ro/pricing, 26.09.2026].
- API eMAG Marketplace существует (клиенты на GitHub: chawel/python-emag, JupiterSells/onsell_inventory_emag) [forum/GitHub]; официальная документация — в кабинете продавца, не прочитана. Есть ли в API отзывы и вопросы покупателей — **проверить**.

### 2.5 E-commerce-интеграции Молдовы — рынок мал
WordPress.org, активные установки [provider data: api.wordpress.org, 26.09.2026]: maib for WooCommerce — 200; maib e-Commerce Checkout — 70; Victoriabank — 30; maib MIA — 10; Victoriabank MIA/StarCard — 10; Nova Post (UA-плагин Morkva) — 10. Все бесплатные, обновлены в 07–09.2026 (alexminza, maib-ecomm на GitHub). Для сравнения Румыния: SamedayCourier 4 000, SmartBill 5 000, NETOPIA 10 000, «Garanție SGR» 100.

### 2.6 Новое по рельсам: ограничения Creem
Страница Account Reviews [provider docs: docs.creem.io, прочитано 26.09.2026, без даты]:
- **Prohibited:** «Regulated services such as… telemarketing…», «Products that operate marketplaces…», «Online traffic and engagement services», «NFT & crypto asset products», PLR/MRR без прав.
- **Restricted (строгая проверка, нужна история в другом процессоре, chargeback/refund rate, «established and proven track record»):** «Services of any kind», **«Job boards»**, **«Advertising in newsletters, on websites, or in social media posts»**, **«API resellers»**, генеративный ИИ (изображения/видео).
- Следствия: SaaS-подписка на **собственные** данные/алерты (UN-01…UN-10) — не в списках [интерпретация]; джоб-борд (CA-04) и платные размещения в каталоге (CA-10) через Creem — под вопросом для нового продавца без истории.

### 2.7 Прочее
- 999.md: `partners-api.999.md` существует (401 без ключа), условия партнёрства не опубликованы. Энтузиасты используют внутренний GraphQL фронтенда (репозиторий fxmidaaa/pret-drept, 07.2026) — это скрейпинг вопреки ToS, в проекте исключён.
- FMCSA: по сниппету Bing, FMCSA «published a Federal Register Notice… announcing Motus, the new USDOT Registration System»; сайт fmcsa.dot.gov отдал 403 — детали не прочитаны.
- Horizon Europe: Молдова в списке ассоциированных стран [official: research-and-innovation.ec.europa.eu, 26.09.2026].

---

## 3. Кандидаты

Таблица разделена на две, связь по ID. P — вероятность первого дохода за 30 дней от старта [оценка]. Потолок — месячная выручка на 6-й месяц [оценка, формула]. Ч/нед — часы владельца. Недооц. — класс теста (раздел 1.2).

### 3A. Что, кому, спрос, конкуренция, выплата

| ID | Ниша (формат × тема × рынок) | Продукт | Монетизация | Доказательства спроса (2025–2026) | Конкуренция | Выплата | Крипто | Недооц. |
|---|---|---|---|---|---|---|---|---|
| UN-01 | SaaS поштучно × ИИ-разбор документации процедуры SICAP (caiet de sarcini → требования, критерии, риски, чек-лист, черновик вопросов на разъяснение) × RO, МСБ-участники тендеров и консультанты | Веб-приложение + расширение Chrome для публичных страниц e-licitatie.ro | 49 лей за процедуру или 99–149 лей/мес [оценка] | RO-фирмы платят за мониторинг 70–162 лей/мес (licitatia.ro); SicapRadar; Licitatii.AI индексирует 270 000+ операторов [vendor] | licitatia.ro, SicapRadar, Termene.ro, Licitatii.AI (скоро), sicap.ai (не прочитан); поштучного ИИ-разбора у проверенных нет | Creem (карта) → USDC владельцу; или счёт SEPA → SRL (63.11 — IT, проверить) | yes | L3 |
| UN-02 | Дайджест + алерты × тендеры восстановления Украины и МФИ/доноров в Украине и Молдове (Prozorro, DREAM, WB, EBRD, UNDP) × EN, МСБ ЕС/Румынии и консультанты | Еженедельный дайджест + фильтры CPV/сектор + ИИ-резюме | 29–49 €/мес [оценка] | WB 2026: UA 80 IFB + 102 REOI, MD 17 + 21; UNDP: UKR 23, MDA 13 активных; Ukraine Facility до €50 млрд 2024–2027 [official] | DevelopmentAid, devex, dgMarket, UNGM Pro (цены не прочитаны), бесплатные официальные порталы | Creem → USDC | yes | L3 |
| UN-03 | Лента заказов × тендеры ЕС, на которые молдавская IT-фирма имеет право (GPA) + ИТ-RFQ ООН/ВБ в Молдове, с резюме RO/RU × резиденты MITP | Telegram/e-mail-лента + веб-кабинет; параллельно — лента для самой Global Web SRL | 300–600 MDL/мес [оценка] | Молдова в GPA с 14.07.2016 [official]; UNDP-MDA: 13 активных, в т. ч. веб/ГИС/хранилище данных [official]; резидентов MITP 3 925 ([база] CA-10) | TED — бесплатные алерты; DevelopmentAid; Notis (только MD) | Банк: SRL → SRL, MDL/EUR | no | L3 |
| UN-04 | API × реестр юрлиц Молдовы (IDNO, статус, CAEM, CUATM, дата ликвидации; без ФИО по умолчанию) × EN/RO, интеграторы ERP/e-Factura, KYB-агрегаторы, финтех | REST API + x402 pay-per-call + листинг на Datarade | $19–99/мес; $0.005–0.01 за вызов [оценка] | Открытый еженедельный файл: 302 952 записи, 9 780 регистраций в 2025 [official]. Платёжеспособный спрос — **нет данных** | Бесплатные сайты srl.md, firme.md, openmoney.md; платного API не найдено | Creem → USDC; x402 → USDC | yes | L2 ⚠ |
| UN-05 | Датасет × нормализованные награды госзакупок MD + UA (+RO) в OCDS, EN × аналитики, bid-tech, исследователи рынка | Помесячные файлы + API, листинг на Datarade | Разовые/годовые лицензии ($500–3 000) [оценка] | Datarade: «thousands of companies… every month» [vendor]; AWS/Snowflake Молдову не пускают [provider docs] | Бесплатные исходные API; конкуренты-агрегаторы — нет данных | Инвойс → SWIFT/SEPA на SRL (Datarade берёт 30%); возможен USDC-инвойс | partial | L2 ⚠ |
| UN-06 | Micro-SaaS × ИИ-ответы на вопросы и отзывы + алерты «здоровья» офферов (потеря Buy Box, цена, сток) через официальный API eMAG × RO (затем BG/HU) | Веб-приложение, ключ API даёт продавец | 9–19 €/мес [оценка] | 64 000+ продавцов, 10 000+ cross-border [about.emag.ro 2025] | easySales 35–179 €/мес (полный пакет); eMAG Project Mira (сама платформа) | Creem → USDC | yes | L2 ⚠ |
| UN-07 | Лента + алерты × тендеры ЕС (TED) с требованием WCAG/EN 301 549 × EN, веб-агентства и студии с компетенцией доступности; параллельно — лента для самой Global Web SRL | Ежедневная выборка TED + резюме + дедлайны | 29–59 €/мес [оценка] | TED «WCAG»: 303 (2025), 432 (2026 по 26.09) [official]; EAA с 28.06.2025 [база] | Общие тендерные сервисы; нишевого по WCAG не найдено (проверка ограничена) | Creem → USDC | yes | L2 ⚠ (Whop #47 смежно) |
| UN-08 | Отчёты × обоснование предполагаемой стоимости закупки по истории контрактов MTender × RO, госзаказчики Молдовы (buyer-side) | PDF-отчёт/кабинет «ценовые ориентиры» | 3 000 MDL/год [оценка по аналогу achizitii.md] | Госорганы платят achizitii.md 3 000 MDL/год за поддержку [vendor]; 2 287 обновлений MTender/нед. [official] | Notis «Tender Intelligence» (в т. ч. интервалы цен, для поставщиков) — скоро | Банк: госорган → SRL (контракт малой стоимости) | no | L3 |
| UN-09 | API × гео-данные Молдовы: населённые пункты (CUATM), почтовые индексы, нормализация адресов RO/RU, геокодинг × e-shop, курьеры, банки | API + датасет | $19–49/мес [оценка] | **нет данных**; косвенно против: MD WooCommerce-плагины 10–200 установок [provider data] | Google Maps/OSM; местных платных — не найдено | Банк MDL → SRL; Creem → USDC для иностранных | partial | L3 |
| UN-10 | Дайджест × конкурсы ЕС (Horizon Europe, где Молдова ассоциирована, EU4Business и др.) + запросы партнёров × RO/RU/UA/EN, МСБ, НКО, вузы MD/UA | Еженедельная рассылка + фильтры | 10–20 $/мес [оценка] | Молдова ассоциирована с Horizon Europe [official]; платёжеспособность НКО — нет данных | Национальные контактные пункты (бесплатно), fundsforNGOs Premium, DevelopmentAid (цены не прочитаны) | Creem → USDC; банк | yes | L2 ⚠ (Whop #68 смежно) |

### 3B. Исполнимость, тест, сроки, потолок

| ID | Флот без лица/GPU/звонков | IT Park (для фиата через SRL) | Самый дешёвый 14-дневный тест | Дней до 1-го $ | P(30 дн.) | Потолок м6 [оценка] | Ч/нед |
|---|---|---|---|---|---|---|---|
| UN-01 | Да: парсинг PDF/.p7s, извлечение требований, RO-тексты; владелец проверяет RO | 63.11 SaaS — вероятно IT (MITP) | MVP на 20 публичных процедурах; RO-лендинг + 3 SEO-статьи; 3 разбора бесплатно, дальше 49 лей через Creem; посты в RO-сообществах по закупкам (не рассылки). Критерий: ≥30 бесплатных разборов, ≥2 оплаты | 35 | 0.08 | 25 подписок × 120 лей = 3 000 лей ≈ €600 ≈ **$680** | 4 |
| UN-02 | Да; UA-тексты владелец проверяет частично | 63.11/63.12 — проверить | Лендинг EN + 2 бесплатных выпуска; посты в LinkedIn-группах; платный тариф 29 €. Критерий: ≥50 подписчиков, ≥1 оплата | 45 | 0.04 | 15 × $39 = **$585** | 2 |
| UN-03 | Да | 63.11/63.12 — проверить | Лента из TED (CPV 72/48) + UNDP-MDA + WB MD с флагом GPA; 10 знакомым IT-фирмам бесплатно на 2 недели (тёплый круг владельца). Критерий: 3 согласия платить 300 MDL | 40 | 0.05 | 10 × 500 MDL = 5 000 MDL ≈ **$281** | 2 |
| UN-04 | Да | 63.11 — IT | Бесплатный эндпоинт (100 вызовов/день) + документация; x402-эндпоинт; листинг Datarade (бесплатный план). Критерий: ≥3 ключа от компаний | 45 | 0.03 | 5 × $49 + 2 000 вызовов × $0.01 = **$265** | 1 |
| UN-05 | Да | Продажа данных — 63.11? проверить | 1 листинг на Datarade + образец. Критерий: ≥1 запрос покупателя | 90 | 0.02 | 1 сделка в квартал × $1 500 × 0.7 / 3 ≈ **$350** | 1 |
| UN-06 | Да; BG/HU без проверки владельцем — начать только с RO | 63.11.13 — IT | RO-лендинг + лист ожидания; 5 знакомых продавцов eMAG; проверить доступ к API отзывов. Критерий: ≥10 в листе ожидания, 1 пилот | 40 | 0.05 | 40 × €15 = €600 ≈ **$680** | 3 |
| UN-07 | Да | 63.11/63.12 — проверить | Ежедневная выборка TED «WCAG» + лендинг EN; бесплатный еженедельный дайджест, платные мгновенные алерты 29 €. Посты в a11y-сообществах. Критерий: ≥40 подписчиков, ≥1 оплата | 35 | 0.05 | 12 × $49 = **$588** | 1.5 |
| UN-08 | Да; переписка RO с госорганами — владелец | 63.11 — проверить | 3 бесплатных публичных отчёта-примера (SEO-страницы). Критерий: 2 входящих запроса. Холодные письма госорганам не использовать | 90 | 0.02 | 15 × 3 000 MDL / 12 = 3 750 MDL ≈ **$211** | 3 |
| UN-09 | Да | 63.11 — IT | Бесплатный датасет + API с документацией. Критерий: ≥3 ключа от компаний | 90 | 0.01 | 2 × $49 ≈ **$100** | 1 |
| UN-10 | Да | 63.12? проверить | Еженедельная рассылка RO/RU. Критерий: ≥100 подписчиков | 60 | 0.02 | 20 × $15 = **$300** | 2 |

«Дней до 1-го $» учитывает выплату Creem 1-го/15-го числа и холд 7–12 дней ([база]); для банка — срок подписания договора [оценка].

---

## 4. Рейтинг

Балл = P × потолок / часы владельца в неделю [оценка; та же формула, что в `niches_b2b_services.md`, раздел 7].

| Место | ID | Балл | Почему |
|---|---|---|---|
| 1 | UN-07 | 0.05 × 588 / 1.5 ≈ **19.6** | Рост «WCAG» в TED ×1.8; дёшево в сборке; двойное использование — лента заказов для самой SRL и лидогенерация для услуг N1–N5 |
| 2 | UN-01 | 0.08 × 680 / 4 ≈ **13.6** | Единственный кандидат, где рынок уже платит за соседний продукт (мониторинг 70–162 лей/мес); RO — родной язык владельца. Минус: Licitatii.AI и sicap.ai выходят сейчас |
| 3 | UN-02 | 0.04 × 585 / 2 ≈ **11.7** | Большой поток денег (€50 млрд), чистый рельс USDC; минус — платящие инкумбенты и UA-язык |
| 4 | UN-06 | 0.05 × 680 / 3 ≈ **11.3** | 64 000 продавцов; минус — eMAG сам делает ИИ-ассистента; доступ к API отзывов не проверен |
| 5 | UN-04 | 0.03 × 265 / 1 ≈ **8.0** | Данные готовы и еженедельно обновляются; спроса нет данных |
| 6 | UN-03 | 0.05 × 281 / 2 ≈ **7.0** | Мал как продукт, но полезен как внутренняя лента заказов (ИТ-RFQ ПРООН в Молдове) |
| 7 | UN-05 | 0.02 × 350 / 1 ≈ **7.0** | Только как витрина для данных UN-02/UN-04 |
| 8 | UN-10 | 0.02 × 300 / 2 ≈ **3.0** | Аудитория с низкой платёжеспособностью |
| 9 | UN-08 | 0.02 × 211 / 3 ≈ **1.4** | Продажа государству — процедуры, пересечение с Notis |
| 10 | UN-09 | 0.01 × 100 / 1 ≈ **1.0** | Рынок MD-e-commerce мал (раздел 2.5) |

**Практический вывод [оценка].** Для сравнения: N7 (технический SEO на Upwork) — 140, SS-01 и EA-01 из других потоков тоже выше. Недооценённые «данные и тендеры» не заменяют нишу №1. Разумный ход — собрать UN-07 и UN-03 как **внутренние ленты** (флот, ~2–3 дня работы): они сразу дают Global Web SRL поток публичных заказов (WCAG-сайты в ЕС; веб/ГИС/хранилища данных у ПРООН в Молдове — это входящие RFQ, не холодные рассылки; выручка по 62.01 — IT). Подписку открывать, если лента наберёт ≥40 подписчиков. UN-01 — отдельная ставка на RO-рынок, если владелец готов ~4 ч/нед на RO-QA.

---

## 5. Ловушки и тупики (с доказательствами)

1. **AWS Data Exchange и Snowflake Marketplace для платных данных — тупик для Молдовы:** Молдовы нет в списках юрисдикций/стран; у Snowflake выплата только через Stripe Express [provider docs, 26.09.2026]. Регистрировать продавца на «чужую» юрисдикцию — ложное резидентство, исключено правилами проекта.
2. **Уведомления о тендерах MTender — занято:** Notis.md (Telegram-алерты, IDNO-мониторинг, «Tender Intelligence» скоро), achizitii.md (бесплатно), собственные уведомления MTender [vendor; база `telegram_2026.md`]. Проверка контрагентов в MD — тоже Notis (инсолвентность) и Infodebit (кредитное бюро).
3. **Простой мониторинг SEAP/SICAP — тесно:** licitatia.ro, SicapRadar, Termene.ro; Licitatii.AI выходит с ИИ-аналитикой [vendor]. Делать только узкую функцию (UN-01).
4. **Платные плагины оплаты/доставки для молдавских магазинов:** бесплатные и поддерживаемые плагины maib, Victoriabank, MIA, MPay; установки 10–200 [provider data]. Рынок слишком мал.
5. **Джоб-борды и каталоги с платным размещением через Creem:** «Job boards» и «Advertising… on websites» — restricted, нужна история платежей [provider docs]. Касается CA-04 и CA-10 из `content_affiliate_2026.md` — пересчитать рельс (Polar → банк или прямой инвойс).
6. **Продажа списков «новых компаний» (реестр ASP) и «новых перевозчиков» (FMCSA) для обзвона/рассылок:** это топливо для холодных контактов (исключено как основной канал), Creem прямо запрещает «telemarketing»; в файле ASP — ФИО руководителей и учредителей (персональные данные; закон РМ 133/2011 о защите персональных данных — к юристу). У FMCSA в 2026 новая система регистрации Motus (по сниппету, не прочитано) — источник данных может меняться.
7. **Синтетические датасеты, сгенерированные Claude, для обучения ИИ:** запрещено Commercial Terms D.4 («train competing AI models») и Usage Policy («Utilization of inputs and outputs to train an AI model… without prior authorization») [provider docs: Anthropic, 17.06.2025 и 15.09.2025]. «Продавать данные для ИИ» можно только собранные законно из открытых источников, без выходов модели как обучающего корпуса.
8. **Инструменты для 999.md через внутренний GraphQL сайта:** это скрейпинг вопреки правилам сайта (исключено). Официальный `partners-api.999.md` есть, условия — не опубликованы (401).
9. **Лицензия открытых данных MD не указана** («License Not Specified» на dataset.gov.md) — коммерческое переиспользование реестра надо подтвердить (к юристу; закон об открытых данных РМ не прочитан — legis.md за Cloudflare).
10. **eMAG как конкурент своим разработчикам:** Project Mira и ИИ-функции для продавцов объявлены 24.09.2025 [about.emag.ro]. Любой инструмент для eMAG может стать ненужным после обновления платформы.
11. **RapidAPI для «ниши API»:** выплаты только через PayPal/Payoneer — у владельца их нет [база]. Альтернатива — свой сайт + Creem или x402.
12. **ИИ-разбор тендерной документации как «юридическая консультация»:** продавать как «резюме и чек-лист со ссылками на пункты документации», без выводов о правомерности; иначе — исключение «юридические советы».

---

## 6. Что не удалось проверить

1. **Google-выдача** по трём запросам — недоступна; тест сделан по Bing (US). Не прочитаны 8 из 29 страниц (Forbes ×2, Inc, US News, Investopedia, College Investor, SideHustleNation /ideas, marksinsights, ideaproof).
2. Цены DevelopmentAid, devex, dgMarket, UNGM Pro, Termene.ro, fundsforNGOs Premium, SicapRadar — 403/Cloudflare или не опубликованы.
3. Объём процедур SICAP за 2025–2026 (data.gov.ro рвал соединение); число новых (а не обновлённых) тендеров MTender в неделю.
4. Содержимое sicap.ai (Vercel checkpoint) и точная дата запуска Licitatii.AI и Notis «Tender Intelligence».
5. Есть ли в API eMAG Marketplace эндпоинты отзывов и вопросов; условия для сторонних приложений; нужна ли песочница.
6. Лицензия датасета ASP для коммерческого использования; допустимость переиспользования ФИО руководителей/учредителей (закон 133/2011) — к юристу.
7. Условия `partners-api.999.md`.
8. Классификация CAEM для платных дайджестов тендеров и продажи данных (63.11 / 63.12 / 63.99?) — спросить MITP.
9. Разрешает ли Creem продажу подписки на собственные данные и API без статуса «API reseller» — спросить поддержку Creem до запуска.
10. Спрос на платный API реестра Молдовы и гео-данных — ни одного платящего конкурента и ни одного запроса не найдено.
11. Детали системы FMCSA Motus (fmcsa.dot.gov — 403).
12. Курс RON/EUR — допущение 5.0.

---

## 7. Источники (дата обращения — 26.09.2026, если не указано иное)

**Тест недооценённости (выдача Bing US, 26.09.2026)**
- Bing: «side hustles 2026», «passive income ideas 2026», «profitable online business ideas 2026» — https://www.bing.com/search?q=side+hustles+2026 и аналогичные [provider data]
- Whop, 105 online business ideas — https://whop.com/blog/online-business-ideas/ [vendor]
- 99businessideas — https://www.99businessideas.com/online-business-ideas/ ; Xero — https://www.xero.com/us/guides/online-business-ideas/ ; Startupill — https://startupill.com/profitable-online-business-ideas-2026/ ; Shopify — https://www.shopify.com/blog/online-business-ideas , https://www.shopify.com/blog/10580693-how-to-start-an-ecommerce-business-without-spending-any-money ; Omnisend — https://www.omnisend.com/blog/online-business-ideas/ ; Fundwell — https://www.fundwell.com/blog/most-profitable-businesses-to-start ; Marketingscoop — https://www.marketingscoop.com/ai/the-35-most-profitable-businesses-to-start-in-2026/ [vendor]
- DailyRemote (29.03.2026) — https://dailyremote.com/advice/best-remote-side-hustles-2026 ; Jobright (19.01.2026) — https://jobright.ai/blog/best-side-hustles-2026/ ; Penny Hoarder (11.09.2026) — https://www.thepennyhoarder.com/make-money/side-gigs/best-side-hustles/ ; InterviewGuys (19.05.2026) — https://blog.theinterviewguys.com/best-side-hustles-from-home/ ; Journeybee (20.07.2026) — https://journeybee.io/resources/best-high-paying-side-hustles [vendor/press]
- WellKeptWallet (05.09.2026) — https://wellkeptwallet.com/passive-income-ideas/ ; Ramsey (12.02.2026) — https://www.ramseysolutions.com/saving/passive-income-streams-to-build-in-2026 ; Yahoo/Penny Hoarder (18.09.2026) — https://finance.yahoo.com/small-business/articles/build-passive-income-2026-13-131749994.html , https://www.thepennyhoarder.com/make-money/side-gigs/beginners-guide-to-passive-income/ ; SHN (03.08.2026) — https://www.sidehustlenation.com/passive-income/ ; DollarSmartGuides (14.07.2026) — https://dollarsmartguides.com/blog/passive-income-ideas-in-2026/ [vendor]

**Маркетплейсы данных**
- AWS Marketplace, Getting started as a seller (eligible jurisdictions) — https://docs.aws.amazon.com/marketplace/latest/userguide/user-guide-for-sellers.html [provider docs]
- Snowflake, Requirements for offering paid listings — https://docs.snowflake.com/collaboration/provider-becoming [provider docs]
- Datarade Provider Studio, pricing & FAQ — https://providers.datarade.ai/apply [provider docs]

**Госзакупки**
- MTender public OCDS API — https://public.mtender.gov.md/tenders/ [official]
- achizitii.md, Modalitățile de plată și tarife — https://achizitii.md/info/payment [vendor]
- Notis.md — https://notis.md/ [vendor]
- openmoney.md — https://openmoney.md/ [vendor]
- licitatia.ro, Abonamente — https://www.licitatia.ro/abonamente.html [vendor]
- SicapRadar — https://licitatii-publice.ro/ [vendor]
- Licitatii.AI (цифры на 05.08.2026) — https://licitatii.ai/ [vendor]
- World Bank procurement notices API — https://search.worldbank.org/api/v2/procnotices?format=json&project_ctry_name=Moldova (и Ukraine) [official]
- UNDP Procurement Notices — https://procurement-notices.undp.org/search.cfm [official]
- Prozorro public API — https://public-api.prozorro.gov.ua/api/2.5/tenders [official]
- European Commission, Ukraine Facility — https://enlargement.ec.europa.eu/funding-technical-assistance/ukraine-facility_en [official]
- WTO, GPA parties and observers — https://www.wto.org/english/tratop_e/gproc_e/memobs_e.htm [official]
- TED API v3 notices search — https://api.ted.europa.eu/v3/notices/search [official]
- USAspending API, spending_by_award_count — https://api.usaspending.gov/api/v2/search/spending_by_award_count/ [official]
- UNGM Tender Alert Service — https://www.ungm.org/Public/Pages/TenderAlertService [official]
- Horizon Europe association — https://research-and-innovation.ec.europa.eu/strategy/strategy-research-and-innovation/europe-world/international-cooperation/association-horizon-europe_en [official]

**Открытые данные Молдовы**
- dataset.gov.md, Registrul de stat al unităților de drept (файл 21.09.2026) — https://dataset.gov.md/ro/dataset/11736-date-din-registrul-de-stat-al-unitatilor-de-drept-privind-intreprinderile-inregistrate-in-repu [official]
- srl.md — https://srl.md/ ; firme.md — https://firme.md/ [vendor]

**eMAG и e-commerce**
- eMAG, FY2024-2025 (04.06.2025) — https://about.emag.ro/2025/06/04/cu-o-crestere-de-12-a-cifrei-de-afaceri-in-anul-fiscal-2024-2025-grupul-emag-anunta-noi-investitii-de-peste-12-miliarde-de-lei-pentru-urmatorul-an/ [official-корп./press]
- eMAG, Sellers’ Day 2025 (24.09.2025) — https://about.emag.ro/2025/09/24/2106/ [official-корп./press]
- easySales, Prețuri — https://easy-sales.com/ro/pricing [vendor]
- GitHub: chawel/python-emag, JupiterSells/onsell_inventory_emag — https://github.com/chawel/python-emag , https://github.com/JupiterSells/onsell_inventory_emag [forum]
- WordPress.org Plugins API — https://api.wordpress.org/plugins/info/1.2/?action=query_plugins&request[search]=moldova [provider data]
- GitHub: alexminza/wc-moldovaagroindbank, alexminza/payment-gateway-wc-maib-mia, maib-ecomm/maib-payment-gateway-for-woocommerce, alexminza/wc-victoriabank — https://github.com/alexminza [provider data]

**Правила платформ**
- Creem, Account Reviews (prohibited/restricted) — https://docs.creem.io/merchant-of-record/account-reviews/account-reviews.md [provider docs]
- Anthropic, Commercial Terms of Service (effective 17.06.2025) — https://www.anthropic.com/legal/commercial-terms [provider docs]
- Anthropic, Usage Policy (effective 15.09.2025) — https://www.anthropic.com/legal/aup [provider docs]
- 999.md partners API (401) — https://partners-api.999.md/ ; пример скрейпинга GraphQL — https://github.com/fxmidaaa/pret-drept [forum]
- FMCSA Registration (403; сниппет Bing про Motus) — https://www.fmcsa.dot.gov/registration [official, не прочитано]

**База проекта:** `STATUS.md` (2.1–2.6), `notes/niches_software.md` (N7, N8 — Apify-actors MTender/TED/SEAP), `notes/niches_b2b_services.md` (N1–N7, формула балла), `notes/it_park_verified.md` (коды 63.11/63.12/62.01), `notes/decision_niche_1.md`, `notes/crypto_rails_2026.md` (Creem, x402, закон 62/2008), `notes/content_affiliate_2026.md` (CA-04, CA-10, CA-13), `notes/telegram_2026.md` (Notis), `notes/existing_assets_2026.md`.

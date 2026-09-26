# Софт на маркетплейсах: самые быстрые пути к первой выручке за 30 дней

Дата: 26.09.2026. Только исследование: аккаунты не создавались, формы не отправлялись.
Для кого: Global Web SRL (резидент IT Park) и флот ИИ-агентов. Выплаты должны приходить на OTP Bank Moldova (SWIFT/SEPA).

**Допущения по умолчанию** (вопросов не задавали, работали по умолчаниям):
1. Получатель — Global Web SRL. Доход от продажи или лицензирования своего софта, скорее всего, идёт в 70% IT-выручки. Шаблоны Notion и Telegram Stars под вопросом. Всё это — **для бухгалтера**.
2. Время владельца — ≤10 ч в первые 30 дней на весь портфель. Остальное делают агенты.
3. Paddle, Lemon Squeezy, RapidAPI, Etsy, Microsoft Store, Figma, KDP, Kwork не рассматриваются: это уже установлено в `STATUS.md`.
4. Метки: [official] — закон или госисточник; [provider docs] — справка или документация провайдера; [provider data] — выгрузка из API провайдера; [press]; [vendor] — блог продавца или конкурента; [forum] — анекдот.

---

## 0. Главное

- **Apify Store — единственный канал, где сошлись три условия:** встроенный спрос, выплата юрлицу в Молдову по SWIFT и сборка силами агентов за дни.
  - Рынок сильно перекошен. Лидеры набирают десятки тысяч пользователей в месяц. Типичный нишевый actor — 1–30 пользователей за 30 дней (раздел 2.1).
  - Отсюда стратегия: не один хит, а портфель из 10–20 нишевых actors на **открытых данных и официальных API**.
- **Chrome-расширения, WordPress-плагины, Wix и Shopify** дают больший потолок. Но за 30 дней первый доллар маловероятен: мешают ревью, нулевой органический трафик и неподтверждённые выплаты (Shopify, Wix).
- **Notion Marketplace** — самый быстрый не-IT-канал: Молдова в списке Stripe, комиссия 8% + $0.40. Но это шаблоны, не софт — риск для правила 70% IT Park.
- **Telegram Stars.** Спрос есть, выплата идёт через Fragment в TON. Дальше мешает лимит 50 000 лей в месяц на крипту→банк (`STATUS.md` 2.5). Годится только как дополнительный канал.
- **Без прямой выплаты:** GPT Store (программы выплат вне США нет), каталоги Claude/MCP, Zapier, HubSpot, n8n-библиотека. Это только воронки к своему продукту на MoR.

---

## 1. Каналы: выплата, спрос, конкуренция, усилия, срок, потолок

### 1.1 Сводная таблица A — выплаты и экономика

| ID | Канал | Выплата в Молдову (проверено) | Комиссия платформы | Минимум / график |
|---|---|---|---|---|
| C1 | Apify Store (actors, pay-per-event) | Да: SWIFT ≥$100 или PayPal ≥$20, нужен KYC [provider docs, обновлено 20.07.2026]; юрлицо — база `STATUS.md` | 20% + стоимость вычислений платформы вычитается из выплаты [provider docs, 22.10.2025] | Ежемесячно, выплата 21–25-го числа [provider docs] |
| C2 | Chrome Web Store + MoR Creem | Creem: «Moldova ✓» без ограничений [provider docs, дата не указана] | 3.9% + $0.40 [provider docs]; выплата — 7 EUR/USD или 1%, что больше (docs). На странице цен — «0% payout for several methods». **Расхождение**: считаем по docs, это консервативнее | Дважды в месяц |
| C2' | … + MoR Polar | Молдова в списке стран выплат (Stripe Connect Express) [provider docs] | 5% + $0.50, +1.5% за международные карты; выплата $2/мес + 0.25% + $0.25, конвертация 0.25–1% [provider docs; тарифы для организаций, созданных после 27.05.2026] | — |
| C2'' | … + MoR Dodo Payments | Молдова в списке «Countries Eligible for Merchant Acceptance», № 103 [provider docs; политика — для решений с 23.03.2026] | нет данных (не проверяли) | — |
| C3 | WordPress-плагин + Freemius | Молдова в «Supported Countries» (там страны, где доступен хотя бы один метод). Методы: PayPal, Payoneer, wire IBAN/SWIFT, Wise. **Какой метод доступен именно Молдове, не указано** → проверить [provider docs] | 4.7% + шлюз; для WordPress ещё +2.3% [provider docs] | Минимум $100 [provider docs] |
| C4 | Wix App Market | Выплаты через Tipalti. Список стран Wix не публикует. Ограничения известны только для банков РФ и Пакистана [press/поиск]. Страница Tipalti с покрытием стран не открылась (403) → **проверить** | 0% в первые 12 месяцев, затем 20%. База — после 2.5% transaction fee и налога [provider docs] | Минимум $200, net-30 EOM [provider docs] |
| C5 | Shopify App Store | Методы: PayPal, банковский счёт, wire (через Hyperwallet), «зависит от страны» [provider docs]. Молдова не упомянута → **проверить в Partner Dashboard**. В директории партнёров есть раздел «Moldova» — это не доказательство выплат | 0% на первый $1 млн за всё время (с 01.01.2025), затем 15%; регистрация $19 [provider docs / BetaKit] | Минимум $25 [provider docs] |
| C6 | Telegram-бот или мини-апп (Stars) | Stars → Fragment → TON → биржа → банк. Крипта→OTP — лимит 50 000 лей в месяц (`STATUS.md`) | Telegram не берёт долю. Звёзды, купленные в iOS/Android, дают ~$0.009 против $0.013 [vendor/dev.to 2026] | Холд 21 день (`STATUS.md`); минимум 1 000 Stars [vendor] |
| C7 | Google Play (SRL = организация) | Да, USD переводом, минимум $100 (база) | Стандартная комиссия Play (здесь не проверяли) | Организации освобождены от «12 тестеров × 14 дней» [provider docs]. Но нужен D-U-N-S, до 30 дней [provider PDF 10.2024 + вторичные источники] |
| C8 | Notion Marketplace | Молдова в списке стран Stripe для продавцов [provider docs] | 8% + $0.40 [provider docs]. Вторичные источники пишут «10%» — **доверяем справке Notion** | Минимум $20 [provider docs] |
| C9 | Gumroad (шаблоны, n8n-воркфлоу, мини-софт) | Да, в MDL через Stripe, минимум $100 (база) | Здесь не перепроверяли | — |
| C10 | n8n / Make / Zapier / HubSpot | Своих выплат нет. Библиотека n8n бесплатна; партнёрка n8n — 30% за первый год (выплата не проверялась). У Make официального маркетплейса платных шаблонов нет [forum]. HubSpot не берёт долю, биллинг ваш [vendor] | — | Годится только как воронка |
| C11 | GPT Store / каталоги Claude и MCP | Официального подтверждения выплат вне США нет. Тред OpenAI от 13.09.2025 без ответа сотрудников [forum]. Сайт gptstorerevenueprogram.com — не OpenAI, не доверяем | — | Тупик для выплат |
| C12 | Atlassian Marketplace | EFT на банковский счёт, минимум $500. Официального списка стран нет (тред от 09.08.2026 без ответа) → **проверить** [provider docs / forum] | Forge: 100% до $1 млн за всё время (с 01.01.2026) [provider blog] | Долгий цикл, для 30 дней не подходит |

### 1.2 Сводная таблица B — спрос, конкуренция, срок, потолок

| ID | Доказательства спроса (2025–2026) | Конкуренция | Сборка агентами | Время до первого $ | Потолок на 6-й месяц [оценка] |
|---|---|---|---|---|---|
| C1 | Выплаты разработчикам: $1.6 млн в месяц, 4 500 разработчиков, 74 867 actors, 10 000+ регистраций в день [provider, страница partners, 26.09.2026]. Ранее: $1 млн за месяц против $222K годом раньше [provider X, 13.05.2026]; $1.4 млн [provider blog 14.04.2026]. Топ-авторы — >$10k MRR, «многие» — >$1k [provider docs] | Очень высокая в общих категориях: Google Maps Scraper — 37 946 пользователей за 30 дней. Нишевые actors — 1–30 (скан 2.1). Совет автора 98 actors: избегать LinkedIn, Amazon, Instagram, идти в региональные вертикали [provider blog 22.07.2026] | Да. Node или Python + Crawlee, PPE-события, README. 1–2 дня агента на actor | 30–45 дней: выплата 21–25-го числа следующего месяца, нужен KYC | Портфель 15 actors × 8 MAU × $5 × 0.8 × 0.8 (вычисления) ≈ **$380/мес**. Средняя трата на пользователя не публикуется, $5 — допущение. Диапазон $100–1 000 |
| C2 | Chrome Web Store: 178 299 расширений, медиана 18 пользователей, 70.4% — ≤100, 2.63% — >10k [vendor Exstats, 03.2026] | Длинный хвост; органический рост слабый | Да (MV3 + лицензии MoR) | 30–60+ дней | 2 000 пользователей × 1% конверсии × $5 = **$100 MRR**. Конверсия 0.5–2.2% [vendor/dev.to 2026] |
| C3 | Опрос 33 плагинных компаний: у 80% продажи на уровне прошлого года или ниже; новые продажи Barn2 −17.8% за 2025 [press WP Product Talk, 30.12.2025]. Подачи плагинов выросли в 4 раза к 2024 [official make.wordpress.org, 06.2026] | Растёт (ИИ-плагины) | Да | 45–90 дней (ревью, затем набор установок) | $50–300 [оценка]; данных по новичкам нет |
| C4 | Обещанная аудитория Wix — 200+ млн пользователей [vendor/dev.to]. Данных о продажах новых приложений нет | нет данных | Да (Wix CLI) | >30 дней (ревью + Tipalti) | нет данных |
| C5 | Экономика App Store открыта, данных о спросе на новые приложения не нашли | Высокая [не проверено] | Да | >30 дней | нет данных |
| C6 | Telegram >1 млрд MAU; Web3-мини-аппы >100 млн MAU [press, 2026, методика спорная] | нет данных | Да | 21+ день из-за холда | 500 платящих × 100 Stars × $0.012 ≈ **$600** [оценка, оптимистично] |
| C7 | нет данных по утилитам | Высокая [не проверено] | Частично (APK — да, ASO — да) | >30 дней (D-U-N-S) | нет данных |
| C8 | Заявления о $100–500 в первый месяц и больших суммах (Thomas Frank, Easlo) — только маркетинговые блоги [vendor], не доказательство | нет данных | Да | 7–21 день после одобрения | 20 продаж × $15 × 0.92 − $8 ≈ **$270** |
| C9 | Встроенный спрос слабый (Discover) | — | Да | — | нет данных |

**Вывод по каналам.** Для «первого $ за 30 дней на встроенном спросе» проходит только **C1 (Apify)**. Во вторую очередь — **C8 (Notion)**, потом **C6 (Telegram)**. Остальные каналы строятся на горизонт 60–120 дней.

---

## 2. Apify Store подробно

### 2.1 Экономика и правила
- **Модели оплаты.**
  - Rental (аренда): новые запрещены с 01.04.2026; с **01.10.2026** модель полностью закрыта, оставшиеся actors переводят на pay-per-usage без дохода разработчику [provider docs].
  - Остаются **pay-per-event (PPE)** и pay-per-usage [provider docs].
  - 73% клиентов предпочли PPE [provider blog, 14.04.2026].
- **Доход разработчика** = 0.8 × выручка − вычисления платформы [provider docs 22.10.2025; формула повторена в стороннем гайде use-apify.com].
- **Агентный спрос.**
  - MCP-сервер Apify отдаёт агентам только free- и PPE-actors. Под этот фильтр попадают ~29 000 actors [provider blog, 07.2026].
  - x402 и Skyfire: агенты платят без аккаунта Apify [provider blog].
  - Это новый встроенный канал спроса, которого нет у Chrome или WordPress.
- **Челлендж.** Apify $1M Challenge ($2 за MAU) закончился 31.01.2026 — **для нас недоступен**.
- **Средний доход.** $1.6 млн / 4 500 = ~$355 на разработчика в месяц. Это арифметика, не медиана: распределение сильно перекошено.

### 2.2 Скан конкуренции (Apify Store API `api.apify.com/v2/store`, 26.09.2026) [provider data]

u30 — пользователи за 30 дней. Поиск в Store нечёткий, поэтому в выдаче много нерелевантных actors — их не учитывали.

| Тема | Релевантные лидеры (u30 / всего) | Вывод |
|---|---|---|
| Google Maps | compass 37 946 / 619 022 | Не входить |
| Отзывы Trustpilot | memo23 670; automation-lab 488 | Тесно |
| Отзывы Google Play | neatrat 300; thewolves 200 ($0.10 за 1 тыс.) | Ценовая война |
| SEO-аудит сайта | smart-digital 85 ($0.04/стр.); autofacts schema 25; broken links 19 | Спрос средний, лидеры слабые |
| PageSpeed / Lighthouse | dev00 42; бесплатный 35; perryay 12 | Средний |
| WCAG / EAA accessibility | katzino (бесплатный) 2 / 84; axe tester 1 / 16 | **Спрос почти нулевой** |
| llms.txt / GEO-аудит | 3–7 | Спрос низкий, рынок ранний |
| AI Overviews / Perplexity / Gemini | Apify (официальные) 167 / 126 / 59 | Платформа конкурирует сама |
| Лицензии подрядчиков США | AZ 11, CA 9, OH 9, FL 6, TX 5 | Спрос есть, штатов много не покрыто |
| Разрешения на строительство (США) | 12, 6, 5, 4 | Низкий–средний |
| Тендеры | TED 11 и 4; SAM.gov 12; GeBIZ 15; SEAP RO ≤2; **MTender (MD) — 0 actors** | Низкий |
| Джоб-борды | Naukri 739; StepStone 402; ejobs.ro 14; hh.ru 37 | Вертикали работают, но memo23 и blackfalcondata заняли многие |
| Недвижимость ЕС | ImmoScout24 181; Idealista 166; Immobiliare.it 104 | Средний, занято |
| RO/MD e-commerce | eMAG 13; OLX (PL/RO) 32; Rozetka 4 | Низкий |
| Каталоги приложений | Shopify App Store 21/17; WordPress.org 1 | Низкий |

**Вывод.** У нишевого actor реалистично 5–30 MAU. Деньги — в объёме портфеля и в вертикалях, где лидеры слабые: SEO-утилиты, лицензии и разрешения в США. ToS: брать только публичные страницы без логина, лучше — официальные API и открытые данные.

---

## 3. ≥15 конкретных ниш (канал × инструмент × покупатель)

Во всех нишах — только публичные данные или официальные API, без логина. ToS каждого сайта агенты проверяют до сборки («проверить» в колонке). Выплата: Apify → SWIFT → OTP; MoR → банк.

| # | Канал | Инструмент | Покупатель | Спрос / конкуренция (скан 26.09.2026) | ToS / данные | Первый $ за 30 дней | Потолок на 6-й месяц [оценка: MAU × $/MAU × 0.64] |
|---|---|---|---|---|---|---|---|
| N1 | Apify | Проверка лицензий подрядчиков по штатам, которые ещё не покрыты (NC, GA, VA, WA, OR, MN, NV и др.), единый формат вывода, PPE $0.003–0.005 за запись | Лидген-платформы для home services, страховщики, маркетплейсы подрядчиков (плюс синергия с pickaroofer.com) | Аналоги: AZ 11, CA 9, OH 9, FL 6, TX 5 u30 | Госпорталы, публичный поиск. ToS каждого штата — проверить | Средняя | 8 штатов × 5 MAU × $5 × 0.64 ≈ $130 |
| N2 | Apify | Агрегатор разрешений на строительство и кровлю из городских open-data API (Socrata, ArcGIS) | Кровельщики, солнечная энергетика, лидген | 12 / 6 / 5 / 4 u30 | Открытые данные — ОК | Средняя | 20 × $8 × 0.64 ≈ $100 |
| N3 | Apify | Массовый технический SEO-аудит: canonical, hreflang, schema, noindex, цепочки редиректов; PPE $0.01–0.03 за страницу | SEO-агентства, фрилансеры | Лидер 85 u30 по $0.04 | Сканирует сайт, который указал заказчик; соблюдать robots | Средняя–высокая | 30 × $6 × 0.64 ≈ $115 |
| N4 | Apify | Массовый сбор Core Web Vitals через **официальный CrUX API** (полевые данные), история по origin | SEO-агентства, eCommerce | Lighthouse-аналоги 8–42 u30; на CrUX API конкурентов почти нет | Официальный API — ОК | Средняя | 20 × $4 × 0.64 ≈ $50 |
| N5 | Apify | Аудит готовности к ИИ-краулерам: robots.txt по GPTBot, ClaudeBot и др., llms.txt, рендеринг без JS | SEO- и GEO-агентства | 3–7 u30, рынок ранний | ОК | Низкая–средняя | 10 × $5 × 0.64 ≈ $30 |
| N6 | Apify | Массовый аудит WCAG 2.2 / EAA (axe-core + отчёт на человеческом языке, EN/RO/RU) | Агентства ЕС. EAA действует с 28.06.2025 (Директива (ЕС) 2019/882) [official] | **Спрос в Store почти нулевой** (1–2 u30) | ОК | Низкая | $20–60. Ценность скорее как лид-магнит для аудиторских услуг |
| N7 | Apify | Лента тендеров **MTender (Молдова, открытый OCDS API)** + фильтр CPV + дайджест | Поставщики в MD, RO, UA, консультанты | 0 конкурентов; спрос — нет данных | Открытые данные OCDS — ОК (проверить условия) | Низкая | нет данных; $0–50 |
| N8 | Apify | Тендеры EU TED (официальный API) с алертами по CPV и стране + RO SEAP | Малые поставщики ЕС | TED 11 и 4, SEAP ≤2 u30 | TED API — ОК; SEAP — проверить ToS | Низкая–средняя | 15 × $6 × 0.64 ≈ $60 |
| N9 | Apify | Слежение за каталогом WordPress.org (официальный API): рейтинги, версии, новые плагины по ключу | Плагинные компании, инвесторы | 1 u30, тонкий рынок | Официальный API — ОК | Низкая | $10–30 |
| N10 | Apify | Мониторинг Shopify App Store и Wix App Market: категории, отзывы, изменения цен | SaaS-основатели, агентства | 21 / 17 u30 | Публичные страницы; ToS — проверить | Средняя | 15 × $5 × 0.64 ≈ $50 |
| N11 | Apify | Джоб-борды RO/MD без логина (ejobs.ro уже есть: 14 u30; rabota.md, delucru.md) | Рекрутёры RO/MD, HR-аналитика | ejobs 14 u30 | ToS и robots — **проверить**; для 999.md не рекомендуется без проверки | Низкая | $20–60 |
| N12 | Chrome + Creem | Инспектор accessibility + SEO на странице (контраст, alt, заголовки, ARIA, hreflang), бесплатно + Pro $5 в месяц | Аудиторы, QA, SEO-специалисты | Медиана расширений — 18 пользователей; конкуренты — не проверено | — | Очень низкая | $50–100 MRR |
| N13 | WordPress + Freemius | Генератор заявления о доступности по EAA + сканер (free + pro) | Владельцы сайтов в ЕС | нет данных; рынок плагинов стагнирует | — | Очень низкая | $50–300 |
| N14 | Wix App Market | Сканер и мониторинг доступности для Wix-сайтов | Малый бизнес ЕС на Wix | нет данных | — | Очень низкая (ревью + Tipalti) | нет данных |
| N15 | Notion Marketplace | Трекер технических SEO-аудитов и клиент-ops для агентства (EN) | Фрилансеры и агентства | нет данных | — | Низкая–средняя | 10 × $19 × 0.92 ≈ $170 |
| N16 | Notion Marketplace | RO-шаблоны для фрилансера или микробизнеса (CRM, проекты, счета — без налоговых советов) | RO/MD-фрилансеры | нет данных | — | Низкая | $30–100 |
| N17 | Telegram-бот (Stars) | Бот «проверь сайт»: SEO-, скорость- и a11y-отчёт на RU/RO за 50–100 Stars | Владельцы малых сайтов RU/RO | нет данных | — | Низкая | 100 × 75 × $0.012 ≈ $90 |
| N18 | Gumroad | Пакет n8n-воркфлоу для SEO-агентств (отчёты по GSC, алерты об индексации) | Агентства | Бесплатная библиотека n8n — 12 571 воркфлоу | Официальные API | Низкая | $30–150 |

---

## 4. Топ-5

Ранжирование: **балл = P(первый $ ≤30 дней) × потолок (середина диапазона) / часы владельца за первые 30 дней**. Все три множителя — [оценка].

| Ранг | Что | P | Потолок | Часы владельца | Балл | Почему |
|---|---|---|---|---|---|---|
| 1 | **Apify «SEO-утилиты» (N3 + N4 + N5)** | 0.45 | $195 | 3 (при общем сетапе Apify с п. 2; нужна SEO-экспертиза для README) | 29 | Экспертиза 15+ лет SEO; у лидера категории всего 85 u30 |
| 2 | **Портфель Apify «US contractor / permits» (N1 + N2)** | 0.5 | $230 | 5 (KYC Apify, SWIFT-реквизиты SRL, ревью README) | 23 | Подтверждённая выплата юрлицу, встроенный и агентный (MCP) спрос, слабые лидеры, опыт в кровельном лидгене |
| 3 | **Notion Marketplace (N15)** | 0.2 | $170 | 4 (подключение Stripe через Notion, выкладка) | 8.5 | Быстро и дёшево; минус — не IT-выручка, возможен конфликт с правилом 70% (проверить у бухгалтера) |
| 4 | **Apify «тендеры» (N7 + N8)** | 0.25 | $60 | 2 | 7.5 | MTender — пустая ниша, но спрос не доказан |
| 5 | **Chrome + Creem (N12)** | 0.1 | $75 | 6 (аккаунт Creem для SRL, регистрация в CWS) | 1.3 | Чистая выплата, долгосрочный актив; за 30 дней маловероятно |

**Примечания:**
- Места 1, 2 и 4 — **один запуск на Apify**: часы на KYC и реквизиты засчитаны в п. 2, в п. 1 и 4 — только дополнительные.
- Telegram (N17): балл ≈ 0.2 × 90 / 4 ≈ 4.5, с понижающим коэффициентом 0.5 за крипто-рельс ≈ 2.3. Поэтому вне топ-5.
- Действие на 30 дней: агенты собирают 12–15 PPE-actors из N1–N5 и N7–N8. Владелец проходит KYC Apify и указывает SWIFT-реквизиты SRL в OTP. Первая выплата за октябрь придёт около 21–25.11.2026 — при условии, что набрано ≥$100 (иначе переносится). **Первые деньги, скорее всего, придут не в первые 30 дней, а на 50–60-й день.**
  - Первое начисление (продажа) в течение 30 дней — реалистично.
  - Самый быстрый реальный кэш — PayPal ≥$20, но PayPal у владельца нет.

---

## 5. Ловушки и тупики (с доказательствами)

- **Rental на Apify.** Пишут старые гайды, но с 01.10.2026 модель закрыта [provider docs].
- **LinkedIn, Facebook и Instagram скраперы.** Самые популярные в Store (например, LinkedIn Profile Scraper — 10 487 u30), но это данные за логином и против ToS платформ → исключены правилами проекта.
- **Apify $1M Challenge.** Завершён 31.01.2026. Советы «публикуй ради $2 за MAU» устарели.
- **ExtensionPay.** Популярный способ монетизации Chrome-расширений работает только через Stripe, а Stripe для Молдовы недоступен. Использовать MoR: Creem, Polar или Dodo.
- **GPT Store.** Сайты про «GPT Store Revenue Program 2026» не принадлежат OpenAI. Официальных выплат вне США не найдено [forum 13.09.2025].
- **Notion: «10%».** Вторичные блоги пишут 10%, справка Notion — 8% + $0.40. Доверяем справке.
- **Google Play.** Личный аккаунт — 12 тестеров × 14 дней, для организации это не требуется [provider docs]. Зато D-U-N-S может занять до 30 дней.
- **WordPress.** Подачи плагинов выросли в 4 раза. Очередь на ревью доходила до ~1 050 плагинов (апрель 2026) и потом была разобрана [official make.wordpress.org].

---

## 6. Что не удалось проверить

1. **Freemius.** Какой метод выплаты доступен Молдове: IBAN/SWIFT wire или только PayPal/Payoneer. На странице стран разбивки нет.
2. **Shopify Partner.** Выплаты в Молдову (Hyperwallet или банк): страница без списка стран, проверить в Partner Dashboard.
3. **Wix и Tipalti.** Покрытие Молдовы: help.tipalti.com ответил 403.
4. **Atlassian Marketplace.** Список стран не опубликован.
5. **Creem.** Фактическая комиссия за выплату в Молдову: в docs — 7 EUR/USD или 1%, на странице цен — «0%». Дата страницы стран не указана.
6. **Dodo Payments.** Комиссии не проверены.
7. **Apify.** Средняя трата на пользователя или actor не публикуется, поэтому все потолки — допущения. Какой метод KYC Apify примет для молдавского юрлица — проверить при регистрации.
8. **ToS конкретных сайтов** для N1, N2, N8, N10, N11: портал каждого штата, SEAP, rabota.md и др. — агенты проверяют до сборки.
9. **Спрос на Wix, Shopify, Google Play, Gumroad Discover.** Цифр за 2025–2026 для новичков не найдено.
10. **Налоги.** Входят ли выручка Notion-шаблонов и Telegram Stars в 70% IT-выручки IT Park — **для бухгалтера**.
11. **Стоимость регистрации в Chrome Web Store** (по памяти $5) не проверена в этой сессии.

---

## Источники (дата обращения — 26.09.2026)

**Apify**
- Apify, How developer payouts work (обновлено 20.07.2026) — https://help.apify.com/en/articles/10057167-how-developer-payouts-work
- Apify, Make money publishing your Actors (обновлено 22.10.2025) — https://help.apify.com/en/articles/8684010-make-money-publishing-your-actors-on-apify-store
- Apify docs, Rental pricing model — https://docs.apify.com/actors/publishing/monetize/rental
- Apify docs, Monetize — https://docs.apify.com/platform/actors/publishing/monetize
- Apify, Actor developers page ($1.6M/мес, 4 500 разработчиков, 74 867 actors) — https://apify.com/partners/actor-developers
- Apify blog, Why Apify is standardizing Actor pricing (14.04.2026) — https://blog.apify.com/standardizing-actor-pricing/
- Apify blog, How I built 98 production Actors (22.07.2026) — https://blog.apify.com/building-98-actors-on-apify-store/
- Apify on X, $1M paid to creators in a month (13.05.2026) — https://x.com/apify/status/2054547299485745273
- Apify blog, x402 agentic payments — https://blog.apify.com/introducing-x402-agentic-payments/
- Apify blog, What Apify MCP does to your Actor (07.2026) — https://blog.apify.com/fixing-actors-invisible-to-agents/
- Apify $1M Challenge — https://apify.com/challenge
- Apify Store API, скан 26.09.2026 — https://api.apify.com/v2/store?search=…
- AgentByline, Apify passive income 2026 [vendor] — https://agentbyline.com/articles/apify-actor-passive-income-what-really-earns-in-2026-67lcfr

**MoR-платформы**
- Creem, Supported Countries — https://docs.creem.io/merchant-of-record/supported-countries
- Creem, Pricing — https://www.creem.io/pricing
- Polar, Supported countries — https://polar.sh/docs/merchant-of-record/supported-countries
- Polar, Pricing — https://polar.sh/resources/pricing
- Dodo Payments, Accepted countries — https://docs.dodopayments.com/miscellaneous/accepted-countries-and-territories
- Freemius, Supported Countries — https://freemius.com/help/documentation/selling-with-freemius/supported-countries/
- Freemius, Earnings — https://freemius.com/help/documentation/selling-with-freemius/your-earnings/
- Freemius, Pricing — https://freemius.com/wordpress/pricing/

**Маркетплейсы приложений и шаблонов**
- Wix, Payments and Billing FAQs — https://dev.wix.com/docs/build-apps/launch-your-app/pricing-and-billing/payments-and-billing-faqs
- Wix, Set up your payout account — https://dev.wix.com/docs/build-apps/launch-your-app/pricing-and-billing/set-up-your-payout-account
- Shopify, Payout method — https://help.shopify.com/en/partners/manage-account/manage-payouts-invoices/payout-method
- Shopify, Revenue share — https://shopify.dev/docs/apps/launch/distribution/revenue-share
- BetaKit о пересмотре revshare Shopify — https://betakit.com/shopify-app-developers-will-no-longer-be-exempt-from-sharing-their-first-1-million-usd-in-revenue-every-year/
- Notion, Sell templates on Marketplace — https://www.notion.com/help/selling-on-marketplace
- Atlassian, Marketplace revenue share 2026 — https://www.atlassian.com/blog/development/updates-to-marketplace-revenue-share-2026
- Atlassian dev community, supported countries (09.08.2026) — https://community.developer.atlassian.com/t/supported-countries-for-marketplace-partner-registration-and-payouts-where-is-this-documented/102084
- OpenAI community, GPT Store builders outside the US (13.09.2025) — https://community.openai.com/t/guidance-for-gpt-store-builders-outside-the-us/1357911

**Google Play**
- Google Play, App testing requirements for new personal accounts — https://support.google.com/googleplay/android-developer/answer/14151465
- Google Play, Verifying org accounts (PDF, 10.2024) — https://play.google.com/console/about/static/pdf/Verifying_your_Play_Console_developer_account_for_organizations.pdf

**Chrome-расширения**
- Chrome extension statistics 2026 (Exstats, 03.2026) [vendor] — https://konabayev.com/blog/chrome-extension-statistics-2026/
- DEV, Freemium Chrome extension real numbers (2026) [vendor/forum] — https://dev.to/ktg0215/real-numbers-freemium-chrome-extension-monetization-after-6-months-5hga
- ExtensionPay (только Stripe) — https://extensionpay.com/

**WordPress**
- WP Product Talk, plugin sales survey (30.12.2025) — https://wpproducttalk.com/blog/wordpress-plugin-sales-survey-2025/
- Make WordPress Plugins, update June 2026 — https://make.wordpress.org/plugins/2026/06/13/update-on-the-status-of-the-team-june-2026/

**Telegram**
- DEV, Telegram Stars economics 2026 [vendor] — https://dev.to/starsearn/telegram-stars-economics-for-bot-developers-what-your-stars-are-actually-worth-in-2026-2742
- Telegram core, Stars API — https://core.telegram.org/api/stars

**n8n**
- n8n affiliates — https://n8n.io/affiliates/
- n8n workflows (12 571) — https://n8n.io/workflows/

# B2B-услуги, которые выполняют ИИ-агенты: первые деньги за 30 дней

Дата: 26.09.2026. Поток исследования B2B (промпт v2 из чата «B2B AI services» не найден, работа по брифу вызывающего агента).
Это исследование, а не юридическая или налоговая консультация. Пункты «спросить бухгалтера / MITP» — для бухгалтера и аудитора IT Park.
Метки: [official], [provider docs], [press], [vendor], [forum], [интерпретация], [оценка]. Цифры без источника не приводятся — «нет данных».

## Допущения по умолчанию (вопросов пользователю не задавалось)

1. Получатель всех B2B-денег — Global Web SRL (резидент IT Park, плательщик НДС). Не-IT доход держится в пределах 30% оборота (база: `notes/it_park_verified.md`).
2. Каналы — только входящие: Upwork (Direct to Local Bank работает для Молдовы, $0.99 за вывод — база `STATUS.md` 2.3), собственные SEO-лендинги, партнёрство с агентствами по их входящим запросам, сообщества. Холодные рассылки не используются.
3. Язык отчётов для клиентов — EN (пишут агенты, владелец проверяет частично), RO/RU (владелец проверяет полностью). DE — только как перевод без полной проверки.
4. Курс: 1 EUR = 20.2078 MDL, 1 USD = 17.7706 MDL (НБМ 25.09.2026, база проекта) → 1 EUR ≈ 1.137 USD. RON→EUR: **допущение 1 EUR ≈ 5 RON, курс в этой сессии не проверялся**.
5. Часы владельца — это только проверка, переписка и подписание. Работу делают агенты.

## Уже проверено в проекте (не перепроверялось, используется как база)

- Upwork: вывод Direct to Local Bank, Молдова в списке, $0.99, минимум $5. Fiverr, Freelancer.com — только PayPal/Payoneer. Payoneer — «работает, подтвердить при регистрации». PayPal Молдова — приём коммерческих платежей «зависит от аккаунта». Wise и Revolut для резидентов Молдовы недоступны. Stripe напрямую — нет (`STATUS.md` 2.1, 2.3, 2.4).
- OTP Bank Moldova: входящие SWIFT/SEPA для компаний бесплатны, банк запрашивает договоры и счета; OTP в SEPA с 06.10.2025.
- Экспорт услуг нерезиденту по ст. 111(1)(e) НК — НДС 0% с правом на вычет (`notes/srl_it_park.md`, TL;DR 4; перечень — проверить).
- IT Park: разрешены 62.01, 62.02, 62.03, 62.09, 63.11, 63.12, 58.29; SEO, контент, переводы (73.11 / 74.30) и продажа лидов — не IT или неясно (`notes/it_park_verified.md`).

---

## 1. European Accessibility Act (EAA): аудит и исправление по WCAG / EN 301 549

### 1.1 Что установлено

**Правовая база.**
- EAA (директива 2019/882) применяется с 28.06.2025 [official].
- Микропредприятия, которые оказывают **услуги** (менее 10 работников и оборот или баланс не больше €2 млн), освобождены. Это прописано в румынском законе 232/2022 [press: juridice.ro, 08.07.2025] и в нидерландской практике: ACM указывает порог «10+ работников и/или оборот > €2 млн» [official: ACM, 24.03.2026].
- Вывод [интерпретация]: платёжеспособный спрос — у e-commerce и потребительских онлайн-сервисов с 10+ работниками. Чисто B2B SaaS под EAA, как правило, не попадает: директива про потребительские продукты и услуги. Проверить по тексту директивы для каждого клиента.

**Правоприменение по странам (2025–2026):**

| Страна | Что происходит | Источник, уровень |
|---|---|---|
| Германия (BFSG) | Надзор — MLBF (Магдебург), единый орган 16 земель. Работает с 26.09.2025, активно — с января 2026; около 70 сотрудников. Приоритет — жалобы, плюс выборочные проверки, «часто» автоматическими инструментами. Стратегия надзора принята 29.01.2026. Число дел и штрафов не опубликовано. | [official: пресс-служба Саксонии-Анхальт, 01.06.2026]; [press: marcus-herrmann.com, 01.06.2026]; [vendor: xictron.de, 7aufeinenstreich.com] |
| Германия, частные иски | Abmahnungen (досудебные претензии) от конкурентов и объединений. Сообщают о суммах 3 500–20 000 € за претензию и о типовом счёте 1 784,10 € + 490 € за анализ. | [vendor: xictron.de; checkbarriere/сводки поиска] — по одной-двум кампаниям; масштаб — нет данных |
| Нидерланды | ACM проверил около 100 крупнейших webshops и сайтов телеком- и энергокомпаний: 61% недоступны, у 33% — «serious problems» при заказе. Дальше — требования к худшим, за неисправление — «handhaving» (принуждение). | [official: ACM, 24.03.2026] |
| Швеция, Дания | Надзор за цифровыми продуктами начался в октябре 2025. | [vendor: Level Access / сводка поиска] — проверить |
| Франция | Контроль — ARCOM и DGCCRF. Сообщают о первых предписаниях в начале 2026 года и штрафах €15 000–60 000 (предложенных). | [press/неясный источник: disabilityworld.org, 22.05.2026] — проверить |
| Испания | Сообщают о первых санкциях в конце 2025 года (киоски, €50 000–150 000). | [то же, disabilityworld.org] — проверить |
| Румыния (закон 232/2022) | Штрафы 2 500–15 000 лей; надзор за e-commerce — ANPC. Микропредприятия-услуги освобождены. | [press: juridice.ro, 08.07.2025]. Другой источник даёт нижнюю границу 6 000 лей (ст. 27) — [vendor]. Доверяем juridice.ro как юридическому изданию; оригинал на legislatie.just.ro не открылся (502) |

**Конфликт источников по первому штрафу в Германии.**
- disabilityworld.org (22.05.2026): BAFA наложил штраф «upper-five-figure» на fashion-магазин в I квартале 2026 года.
- Level Access (2026): «as of June 2026, no confirmed EAA-specific fine could be verified from reliable public sources».
- **Доверяем Level Access**, потому что надзорный орган по BFSG — MLBF, а не BAFA. Значит, у disabilityworld ошибка в базовом факте. Итог: подтверждённых штрафов в Германии нет, есть надзор и частные претензии.

**США (второй рынок того же сервиса):**
- 5 114 исков о цифровой доступности по ADA за 2025 год: 3 195 в федеральных судах и 1 919 в судах штатов (NY + CA). 70% — против e-commerce. 1 427 исков — повторные против уже судившихся компаний [vendor: UsableNet 2025 Year-End Report, PDF].
- Иски против сайтов с виджетами: по месяцам 2025 года в сумме **1 416** (сложено из помесячных цифр отчёта).
- ADA Title II (госорганы): DOJ перенёс сроки на 26.04.2027 (≥ 50 000 жителей) и 26.04.2028 (меньше) [official: Federal Register 2026-07663, 20.04.2026]. Спрос от подрядчиков госорганов (VPAT/ACR) сдвигается, но не исчезает.

**Оверлеи против ручной работы:**
- FTC: accessiBe заплатит $1 млн. Запрещено заявлять, что автоматический продукт делает сайт соответствующим WCAG, без доказательств. Предложено в январе 2025 года, окончательно утверждено в апреле 2025-го [official: ftc.gov].
- MLBF и практики сходятся: автоматика покрывает около 30–40% проверок WCAG [press: marcus-herrmann.com, 01.06.2026].
- Значит, продукт «axe-core + Playwright + ручная проверка по чек-листу + скриншоты/видео» законно отличается от оверлея. Но **обещать «соответствие» нельзя**: только «аудит по WCAG 2.1/2.2 AA с перечнем найденного».

**Цены:**

| Рынок | Цена | Источник |
|---|---|---|
| DE, полный аудит | 1 500–20 000+ €; сайт на 20–50 страниц — 4 000–8 000 €; до 20 страниц — 1 500–4 000 €; quick check — от 490 € | [vendor: barrierefix.de, 2026; сводка поиска] |
| DE, фиксированная цена | WCAG 2.2 AA audit от 2 480 € | [vendor: bfsg-experte.de] |
| DE, повторные аудиты | 700–2 500 € в год | [vendor] |
| Upwork | «$500–1 500 per project» за фокусный аудит или исправление | [provider docs: upwork.com/hire/web-content-accessibility-guidelines-wcag-freelancers, 08.2026] |
| Upwork, тревожный сигнал | Ниже $30/ч — «automated tools are doing most of the work» | [provider docs: там же] |

**Спрос на Upwork:**
- 224 открытых вакансии «Accessibility Testing» [provider docs: страница категории, число из поисковой выдержки 26.09.2026; дата снимка неизвестна].
- Примеры: remediation для WordPress и Shopify (опубликованы за 12–14 дней до снимка); VPAT на 300 порталов госсектора США.
- Число вакансий WCAG — нет данных (страница за Cloudflare, 403).

**Конкуренция:**
- Shopify App Store: виджет Avada Accessibility — 5.0, около 280–293 отзывов. Есть сканеры с исправлением кода (TestParty, Patrol) [vendor: fudge.ai, 2026]. Виджеты дешёвые и массовые, но подрывают доверие к «автоматике».
- White-label аудит для агентств уже продают HalfAccessible, Accessible Pixels, WCAG Repair, WhiteLabelIQ [vendor].
- Немецкий рынок насыщен локальными агентствами с BFSG-предложениями (десятки страниц в выдаче) [наблюдение по выдаче].

### 1.2 Оценка для оператора

- **Флот может:** crawl через Playwright → axe-core / pa11y → скриншоты и фрагменты DOM → черновик отчёта по критериям WCAG → патчи (ARIA, контраст, фокус, alt, формы) в виде PR или файла темы.
- **Не может без человека:** реальная проверка скринридером (NVDA/VoiceOver), клавиатурные сценарии checkout. Скрипты Playwright покрывают часть, итог — ручная выборка владельца, около 2–4 ч на сайт [оценка]. Опыт accessibility-аудитов у владельца есть.
- **Асинхронность:** полная; отчёт + Loom-подобное видео без голоса (TTS) или скриншоты.
- **IT Park:** исправление кода = 62.01 (IT). Аудит = 62.02 (IT-консалтинг) или 62.09 [интерпретация] — спросить MITP. Формулировку в договоре писать «software accessibility testing / IT consulting».
- **Выплата:** Upwork → OTP (USD). Прямые клиенты ЕС → счёт SRL, SEPA EUR → OTP, НДС 0% (экспорт услуг).
- **Ловушки:** обещание «compliance» (прецедент FTC); немецкие клиенты хотят отчёт на DE и часто — звонок; разговоров оператор избегает.

---

## 2. Технический SEO / AI-search (GEO), programmatic SEO, миграции — white-label для агентств

### 2.1 Что установлено

**Спрос на Upwork** (числа из поисковых выдержек страниц категорий, снимок на 26.09.2026, дата индексации неизвестна):

| Категория | Открытых вакансий |
|---|---|
| Technical SEO | 1 661 |
| Off-Page SEO | 1 994 (не наш профиль, для масштаба) |
| Website Migration | 218 |
| WordPress Migration | 233 |
| Domain Migration | 453 |
| Data Migration | 54 |
| Programmatic SEO | счётчика нет; видны отдельные вакансии, в том числе «Programmatic SEO Pipeline Developer» и «Multilingual WordPress» |
| GEO | счётчика нет; отдельные вакансии, в том числе телемедицина США (GEO + programmatic state pages) |

- **Ставки Upwork:** SEO Expert — медиана $21/ч, типично $15–35; SEO Analyst — медиана $35/ч, типично $25–50 [provider docs: upwork.com/hire/seo-experts/cost, /seo-analysts/cost; 2026].
- **Опта white-label SEO:** entry $300–700 в месяц за клиента, mid $700–1 500, premium $1 500–3 000+. Проектный аудит или миграция — $2 000–10 000; почасовая оплата — $75–200 [vendor: icecubedigital, clicksgeek 2026].

**AI Overviews меняют ценность «классического» SEO:**
- Ahrefs: CTR первой позиции при наличии AIO ниже на 58% (раньше было 34.5%, апрель 2025) [vendor: ahrefs.com].
- Pew (июль 2025, 900 взрослых, 68 879 поисков): клик по обычному результату 8% при AIO против 15% без него [press/research].
- Seer: органический CTR 1.76% → 0.61% (06.2024 → 09.2025), затем рост до 2.4% к 02.2026. Seer — [vendor]; через сводку omnibound.ai, первоисточник не открыт — проверить.
- Итог: агентствам нужен продукт «AI visibility / GEO», это аргумент для white-label.

**Цены на GEO-аудит:**
- $1 000–10 000; mid-market — $2 500–5 000 [vendor: avantevisibility, makdigitaldesign 2026].
- Но: инструменты для агентств продают автоматические GEO-аудиты по **$5 за аудит** [vendor: aisearchvisibility.ai]. Сам по себе автоматический GEO-аудит — товар без цены. Ценность — только в аудите со ставкой на исправления (schema, рендеринг, внутренние ссылки, entity-страницы) и их внедрении.

**Programmatic SEO:**
- Google с марта 2024 года применяет политики scaled content abuse, site reputation abuse и expired domain abuse. Спам-апдейты — август 2025 и март 2026 [press/vendor: stanventures, rebelmouse]. Сами политики — [official: Google Search Central], страница в этой сессии не открывалась.
- pSEO продаётся только с «уникальными данными на каждой странице», иначе клиент получит санкции, а оператор — отзыв 1*.

### 2.2 Оценка для оператора

- **Сильное место:** 15+ лет SEO; флот делает crawl (Playwright; Screaming-Frog-подобный краулер своими силами), логи, карты редиректов, проверку рендеринга JS, schema, отчёты.
- **Асинхронность:** полная. Агентства обычно работают через Slack или email; white-label не требует общения с конечным клиентом.
- **IT Park:**
  - «SEO-аудит» и «SEO-сопровождение» — 73.11, **не IT**;
  - миграция сайта (перенос, редиректы на сервере, код), внедрение schema и Core Web Vitals, сборка pSEO-движка — **62.01, IT** [интерпретация];
  - вывод: продавать «technical implementation», а не «SEO-услугу». Спросить MITP.
- **Выплата:** Upwork → OTP; агентства ЕС/UK → SEPA / SWIFT на SRL; агентства США → SWIFT USD (ACH в Молдову невозможен, см. раздел 3).

---

## 3. Лидген / pay-per-lead для кровельщиков США (на базе pickaroofer.com)

### 3.1 Что установлено

**Экономика:**
- Средняя «аренда» rank-and-rent сайта — около $900–1 000 в месяц; диапазон, который малый бизнес платит за лиды, — $500–3 000 в месяц [vendor/блоги: sidehustlenation, ranklocal.cc, 2026].
- Практическое правило — брать около 10% ожидаемой выручки подрядчика [то же].
- Кровельный лид стоит $75–250; shared — ниже, exclusive — выше [vendor: сводки 2026 — lgg.media, agedleadstore].
- Pay-per-call: медиана выплаты $38.50 за звонок по всем вертикалям, среднее $68.47; для кровли медиана CPL $130.00 [vendor/press-release: Lead Smart 2026 через wboc.com].
- Другая оценка — около $60 за кровельный звонок [vendor: Aragon Advertising 2026].
- **Конфликт** $60 и $130: разные метрики (звонок против CPL) и разные сети. Для оценки берём нижнюю, $60.
- Рост дел: roof replacement в среднем около $11 500, маржа кровельщика 20–40% [vendor, 2026].

**Как платят подрядчики США:**
- AFP 2025 Digital Payments Survey: 26% B2B-платежей в США и Канаде идут чеком (в 2004 году — 81%); 87% организаций в 2025 году ещё используют чеки [press: Nacha / KC Fed].
- ACH дешевле: $0.26–0.50 за платёж против $2.01–4 за чек [press: Nacha].
- Отсюда ожидаемый способ оплаты от небольшого кровельщика — ACH, карта или чек. Доля по малым подрядчикам — нет данных.

**Может ли Global Web SRL получить эти деньги без Stripe:**

| Способ | Статус | Комментарий |
|---|---|---|
| ACH | **Нет напрямую**: ACH работает только внутри США [provider docs: Payoneer] | Нужен US receiving account: Payoneer (для Молдовы — «подтвердить при регистрации», база `STATUS.md`) |
| Международный wire (SWIFT USD) на OTP | **Да** технически; OTP берёт 0 за входящие для компаний (база) | Комиссию отправителя платит подрядчик, обычно это барьер. Размер комиссии банков США — нет данных. OTP запросит договор и счёт |
| Карта: Stripe | Нет | База проекта |
| Карта: 2Checkout / Verifone (2Sell) | **Возможно**: Молдовы нет ни в списке стран, которым отказано в PSP-аккаунтах, ни среди санкционных (Cuba, Iran, North Korea, Syria, Крым, Донецк, Луганск) [provider docs: docs.2checkout.com, 26.09.2026] | Допускает ли 2Checkout услуги по лидогенерации и SEO — **проверить** (одобрение merchant) |
| Карта: maib e-commerce | Visa/MC/Amex, Apple/Google Pay [provider docs: maib.md]. Для зарубежного биллинга «not the right tool» [vendor: incorpore.md, 03.06.2026] | Приём карт США — проверить у банка |
| PayPal invoicing | «Зависит от аккаунта» (база) | Проверить |
| Продавать звонки в pay-per-call сеть, а не подрядчику | Сети платят паблишерам ACH или wire [vendor: Lead Smart] | Принимают ли международных паблишеров и платят ли SWIFT в Молдову — нет данных |

**Конфликт по Wise:**
- Incorpore (03.06.2026) пишет «Wise supports Moldovan SRLs».
- База проекта [official, страницы Wise]: Wise для резидентов Молдовы недоступен.
- Доверяем базе: у Incorpore это вендорский блог, у базы — страница провайдера. Проверить на странице Wise Business, если понадобится.

### 3.2 Оценка для оператора

- **IT Park:** продажа лидов — 73.11 или неясно, **не IT** (база). Весь лидген — внутри 30% не-IT или вне SRL (antreprenor independent). Но 47.91 и 73.11 для AI недоступны — проверить.
- **Налог США:** SRL даёт подрядчику W-8BEN-E; услуги оказываются вне США [интерпретация] — спросить бухгалтера.
- **Первые деньги за 30 дней маловероятны:** pickaroofer.com запущен в 09.2026. Нужно 1) ранжироваться, 2) найти подрядчика по входящему запросу (объявление «Advertise with us» на сайте, а не cold outreach), 3) получить платёж по одному из путей выше. Каждое звено может сорвать срок.
- **Ловушки:**
  - «перепродажа звонков» без согласия (TCPA);
  - записи звонков — согласие по законам штатов, проверить;
  - фейковые отзывы на GBP — исключено правилами проекта;
  - GBP (Google Business Profile) на виртуальный адрес — нарушение правил Google, исключено.

---

## 4. RU/RO/UA-услуги, где владелец сам проверяет качество

### 4.1 Что установлено

**Upwork** (выдержки страниц категорий, снимок на 26.09.2026):
- English→Romanian Translation — 87 открытых;
- Romanian→English — 55;
- Language Localization (все языки) — 1 082;
- по RU и UA — нет данных (не искалось, лимит).

**Цены:**
- MTPE $0.05–0.15 за слово, обычно на 30–50% дешевле человеческого перевода; человеческий перевод — $0.07–0.14 (есть оценки до $0.15–0.30) [vendor: alconost, weglot, smartling 2026].
- Румынский — от $0.08 за слово [vendor: writeliff].

**Рынок Румынии:**
- B2C e-commerce — €12.9 млрд в 2025 году (+10% за год), крупнейший в Восточной Европе [press: nineoclock.ro со ссылкой на European E-Commerce Report 2026].
- Число интернет-магазинов — нет данных.
- 121 SaaS-компания в Румынии, $548.8 млн выручки [vendor: getlatka, 08.2026].

**SEO-цены в Румынии** [vendor, сайты агентств 2026]:
- аудит — 500–2 000 лей (простой);
- полный аудит — 2 499 лей (сайт-визитка) … 39 999 лей (крупный магазин), средний сайт — 7 499–17 499 лей;
- абонемент — 500–6 000 лей в месяц; пакеты 600 / 1 000 / 1 350 лей.

**Оплата:** румынские компании платят SEPA EUR или RON-переводом; OTP Moldova в SEPA (база).

**Молдова (МСБ):** цены на сайты и объём спроса — нет данных в этой сессии.

**Россия:** клиенты из РФ исключены практически. Платёжные рельсы РФ → Молдова завязаны на санкционные ограничения. Правило проекта — «не обходить санкции и платёжные блокировки». RU-язык продаём клиентам вне РФ: SaaS, которые локализуют продукт на RU для Казахстана, Израиля, Балтии.

### 4.2 Оценка

- **Локализация SaaS EN→RO/RU:** флот переводит, владелец — носитель RO/RU и полностью проверяет. Это редкое для рынка качество QA.
  - IT Park: перевод — 74.30, **не IT**;
  - «software localization engineering» (i18n-ключи, pluralization, строки в коде, сборка) — 62.01 [интерпретация].
- **SEO для RO e-shops:** SEPA, асинхронно по-румынски. Цены низкие (абонемент от 600 лей), конкуренция — местные агентства.
- **Сайты МСБ RO/MD:** 62.01 — IT, основная «IT-масса» для правила 70%. Канал — только входящий (свои лендинги на RO с SEO, каталоги). Клиенты в Молдове часто хотят звонок — ограничение.

---

## 5. Upwork: спрос, ставки, Connects, барьеры для новичка

- **Connects:** $0.15 за штуку. Basic — бесплатно, 10 Connects в месяц; Freelancer Plus — $19.99 в месяц, 100 Connects [vendor: сводки golance, vortenza 2026; цена $0.15 подтверждается несколькими источниками]. Справка Upwork (support.upwork.com) отвечает 403 — не прочитана.
- **Отклик стоит** 10–24 Connects, то есть **$1.50–3.60**. Цена может расти, пока вакансия открыта; boost — аукцион Connects [vendor: bidpilotpro, zenlance со ссылкой на справку Upwork].
- **Комиссия фрилансера:** с 01.05.2025 переменная, **0–15%** вместо фиксированных 10%. Ставку показывают при отклике, она фиксируется на весь контракт [vendor: gigradar, golance]. Клиент на Basic платит 7.99% marketplace fee [vendor: сводка по upwork.com/pricing/client] — проверить на странице Upwork.
- **Project Catalog:** до 20 фиксированных «проектов» одновременно, клиент покупает сам [provider docs: support.upwork.com, выдержка]. Это единственный входящий канал Upwork без откликов.
- **Барьеры для новичка:**
  - профиль может быть отклонён в насыщенных категориях;
  - «около 30% заявок отклонено в 2025» — [forum / блог, без первоисточника] — нет надёжных данных;
  - Rising Talent выдаётся автоматически при полном профиле и заработке от $250 за 12 месяцев [vendor, ссылаются на справку Upwork; проверить].
- **Масштаб Upwork:** около 800 000 активных клиентов, более $4 млрд расходов в год [vendor: сводка] — проверить по отчётности Upwork.
- **Upwork In-Demand Skills 2026:** навыки применения ИИ +109% за год [official-корпоративный: investors.upwork.com].
- **Юридическое лицо:** выплата Direct to Local Bank на счёт SRL — нужен ли Agency-аккаунт или совпадение имени владельца счёта, **проверить**. Для аудита IT Park нужны инвойсы Upwork как первичка — спросить бухгалтера.

---

## 6. Ниши: 18 конкретных (услуга × покупатель × рынок)

Таблица разбита на две, связь по ID. Копия (сводная) — `notes/niches_b2b_services.csv`.

### 6A. Спрос, конкуренция, цена, выплата

| ID | Ниша | Покупатель × рынок | Канал | Доказательства спроса | Конкуренция | Цена | IT Park | Выплата в Молдову |
|---|---|---|---|---|---|---|---|---|
| N1 | WCAG 2.2 / EAA-аудит checkout для Shopify/Shopware | e-commerce 10+ сотрудников, NL/DE/Nordics, отчёт EN | Upwork Catalog + свой лендинг «EAA audit» EN | ACM: 61% из ~100 крупнейших NL-магазинов недоступны (24.03.2026) [official]; MLBF работает с 01.2026 [official] | DE-агентства, виджеты; ручных EN-аудиторов мало — нет данных | $500–1 500 (Upwork) [provider]; DE 1 500–4 000 € [vendor] | 62.02 / 62.09? [интерпр.] | Upwork → OTP; SEPA → SRL |
| N2 | White-label аудит + исправление доступности | веб-агентства US/UK/EU | Upwork, партнёрские страницы, сообщества агентств | 224 вакансии Accessibility Testing (Upwork) [provider]; 5 114 исков ADA 2025 [vendor UsableNet] | HalfAccessible, Accessible Pixels, WCAG Repair [vendor] | $500–1 500 за проект [provider] | 62.01 (исправление) | Upwork / SWIFT USD / SEPA |
| N3 | VPAT / ACR (Section 508, EN 301 549) для B2B SaaS | SaaS, продающие госорганам US/EU | Upwork | вакансия «Accessibility Audit & VPAT… 300 portals» [provider]; Title II → 2027/2028 [official] | консультанты США с IAAP | нет данных (цена за ACR) | 62.02? | Upwork → OTP |
| N4 | Исправление доступности тем WordPress / Shopify | владельцы сайтов США (ADA) и ЕС | Upwork (вакансии remediation WP/Shopify) | вакансии WP и Shopify remediation, 12–14 дней [provider] | фрилансеры из Индии от $18/ч [provider] | $30+/ч, ниже — «red flag» [provider] | 62.01 | Upwork → OTP |
| N5 | Ежемесячный мониторинг доступности (регрессии) | клиенты N1–N4 | апсейл | 1 427 повторных исков (45% федеральных) [vendor UsableNet] | SaaS-сканеры | DE: повторные 700–2 500 €/год [vendor] | 63.11 / 62.09 | SEPA / Upwork |
| N6 | BFSG quick-check + Barrierefreiheitserklärung (на DE) | малые DE-магазины 10+ сотрудников | DE-лендинг | Abmahnungen с 08.2025 [vendor] | очень высокая (десятки DE-агентств) | quick-check от 490 € [vendor] | 62.02? | SEPA |
| N7 | White-label технический SEO-аудит (краулинг, рендеринг, индексация, план исправлений) | SEO- и веб-агентства US/UK/EU | Upwork + сообщества агентств | 1 661 открытая вакансия Technical SEO [provider] | высокая; ставки $15–50/ч [provider] | опт $300–700 в месяц за клиента; проект $2 000–10 000 [vendor] | **не IT** (73.11), если «SEO»; 62.01, если внедрение | Upwork / SWIFT / SEPA |
| N8 | SEO-безопасная миграция сайта (карта редиректов, crawl до/после, мониторинг) | агентства и e-commerce, EN | Upwork | 218 Website + 233 WordPress + 453 Domain Migration [provider] | средняя | нет данных по Upwork; опт-проекты $2 000–10 000 [vendor] | 62.01 [интерпр.] | Upwork → OTP |
| N9 | GEO / AI-visibility аудит с внедрением schema и entity-страниц | SaaS и B2B-сайты US | Upwork (GEO-вакансии) | GEO-вакансии есть, счётчика нет [provider]; падение CTR при AIO на 58% [vendor Ahrefs] | ценовой обвал: авто-аудит за $5 [vendor] | $1 000–5 000 (mid) [vendor] — для новичка нереально | 62.01 (внедрение) / 73.11 | Upwork |
| N10 | Programmatic SEO-движок на данных клиента | SaaS / маркетплейсы US | Upwork | вакансии «pSEO Pipeline Developer» и др. [provider] | средняя | нет данных | 62.01 | Upwork / SWIFT |
| N11 | Локализация SaaS / приложений EN→RO (MTPE + QA носителя) | SaaS и приложения, выходящие в RO/MD | Upwork, биржи локализационных компаний | 87 вакансий EN→RO [provider] | много переводчиков из RO | $0.05–0.15 за слово (MTPE) [vendor] | 74.30 не IT; i18n — 62.01 | Upwork / SEPA |
| N12 | Технический SEO-аудит + абонемент для румынских e-shops (на RO) | e-commerce RO | свой RO-лендинг + SEO, сообщества GPeC | рынок €12.9 млрд, 2025 [press] | местные агентства | аудит 2 499–17 499 лей; абонемент 600–1 350 лей в месяц [vendor] | не IT (73.11) | SEPA EUR / RON → OTP |
| N13 | Сайты «под ключ» для МСБ RO/MD (RO/RU) | МСБ Молдовы и Румынии | свой лендинг + SEO, каталоги | нет данных | высокая | нет данных | 62.01 | MDL / SEPA |
| N14 | Pay-per-lead кровли (pickaroofer.com) | кровельщики США | входящая форма «Advertise» на сайте | CPL $75–250 [vendor] | Angi, HomeAdvisor и др. | $75–250 за лид [vendor] | не IT | SWIFT / 2Checkout? / Payoneer? |
| N15 | Rank-and-rent: копии pickaroofer в других городах | кровельщики США | то же | аренда ~$900–1 000/мес [vendor] | высокая | ~$900–1 000 в месяц [vendor] | не IT | то же |
| N16 | Продажа звонков в pay-per-call сеть | сети (Lead Smart и т. п.) | заявка паблишера | медианный CPL кровли $130 [vendor] | — | $60–130 за звонок [vendor] | не IT | ACH / wire сети — международные паблишеры? нет данных |
| N17 | Оптимизация Core Web Vitals для WP/Shopify | магазины US/EU | Upwork | нет данных (счётчик не найден) | высокая | нет данных | 62.01 | Upwork |
| N18 | Внедрение structured data (Product, Merchant listings, FAQ) + валидация | e-commerce и агентства | Upwork Catalog | нет данных (счётчик не найден) | средняя | нет данных | 62.01 | Upwork |

### 6B. Исполнимость, тест, сроки, потолок

P — вероятность первого $ за 30 дней, **[оценка]** по наличию входящего канала и числу вакансий. Ч/нед — часы владельца на проверку и переписку [оценка]. Потолок — месяц 6 [оценка, формула].

| ID | Флот без лица и GPU | Асинхронно | Самый дешёвый 14-дневный тест | До первого $ | Потолок м6 [оценка] | P | Ч/нед |
|---|---|---|---|---|---|---|---|
| N1 | да, но скринридер — вручную | да | 3 позиции в Project Catalog + 20 откликов (≈20×16×$0.15 = $48) + 1 лендинг | 2–5 нед | $1 000 × 3 = **$3 000** | 0.25 | 8 |
| N2 | да | да | 20 откликов ($48) + пример отчёта на демо-сайте | 2–4 нед | $600 × 4 + $150 × 3 retainer = **$2 850** | 0.20 | 6 |
| N3 | частично: ACR требует экспертного суждения | да | 10 откликов ($24) | 3–6 нед | $1 200 × 2 = **$2 400** | 0.15 | 6 |
| N4 | да (патчи тем), проверка владельцем | да | 20 откликов ($48) | 1–3 нед | $30/ч × 60 ч = **$1 800** | 0.35 | 8 |
| N5 | да | да | только апсейл N1–N4 | после N1–N4 | $99 × 15 = **$1 485** | 0.10 | 2 |
| N6 | частично: DE без полной проверки | да | DE-лендинг, $0 | 4+ нед | 490 € × 4 ≈ **$2 230** | 0.10 | 8 |
| N7 | да (сильная сторона владельца) | да | 3 позиции в Catalog + 30 откликов ($72) | 1–3 нед | $400 × 6 = **$2 400** | 0.35 | 6 |
| N8 | да | да | 20 откликов ($48) | 1–3 нед | $1 200 × 2 = **$2 400** | 0.30 | 8 |
| N9 | да | да | 10 откликов ($24) | 2–4 нед | $300 × 4 = **$1 200** | 0.25 | 4 |
| N10 | да | да | 10 откликов ($24) | 3–6 нед | $2 500 × 1 = **$2 500** | 0.15 | 8 |
| N11 | да; QA — владелец | да | 20 откликов ($48) | 1–2 нед | 30 000 слов × $0.06 = **$1 800** | 0.45 | 8 |
| N12 | да; язык RO — владелец | да | RO-лендинг + 2 бесплатных мини-аудита в сообществах | 3–5 нед | (1 000 лей × 5 + 7 500 лей × 1) / 5 ≈ €2 500 ≈ **$2 840** | 0.20 | 6 |
| N13 | да | частично (клиенты хотят звонки) | RO/RU-лендинг, $0 | 3–6 нед | 600 € × 3 ≈ **$2 050** | 0.25 | 6 |
| N14 | да (сайт уже есть) | да | форма «Advertise here» на pickaroofer | 6+ нед (ранжирование) | $100 × 15 = **$1 500** | 0.15 | 3 |
| N15 | да | да | не за 14 дней: ранжирование — месяцы | 3–6 мес | $900 × 2 = **$1 800** | 0.05 | 3 |
| N16 | да | да | заявка паблишера, $0 | 6+ нед | $60 × 20 = **$1 200** | 0.10 | 2 |
| N17 | да | да | 20 откликов ($48) | 1–3 нед | $400 × 4 = **$1 600** | 0.30 | 5 |
| N18 | да | да | 3 позиции в Catalog + 15 откликов ($36) | 1–3 нед | $250 × 6 = **$1 500** | 0.30 | 4 |

Формула Connects: откликов × 16 Connects (середина диапазона 10–24) × $0.15 [оценка]. Плюс Freelancer Plus $19.99, если нужен.

---

## 7. Топ-5 по формуле (P × потолок м6) / часы владельца в неделю

Счёт [оценка]:

| ID | Счёт |
|---|---|
| N7 | 140 |
| N18 | 112.5 |
| N11 | 101 |
| N17 | 96 |
| N2 | 95 |
| N12 | 95 |
| N1 | 94 |
| N8 | 90 |
| N13 | 85 |
| N4 | 79 |
| N9 | 75 |
| N14 | 75 |
| N5 | 74 |
| N3 | 60 |
| N16 | 60 |
| N10 | 47 |
| N15 | 30 |
| N6 | 28 |

1. **N7 — white-label технический SEO-аудит для агентств (Upwork).** Самый большой видимый спрос (1 661 вакансия Technical SEO). Ядро компетенции владельца, флот делает crawl и отчёт. Минус — SEO не IT (73.11). Продавать как «technical implementation plan + fixes», часть счёта — 62.01.
2. **N18 — внедрение structured data.** Узкая фикс-услуга для Project Catalog; код = 62.01 (IT); проверка валидатором автоматическая. Минус — счётчика спроса нет, P взята по аналогии с N7.
3. **N11 — локализация EN→RO (MTPE + QA носителя).** Самый быстрый первый $: 87 вакансий, короткие задачи. Потолок низкий, перевод не IT. Держать как быстрый «первый отзыв» на Upwork.
4. **N17 — Core Web Vitals для WP/Shopify.** IT (62.01), асинхронно, флот делает сам. Минус — спрос численно не подтверждён.
5. **N2 — white-label доступность для агентств.** EAA + иски ADA дают спрос в двух юрисдикциях. Исправление — IT. Ручная проверка скринридером — узкое место владельца.

**Практический вывод [оценка]:** N7 + N8 + N17 + N18 + N1/N2 — это один Upwork-профиль «Technical SEO & Accessibility engineer» с 5–6 позициями в Project Catalog. Один канал, одни отзывы, IT-доля за счёт внедрения. N11 — параллельно ради быстрых отзывов. Лидген (N14–N16) — не для 30-дневной цели: платёжный путь от кровельщиков США не подтверждён, доход не IT.

---

## 8. Ловушки и тупики

- **Обещать «EAA/ADA compliance» или продавать оверлей.** Прецедент FTC — accessiBe, $1 млн (01–04.2025) [official]. 1 416 исков в 2025 году — против сайтов с виджетами [vendor UsableNet].
- **Считать, что EAA касается всех.** Микропредприятия-услуги освобождены; B2B SaaS, как правило, вне сферы. Продавать МСБ из 3 человек — нечестно.
- **Немецкий рынок BFSG:** много местных агентств, клиенты ожидают DE и звонки. Первый «штраф BAFA» в прессе — вероятно, ошибка (раздел 1.1).
- **Автоматический GEO-аудит:** рынок продаёт его по $5 [vendor]. Без внедрения — не услуга.
- **Programmatic SEO без уникальных данных:** scaled content abuse; спам-апдейты 08.2025 и 03.2026 [press].
- **ACH от подрядчиков США:** в Молдову напрямую невозможен. Wise недоступен (база) — вендорские блоги ошибаются.
- **Клиенты из РФ:** платёжные пути упираются в санкционные ограничения, исключено правилами проекта.
- **Kwork, Etsy — не работают** (база). Fiverr — только через PayPal/Payoneer, которых нет.
- **IT Park, 70%:** SEO, переводы, лидген суммарно ≤ 30% оборота нарастающим итогом. Нарушение — пересчёт по общему режиму с месяца нарушения (ст. 378 НК; база).
- **Upwork-комиссия 0–15% неизвестна заранее.** В новых категориях с высоким предложением может быть близка к 15% [vendor]. Считать маржу по 15%.

---

## Что не удалось проверить

- Страницы Upwork (help center, категории вакансий) — 403 / Cloudflare. Числа вакансий взяты из поисковых выдержек, дата снимка неизвестна. Счётчики для WCAG, GEO, Programmatic SEO, Core Web Vitals, schema, RU/UA-локализации не найдены.
- Официальная справка Upwork о комиссии 0–15%, цене Connects, Freelancer Plus — только через вендорские сводки.
- Работает ли Direct to Local Bank на счёт **юрлица** (Global Web SRL) и нужен ли Agency-аккаунт.
- Первые штрафы EAA во Франции, Испании, Германии (disabilityworld против Level Access); статистика дел MLBF — не опубликована.
- Полный текст закона 232/2022 (Румыния): legislatie.just.ro — 502; нижняя граница штрафа 2 500 или 6 000 лей.
- Текст директивы 2019/882 (сфера для B2B SaaS, ст. 4(5)) в этой сессии не открывался — опора на вторичные источники.
- 2Checkout: одобрят ли SRL из Молдовы для услуг или лидогенерации; комиссии.
- Payoneer для Молдовы (US receiving account / ACH) — вопрос базы, не перепроверялся.
- Принимают ли pay-per-call сети международных паблишеров и платят ли SWIFT в Молдову.
- Комиссии банков США за исходящий SWIFT для подрядчика.
- Цены за VPAT/ACR, миграции, CWV и schema на Upwork; спрос на сайты МСБ в Молдове.
- Контра (Contra): выплата в Молдову. Справка ссылается на «payout support list», Молдова не упомянута; Stripe Global Payouts поддерживает Молдову с 25.02.2026 [provider docs Stripe], но использует ли его Contra — не проверено.
- Классификация CAEM для аудита доступности, технического SEO и локализации — только интерпретация, **спросить MITP / аудитора**.
- Курс RON/EUR — допущение 5.0, не проверен.

## Источники (дата обращения — 26.09.2026, если не указано иное)

**EAA / доступность**
- ACM, «Klant met beperking kan bij merendeel grote webwinkels niet terecht», 24.03.2026 — https://www.acm.nl/nl/publicaties/acm-klant-met-beperking-kan-bij-merendeel-grote-webwinkels-niet-terecht [official]
- Пресс-служба Саксонии-Анхальт о MLBF, 01.06.2026 — https://presse.sachsen-anhalt.de/ministerium-fur-arbeit-soziales-gesundheit-und-gleichstellung/2026/06/01/zugang-zu-modernen-produkten-und-dienstleistungen-fuer-alle-neue-marktueberwachungsbehoerde-in-magdeburg-formiert-sich [official]
- MLBF — https://www.mlbf-barrierefrei.de/ [official]
- marcus-herrmann.com, «Juni 2026: Die MLBF verrät, wie sie prüfen will», 01.06.2026 — https://marcus-herrmann.com/blog/mlbf-verraet-wie-sie-pruefen-will [press/эксперт]
- disabilityworld.org, «EAA First Year», 22.05.2026 — https://www.disabilityworld.org/articles/eaa-first-year-enforcement-report/ [press, низкое доверие]
- Level Access, EAA penalties 2026 — https://www.levelaccess.com/blog/penalties-for-eaa-non-compliance/ ; https://www.levelaccess.com/compliance-overview/european-accessibility-act-eaa/ [vendor]
- xictron.de, BFSG-Abmahnwelle 2026 — https://www.xictron.com/de/blog/bfsg-abmahnwelle-2026-barrierefreiheit-durchsetzen [vendor]
- barrierefix.de, цены на аудит 2026 — https://www.barrierefix.de/de/blog/was-kostet-accessibility-audit-preise-2026 [vendor]
- bfsg-experte.de — https://www.bfsg-experte.de/de/wcag-audit/ [vendor]
- juridice.ro, закон 232/2022, 08.07.2025 — https://www.juridice.ro/791199/obligatii-noi-privind-accesibilitatea-cum-afecteaza-legea-232-2022-operatorii-economici-incepand-cu-28-iunie-2025.html [press]
- FTC, accessiBe final order, 04.2025 — https://www.ftc.gov/news-events/news/press-releases/2025/04/ftc-approves-final-order-requiring-accessibe-pay-1-million [official]
- Federal Register 2026-07663, продление сроков ADA Title II, 20.04.2026 — https://www.federalregister.gov/documents/2026/04/20/2026-07663/extension-of-compliance-dates-for-nondiscrimination-on-the-basis-of-disability-accessibility-of-web [official]
- UsableNet, 2025 Year-End Digital Accessibility Lawsuit Report (PDF) — https://info.usablenet.com/hubfs/Remediated%20-%202025_Year-End_Digital_Accessibility_Lawsuit_Report_FINAL.pdf [vendor]
- Upwork, WCAG specialists (цены), 08.2026 — https://www.upwork.com/hire/web-content-accessibility-guidelines-wcag-freelancers/ [provider docs]
- Upwork, Accessibility Testing jobs — https://www.upwork.com/freelance-jobs/accessibility/ [provider, выдержка]
- fudge.ai, Shopify accessibility apps 2026 — https://www.fudge.ai/blog/best-shopify-accessibility-apps/ [vendor]
- HalfAccessible / Accessible Pixels / WCAG Repair (white-label) — https://halfaccessible.com/specialty/digital-agencies-white-label-accessibility/ ; https://www.accessiblepixels.com/agency-partners ; https://www.wcagrepair.com/agency [vendor]

**SEO / GEO / Upwork**
- Upwork, Technical SEO jobs — https://www.upwork.com/freelance-jobs/technical-seo/ [provider, выдержка]
- Upwork, Website / WordPress / Domain Migration jobs — https://www.upwork.com/freelance-jobs/website-migration/ [provider, выдержка]
- Upwork, Off-Page SEO jobs — https://www.upwork.com/freelance-jobs/off-page-seo/ [provider, выдержка]
- Upwork, SEO Experts / Analysts cost — https://www.upwork.com/hire/seo-experts/cost/ ; https://www.upwork.com/hire/seo-analysts/cost/ [provider docs]
- Upwork, GEO specialists, 09.2026 — https://www.upwork.com/hire/geo-specialists/ [provider]
- Upwork, In-Demand Skills 2026 — https://investors.upwork.com/news-releases/news-release-details/upworks-demand-skills-2026-demand-top-ai-skills-more-doubles-ai [official-корпоративный]
- Сводки о комиссиях и Connects Upwork 2026 — https://golance.com/blogs/upwork-fees-explained-2026 ; https://gigradar.io/blog/upwork-fees ; https://www.bidpilotpro.com/blogs/upwork-connects-strategy [vendor]
- Upwork Help, Freelancer Service Fee — https://support.upwork.com/hc/en-us/articles/211062538 (403, не прочитано)
- icecubedigital, White label SEO pricing 2026 — https://www.icecubedigital.com/blog/white-label-seo-pricing-2026/ [vendor]
- Ahrefs, AI Overviews reduce clicks — https://ahrefs.com/blog/ai-overviews-reduce-clicks/ [vendor]
- omnibound.ai, сводка Seer и Pew — https://www.omnibound.ai/blog/google-ai-overviews-statistics [vendor]
- avantevisibility, AI visibility audit cost 2026 — https://avantevisibility.com/blog/ai-visibility-audit-cost-2026 ; aisearchvisibility.ai/for/agencies [vendor]
- Stan Ventures, спам-апдейты 2026 — https://www.stanventures.com/news/7-google-spam-updates-later-where-seo-stands-in-2026-7573/ [press]

**Лидген / платежи США**
- Lead Smart, 2026 pay-per-call benchmarks (wboc.com) — https://www.wboc.com/online_features/press_releases/lead-smart-publishes-2026-pay-per-call-payout-benchmarks-for-hvac-plumbing-roofing-garage-door/article_6afb47b2-86ce-514d-b136-b7b29f73a731.html [vendor/press release]
- Aragon Advertising, pay per call 2026 — https://blog.aragon-advertising.com/posts/how-to-make-money-with-pay-per-call/ [vendor]
- Side Hustle Nation / RankLocal, rank and rent — https://www.sidehustlenation.com/rank-and-rent/ ; https://ranklocal.cc/blog/how-rank-and-rent-seo-works [vendor/блог]
- LGG Media, roofing leads cost 2026 — https://www.lgg.media/blog/roofing-leads-cost/ [vendor]
- Nacha о AFP 2025 Digital Payments Survey — https://www.nacha.org/news/over-21-years-massive-drop-b2b-check-payments-study-finds [press]
- 2Checkout Help & FAQs — https://docs.2checkout.com/get-started/getting-started/help-and-faqs.md ; https://docs.2checkout.com/llms-full.txt [provider docs]
- maib e-commerce — https://www.maib.md/en/persoane-juridice/e-commerce [provider docs]
- Incorpore, Payment processing for Moldovan SRLs, 03.06.2026 — https://incorpore.md/en/blog/payment-processing-moldova-stripe-paypal/ [vendor]
- Payoneer, SWIFT и ACH — https://www.payoneer.com/resources/business/payoneer-swift-ach-transfers/ [provider docs]
- Stripe changelog, cross-border payouts +12 стран (Молдова), 25.02.2026 — https://docs.stripe.com/changelog/clover/2026-02-25/cross-border-payouts-new-countries [provider docs]
- Contra, Payout methods, 26.03.2025 — https://help.contra.com/en/articles/9322938-payout-methods-for-freelancers-on-contra [provider docs]

**RO / локализация**
- Upwork, EN→RO / RO→EN / Language Localization jobs — https://www.upwork.com/freelance-jobs/translation-english-romanian/ ; https://www.upwork.com/freelance-jobs/translation-romanian-english/ ; https://www.upwork.com/freelance-jobs/language-localization/ [provider, выдержки]
- Alconost, localization cost 2026 — https://alconost.com/en/blog/localization-cost ; Weglot MTPE — https://www.weglot.com/blog/machine-translation-post-editing-rates [vendor]
- nineoclock.ro, Romania e-commerce €12.9 bn 2025 — https://nineoclock.ro/romania-eastern-europes-largest-e-commerce-market-e12-9-billion-in-2025-more-than-double-the-2021-level/ [press]
- smetytech.com, стоимость SEO-аудита в Румынии 2026 — https://smetytech.com/blog/cost-audit-seo-romania ; neuroweb.ro, пакеты SEO — https://neuroweb.ro/preturi/optimizare-seo.html [vendor]
- getlatka, SaaS в Румынии, 08.2026 — https://getlatka.com/companies/countries/romania [vendor]

**База проекта:** `STATUS.md` (разд. 2.1–2.4, 2.6), `notes/it_park_verified.md`, `notes/srl_it_park.md`.

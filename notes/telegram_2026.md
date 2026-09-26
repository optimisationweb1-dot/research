# Экосистема Telegram 2026 при выплате в крипту (Stars / GRAM / USDT)

Дата: 26.09.2026. Поток «Telegram ecosystem» мастер-плана.
Только исследование: аккаунты не создавались, формы не отправлялись, ничего не покупалось. Публичный API трекера мини-аппов (tgadsspy.com, лицензия CC-BY-4.0) читался без регистрации, 5 запросов.
Это исследование, а не юридическая или налоговая консультация.

**Метки:** [official] — правила, документация и блог Telegram, Fragment, госисточники, GitHub API; [provider docs] — страницы провайдера (Adsgram, Monetag, Bybit, Google); [provider data] — выгрузка с сайта или API провайдера; [press]; [vendor] — блоги продавцов, агрегаторов, трекеров; [forum] — анекдоты и частные посты; [оценка] — с формулой.

**База проекта (не перепроверялась):** `STATUS.md` 2.5 (Stars ≈ $0.013, холд 21 день, рекламная доля 50% в TON, лимит 50 000 лей/мес на крипта→банк), `notes/crypto_rails_2026.md` (SRL не получает крипту — Stars/GRAM идут физлицу-владельцу аккаунта; CR-04, CR-08; Contra платит USDC в Молдову), `notes/it_park_verified.md` (бот/мини-апп за Stars — вероятно IT; контент канала, донаты — нет), `notes/decision_niche_1.md` (Telegram был «не сейчас» из-за рельса крипта→банк; теперь крипта приемлема).

**Допущения по умолчанию (вопросы не задавались):**
1. Бот, канал и Fragment привязаны к личному Telegram-аккаунту владельца → доход физлица в GRAM/USDT на свой кошелёк (Tonkeeper) → свой KYC-аккаунт Bybit. Налоги — позже (решение 26.09).
2. «Первый доход» в поле `p_first_usd_30d` = деньги, реально выведенные на свой кошелёк (не начисление Stars). Из-за холда 21 день у Stars-продуктов эта вероятность структурно мала.
3. Флот пишет код и контент; владелец — аккаунты, QA на RU/RO, модерация, переписка на EN письменно.

---

## TL;DR

1. **Рельс работает, спрос — узкое место.** Выплата Stars → Fragment → GRAM на свой TON-кошелёк → Bybit (депозиты GRAM возобновлены 22.06.2026) технически готова. Официально: **$0.013 за Star**, минимум **1 000 Stars** за вывод, **холд до 21 дня**, Stars действуют 3 года [official]. Реклама в каналах — 50%, выводится в GRAM через 2 дня [official]. Отдельной страны-исключения для Молдовы нет, но Fragment «may be unable to issue rewards… in certain countries» — проверить первым выводом.
2. **Первые деньги за 30 дней из Stars почти невозможны**: надо продать ≥1 000 Stars (≈ $13) в первые ~9 дней, иначе холд переносит вывод за 30-й день. Реалистично 35–50 дней. Быстрее только B2B-услуги с оплатой в USDT (**TG-01**).
3. **Рынки:** РФ фактически заблокирована (весна 2026: без VPN доступно ~5% соединений; дневной охват −49.4% за янв–май), а купить Stars из РФ официально почти нельзя → не таргетировать. **Украина** — самый «телеграмный» рынок (81% пользуются для общения, 72% — для новостей, 2025). Молдова и Румыния — малая доля Telegram. Индия — объём, но блокировка Telegram 16–22.06.2026 из-за утечек экзаменов. Иран/фарси — санкционная ловушка.
4. **Платформа сама съедает простые боты:** встроенные ИИ-сводки (01.2026), ИИ-редактор и перевод (03.2026), скан документов (03.2026), приветствия в группах (08.2026). Не строить боты-переводчики, суммаризаторы, приветствия.
5. **Новые API 2026 дают окно для флота:** Managed Bots (03.04), Guest Mode — бота можно позвать в любой чат (08.05), Chat Automation для всех пользователей (07.05), Join Request Queries / AI guardians (11.06), подписки в Stars с событиями продления (14.07) [official].
6. **Лучшие кандидаты** [оценка]:
   - **TG-01** — разработка ботов и мини-аппов под ключ для крипто-нативных заказчиков с оплатой в USDT/USDC: p = 0.2, потолок ≈ $1 800/мес;
   - портфель из 2–3 Stars-ботов на общем коде: **TG-02** (AI guardian для групп), **TG-13** (ИИ-редактор фото для UA/EN), **TG-04** (фото на документы). У каждого потолок $270–470/мес, p ≤ 0.05.
   Реклама, партнёрки, игры и гранты — меньше $250/мес или тупик.
7. **Вывод для мастер-плана:** Telegram — вспомогательный канал, а не ниша №1. Лучший ход — TG-01 как крипто-дополнение к Upwork-нише. Stars-боты делать только если код переиспользуется (Apify, SaaS), а заработанные Stars реинвестировать в Telegram Ads: в рекламе Star стоит $0.02, при выводе — $0.013 [official].

---

## 1. Находки

### 1.1 Механика выплат и правила (a)

| Факт | Значение | Источник |
|---|---|---|
| Выплата за 1 Star (боты, платные посты, подписки) | **$0.013** («Developers can receive an equivalent of 0.013 USD worth of rewards for each Telegram Star»); в конфиге клиента `stars_usd_withdraw_rate_x1000 = 1300` | [official] Bot Developer ToS 6.2.4; core.telegram.org/api/config |
| Цена Stars для покупателя | пакет 1 000 Stars в App Store/Google Play — $19.99 (30% сторам + $0.99 «administrative»); курс Telegram `stars_usd_sell_rate_x1000 = 1410` ($14.10) | [official] таблица цен + config; расчёт — [vendor] adminhub.tools, проверено 09.09.2026 |
| Минимум / максимум вывода | 1 000 / 25 000 000 Stars | [official] config `stars_revenue_withdrawal_min/max` |
| Холд | Stars — «up to 21 days»; рекламная доля в Gram — 2 дня | [official] Bot Dev ToS 6.2.4; Content Creator ToS 4 |
| Срок жизни Stars | 3 года, затем сгорают | [official] Bot Dev ToS |
| Stars в рекламу | 1 Star = **$0.02** рекламного кредита (выгоднее вывода на 54%) | [official] Bot Dev ToS 6.2.3 |
| Чем платит Fragment | по умолчанию **Gram ($GRAM)** на подключённый TON-кошелёк; «In some countries, rewards could be paid in alternative ways, such as stablecoins»; курс — CoinMarketCap, обновление ~5 мин | [official] fragment.com/terms, разд. 5–6 |
| Страны | «Fragment may be unable to issue rewards for certain users or in certain countries»; список не опубликован | [official] Bot Dev ToS, Content Creator ToS |
| KYC на Fragment | с 26.11.2024 обязательный KYC (Sumsub) для **покупок** (Stars, Premium, номера); для **вывода** вознаграждений не документирован — «проверить» | [press] PANews, 11.2024 — **старше 2025**; [forum] dev.to 24.05.2026: «not publicly documented» |
| Цифровые товары | внутри бота или мини-аппа — **только Stars** (требование Apple/Google); за сторонние платежи — предупреждение, затем удаление из сторовых версий | [official] Bot Dev ToS 6.2 |
| Возвраты | Apple может вернуть деньги покупателю в течение 21 дня — Stars списываются с баланса; оплата в TON невозвратна | [official] блог 01.07.2025 |
| Комиссии Telegram | темы в личных чатах бота — 15% со всех покупок; платная рассылка сверх 30 msg/s — 0.1 Star/сообщение | [official] Bot Dev ToS |
| Подписки ботов | период строго 30 дней, цена ≤ 10 000 Stars; события продления — с Bot API 10.2 (14.07.2026) | [official] Bot API, changelog |
| Платные сообщения / предложенные посты | получатель — 85% (`commission_permille = 850`); пост должен провисеть ≥ 24 ч; от 5 до 100 000 Stars или в TON | [official] config, Stars ToS, блог 01.07.2025 |
| Партнёрки (Affiliate Programs) | комиссию и срок задаёт владелец мини-аппа, снизить их нельзя; Stars аффилиата заморожены на 21 день; спам ссылками запрещён | [official] tos/affiliate-program; запуск — блог 04.12.2024 (**старше 2025**) |
| Реклама в каналах и ботах | 50% дохода от показов владельцу публичного канала от 1 000 подписчиков, «channel and bot owners» | [official] Content Creator ToS 2.1; core.telegram.org/api/revenue; блог 31.03.2024 (**старше 2025**) |
| Минимальный CPM Telegram Ads | 0.1 Toncoin/GRAM за 1 000 показов; ссылки только внутрь Telegram | [official] promote.telegram.org |
| Курс GRAM | **$1.47** (26.09.2026, ATH $8.25) → пол CPM $0.147, владельцу — **$0.074 за 1 000 показов** при минимальной ставке [оценка] | [provider data] CoinGecko API, 26.09.2026 |
| Bybit и GRAM | TON → GRAM: ввод и вывод приостановлены 15.06, возобновлены 22.06.2026; USDT в сети TON поддерживается с 04.2024 | [provider docs] Bybit announcement (по выдержке, страница отдала 503); USDT-TON — 2024, **старше 2025**, проверить в аккаунте |
| Adsgram (реклама в ботах, каналах, мини-аппах) | выплаты **USD₮ в сети TON**; от $10 раз в месяц (1–5 числа), от $100 — в любой день; «$4M+» выплачено | [provider docs] adsgram.ai/monetization, 26.09.2026 |
| Monetag (TMA SDK) | минимум $5 (PayPal/Skrill/WebMoney), $500 wire; средний CPM rewarded interstitial «от $2» | [provider docs] FAQ, обновлён 11.06.2026. Крипто-выплаты на странице не подтверждены |

**Расхождения:**
- **Сколько реально получает разработчик.**
  - [vendor] dev.to/starsearn (14.06.2026) и teleclaw: $0.0087–0.009 за Star при покупке с мобильного.
  - [vendor] starsfast: «комиссия Fragment ~5%».
  - [official] ToS: ставка $0.013 «has no connection… to the… purchase cost… in any particular region»; комиссии вывода в условиях Fragment нет.
  - Доверяем официальному тексту; ему же соответствует разбор adminhub (09.09.2026, со ссылками на config).
  - Реальные потери — только спред и комиссия биржи при продаже GRAM (нет данных; обычно доли процента — проверить на первом выводе).

**Цепочка вывода** [official + provider]: бот или канал → баланс Stars (холд 21 день) → fragment.com (логин Telegram + подключение TON-кошелька) → GRAM на свой Tonkeeper → депозит GRAM на Bybit → продать за USDT. Дальше — по решению владельца: держать USDT, тратить картой BingX или выводить в банк в пределах лимита 50 000 лей/мес.

### 1.2 Платформа 2025–2026: что изменилось (b)

| Дата | Изменение | Значение для нас |
|---|---|---|
| 07.03.2025 | Платные сообщения (Star Messages) | Монетизация личных сообщений; нам не подходит |
| 01.07.2025 | Предложенные посты за Stars/TON, канал получает 85% | Любой канал может продавать размещения без биржи |
| 31.07.2025 | Глобальный поиск по публичным постам (сначала только Premium) | Рождается «Telegram SEO» — нужны метрики, спроса не нашли |
| 03.01.2026 | Встроенные ИИ-сводки постов | Боты-суммаризаторы не нужны |
| 09.02.2026 | Крафт подарков (шансовая механика) | Экономика подарков похожа на азартную — исключение |
| 31.03.2026 | ИИ-редактор и перевод в поле ввода; скан документов (iOS); **Managed Bots** — боты создают ботов (Bot API 9.6, 03.04) | Боты-переводчики и «сканеры» не нужны; появился no-code конструктор ботов |
| 07.05.2026 | **Guest Mode** (бота можно позвать в любом чате через @), бот-бот, **Chat Automation для всех** (бот отвечает за пользователя), стриминг (Bot API 10.0) | Утилиты «по упоминанию» и автоответчики для личного профиля |
| 11.06.2026 | **AI guardians**: ботов-админов проверяют заявки на вступление через мини-апп (Join Request Queries, Bot API 10.1) | Новый рынок модерации групп |
| 14.07.2026 | Communities, эфемерные ответы ботов, события продления подписки (Bot API 10.2) | Проще продавать подписку в группах |
| 25.08.2026 | Встроенные приветствия; кнопки в тексте сообщений (Bot API 10.3) | Боты-приветствия не нужны |

Источники — официальный блог и changelog Bot API (раздел 5).

### 1.3 Масштаб и спрос: что известно (c)

- **Telegram в целом:**
  - >1 млрд MAU (март 2025) [press: TASS];
  - выручка за H1 2025 — $870 млн (+65%), цель на 2025 — $2 млрд [press: FT через Cointelegraph, 2025].
  - Сколько Stars выплачено разработчикам в сумме, публично не раскрыто — **нет данных**.
- **Трекер мини-аппов** (tgadsspy / tgstats, 4 760 ботов с main mini-app, данные 20–26.09.2026) [vendor]:
  - по числу: VPN 680, крипта 658, игры 647, боты 505, **gambling 368 + casino 266**, tech 284, education 97.
  - Реальный спрос на «чистые» утилиты:
    - @gpt4telegrambot (мульти-LLM) — 2.34 млн MAU;
    - @nanobananus_bot (генерация фото, RU) — 271 тыс.;
    - @PostBot — 3.32 млн;
    - @ChatKeeperBot — 527 тыс.;
    - Tribute (подписки) — 1.77 млн;
    - @stickers — 650 тыс.;
    - «Тесты и точка» — 89 тыс.;
    - «Решебник ГДЗ по фото» — 31 тыс.;
    - арабские образовательные боты — 110–270 тыс.
  - Поле «Stars rating» в анонимном API пустое → **выручку конкретных ботов в Stars проверить не удалось**.
  - У всех 4 758 мини-аппов флаг «sponsored-enabled» = 0: реклама Telegram в мини-аппах на практике не видна.
- **Публичные кейсы выручки в Stars за 2025–2026:**
  - нашли один честный пост: PolySignal, dev.to, 24.05.2026 [forum]. Тарифы 150 и 750 Stars/мес → $1.95 и $9.75 нетто; «вопрос в объёме»;
  - сам продукт — сигналы Polymarket, исключение проекта; берём только как данные о механике.
  - Остальные «кейсы» — калькуляторы продавцов без проверяемых цифр.
- **Реклама в мини-аппах:**
  - кейс Monetag: 155 тыс. MAU → $447.98 за ~месяц, CPM ~$5, это ≈ **$0.003 на MAU в месяц** [provider, 25.11.2024 — **старше 2025**; приложение было в стиле crash/mines, только как бенчмарк];
  - Adsgram заявляет «$4M+» выплат [provider].
- **Tap-to-earn обвалился:** Hamster Kombat — 300 → 41 млн пользователей за 3 месяца (−86%, 2024 — **старше 2025**) [press]; сейчас @hamster_fightclub_bot — 98 тыс. MAU [vendor 09.2026].

### 1.4 Рынки (d)

| Рынок | Факты | Вердикт |
|---|---|---|
| **РФ** | 10.02.2026 РКН подтвердил замедление (база). Массовая блокировка 14–15.03, в первые 10 дней апреля без VPN доступно ~5% соединений; VPN используют ≥40% [press: OSW 17.04.2026; Meduza 17.03.2026]. Дневной охват 40.25 млн (−49.4% за янв–май) [press: hi-tech.mail.ru 02.07.2026, данные «Родная речь»]. Время в приложении 44 → 34 мин/день (февраль → март) [press: Sostav/Mediascope]. Stars «официально купить почти невозможно», оплата с баланса телефона отключена с 04.2026, покупают через посредников по СБП [блог/forum: vc.ru, DTF 2026] | **Не таргетировать.** Покупатели заходят через серых посредников — это ловушка «обход платёжных блокировок» |
| **UA** | 81% используют Telegram для общения, 72% — для новостей (InMind для Internews Ukraine, май–август 2025, n=1 649) [press] | Лучший русско- и украиноязычный рынок. Владелец проверяет украинский только частично — нужен вычитчик или RU-интерфейс для тех, кому удобно |
| **MD/RO** | Telegram используют 12.8% молдаван (CBS-Research для WatchDog.MD, **2023 — старше 2025**) [press]. По Румынии — нет данных. Госзакупки MD уже закрыты: Notis.md шлёт фильтрованные уведомления MTender в Telegram [vendor, 26.09.2026]; сам MTender тоже рассылает уведомления | Рынок мал, B2B-ниша занята. Только как тестовый рынок с полным QA |
| **EN (глобальный)** | Самая сильная конкуренция: ИИ-агрегаторы — миллионы MAU | Только узкие функции или B2B |
| **Индия** | 45% респондентов пользуются Telegram (опрос Statista через demandsage, дата неизвестна) [vendor]; 104 млн загрузок в 2025 [vendor]. Stars продаются через Google Play с UPI [vendor]. **16–22.06.2026 MeitY заблокировало Telegram по ст. 69A IT Act** перед пересдачей NEET-UG: через каналы и **боты** шли утечки [press/vendor-блоги; первичный приказ не прочитан — проверить] | Объём есть, платёжеспособность низкая. **Образовательные и экзаменационные боты — регуляторная ловушка** |
| **Бразилия** | 38% опрошенных пользуются Telegram (Statista через demandsage) [vendor]; в топ-5 по загрузкам 2026 [vendor: RichAds 10.09.2026] | Португальский владелец не проверяет. Только флот плюс внешний вычитчик |
| **Турция** | Нет данных (надёжных цифр 2025–2026 не нашли) | — |
| **Арабский мир** | Египет — >40 млн пользователей [vendor, hackmd 2026]; арабские образовательные боты — 110–270 тыс. MAU [vendor-трекер] | Спрос есть, QA нет. Рекламная модель, низкий ARPU |
| **Африка** | Монетизируется в основном рекламой: гео Нигерия, Алжир, Эфиопия в кейсе Monetag (2024 — **старше 2025**) | Только реклама, ARPU ≈ $0.003/MAU [оценка по кейсу] |
| **Иран/фарси** | Bybit исключает Иран в Service Agreement, проверка по OFAC/ЕС/UK/ООН [vendor: datawallet 2026 — сверить со страницей Bybit] | **Санкционная ловушка** — не делать |

### 1.5 Гранты TON (e)
- Репозиторий `ton-society/grants-and-bounties` **заархивирован**: последний push 20.05.2026, `archived: true` [official: GitHub API, 26.09.2026].
- «Champion Grants»: вертикали — GameFi, Payments, Telegram In-App Economy, DeFi, AI; суммы публично не указаны [press/vendor, дата неизвестна]. Страница ton.org/en/ton-grants рендерится скриптом — программу не прочитали.
- Гранты на миграцию мини-аппов — рекламные кредиты $100–10 000 при 10 тыс.–1 млн пользователей [vendor, дата неизвестна]. Деньгами не платят, нужна аудитория.
- Хакатоны TON с призами $1–6 млн — 2024–2025 гг. (**старше или на границе**); открытого конкурса в 2026 не нашли.
- Вывод: грантами первый доход не закрыть.

### 1.6 Налоги и IT Park (кратко, база)
- Stars и GRAM приходят на личный аккаунт → это доход физлица. Global Web SRL крипту не получает (`crypto_rails_2026.md` 3.4).
- Если TG-01 оплачивается банковским переводом на SRL — это, вероятно, разработка ПО (62.01), IT-доход → 7% (к MITP/бухгалтеру).
- Stars-выручка бота — «вероятно IT, если продаётся бот или мини-апп», но документы для аудита IT Park проблемны (`it_park_verified.md`).

---

## 2. Кандидаты

Все p, сроки и потолки — [оценка]. p — вероятность получить деньги на свой кошелёк за 30 дней (допущение 2). Потолок — через 6 месяцев, до налогов.

### 2.1 Таблица A — продукт и доказательства

| ID | Ниша (формат × тема × рынок) | Что продаём | Монетизация | Рельс | Крипто | Доказательства спроса (2025–2026) | Конкуренция |
|---|---|---|---|---|---|---|---|
| TG-01 | B2B-услуга × разработка ботов и мини-аппов (Stars-подписки, guest mode, guardian, managed bots) × крипто-нативные заказчики, EN письменно | Проекты под ключ $300–1 500 + поддержка | Фикс-цена по этапам, предоплата | Прямой инвойс USDT/USDC (TON/TRC-20) на свой Bybit; Contra (USDC, Молдова «YES» — база crypto_rails); фиат — Upwork или SRL | yes | Медиана зарплаты «Telegram bots & mini-apps» $5 638/мес [vendor: Upstaff 2026]; 5 новых API за 2026 [official]; проект «Telegram mini-app» на Freelancehunt 27.05.2026 [provider, по выдержке]. Числа вакансий по TMA — **нет данных** (Upwork 403) | Очень высокая: от $10/ч на Upwork; СНГ — $100–400 за проект [vendor: arc.dev, kolodych 2026]. На Freelancer.com из 5 вакансий «Telegram API» 3 серые [provider data 26.09.2026] |
| TG-02 | Бот × AI guardian (проверка заявок + антиспам) × админы групп EN/ES/UA | Freemium-бот; Pro-подписка на группу | 250 Stars/мес за группу | Stars → Fragment → GRAM → Bybit | yes | Join Request Queries, AI guardians — 11.06.2026 [official]; ChatKeeperBot 527 тыс. MAU [vendor-трекер]; в 2026 вышли десятки обзоров антиспам-ботов [vendor] | Высокая: Rose бесплатно, Group Help Pro 150 Stars разово за 5 групп, ChatKeeper $4.99–39.99, Telm $29/мес [vendor: telm.com 08.08.2026] |
| TG-03 | Бот × автоответчик для личного профиля (Chat Automation + Managed Bots) × фрилансеры и мелкие продавцы UA/EN/ES | Свой ИИ-бот за 2 минуты: FAQ, прайс, запись | 400 Stars/мес | Stars → Fragment | yes | Chat Automation для всех — 07.05.2026; Managed Bots — 03.04.2026 [official]; настройка ИИ-ботов для бизнеса «от $290» [vendor: optimum-web 2026] | Средне-высокая, рынок новый: no-code конструкторы, агентства |
| TG-04 | Бот × фото на паспорт/визу/ID × EN/UA/TR/IN (по спецификациям стран) | Готовое фото по стандарту страны | 75 Stars за фото | Stars → Fragment | yes | Бот Qsbot продаёт то же за Stars [vendor]; много ИИ-приложений «passport photo» в App Store [vendor]. Объёмы — **нет данных** | Средняя: Qsbot, приложения, фотосалоны |
| TG-05 | Бот (guest mode) × экспресс-аудит сайта (SEO, CWV, a11y) × вебмастера UA/KZ/MD/RO, интерфейс RU/RO/UA | Бесплатный снимок + платный глубокий отчёт | 100 Stars за отчёт | Stars → Fragment | yes | Guest mode — 08.05.2026 [official]; спрос — **нет данных** (так же в CR-04) | Высокая: бесплатные PageSpeed Insights и SEO-сервисы |
| TG-06 | Мини-апп × инструменты админа канала (ИИ-черновики в стиле канала, расписание, учёт предложенных постов) × малые каналы UA/EN | Подписка | 200 Stars/мес | Stars → Fragment | yes | PostBot — 3.32 млн MAU (бесплатный) [vendor-трекер]; предложенные посты с 01.07.2025 [official]; UA — 72% читают новости в Telegram [press] | Высокая: PostBot, TGStat, Metricgram, adminhub (0% комиссии) [vendor] |
| TG-07 | Канал × безликий дайджест («AI coding tools» EN; «ИИ-инструменты и удалёнка» UA) × EN/UA | Контент канала | Реклама 50% (GRAM) + предложенные посты 85% + Adsgram для каналов (USDT) | Fragment; Adsgram USDT-TON | yes | 50% от 1 000 подписчиков, пол CPM 0.1 GRAM [official]; GRAM $1.47 [CoinGecko] | Высокая; рост платный: 0.1–0.3 TON за подписчика через Telegram Ads [vendor: adminhub 2026] |
| TG-08 | Бесплатный утилитарный бот × PDF и документы (сжатие, склейка, конвертация) × EN/IN/PT | Бесплатная утилита | Adsgram-реклама в боте | Adsgram → USDT-TON | yes | Adsgram — от $10, «$4M+» выплат [provider]; ≈$0.003/MAU/мес по кейсу Monetag (2024) | Высокая; встроенный скан документов в iOS с 03.2026 [official] |
| TG-09 | Платный Stars-канал × проверенный дайджест грантов, баунти и хакатонов для Web3-разработчиков × EN | Еженедельный список: суммы, дедлайны, ссылки на первоисточник | Подписка 250 Stars/мес + бесплатный тизер | Stars → Fragment | yes | Superteam Earn: 606 закрытых листингов ≈ $1.99 млн за 12 мес [provider data, база crypto_rails]; репозиторий грантов TON закрыт [official] | Средняя: бесплатные каналы CryptoJobsList, Superteam |
| TG-10 | Канал или бот × каталог мини-аппов с партнёрскими ссылками × EN/IN | Подборки полезных мини-аппов | Комиссия по Affiliate Programs (Stars) | Stars → Fragment | yes | Механика — [official]; типичные ставки 10–30% [vendor]. Список активных программ и заработки — **нет данных** | Высокая, спам-риск |
| TG-11 | Мини-апп × казуальная головоломка без токенов × EN/глобально | Игра | Stars за подсказки и жизни + rewarded-реклама Adsgram | Stars; Adsgram USDT | yes | Игр в трекере 647, в топе — крипто- и азартные [vendor]; tap-to-earn −86% (2024) [press] | Очень высокая |
| TG-12 | Грант или хакатон TON × мини-апп, сделанный флотом × глобально | Заявка или хакатон-проект | Разовый приз или грант | GRAM/USDT | yes | Репозиторий грантов заархивирован 20.05.2026 [official]; суммы Champion Grants не опубликованы | Высокая, непрозрачно |
| TG-13 | Бот × ИИ-редактор фото (замена фона, ретушь предметов для объявлений, стилизация) × UA/EN | Генерации поштучно | 10 Stars за изображение, пакеты | Stars → Fragment | yes | @nanobananus_bot — 271 тыс. MAU, @gpt4telegrambot — 2.34 млн [vendor-трекер]; себестоимость $0.039 за картинку (Gemini 2.5 Flash Image; модель отключат 02.10.2026, переход на 3.x) [provider docs] | Очень высокая |

### 2.2 Таблица B — исполнение и экономика

| ID | Флот без лица и GPU | Тест на 14 дней (самый дешёвый) | Дней до $ | Потолок через 6 мес [оценка] | Формула | p (30 дн) | Ч/нед владельца | Главные риски |
|---|---|---|---|---|---|---|---|---|
| TG-01 | Да: код, тесты, деплой, документация; владелец — переписка и приёмка | Флот делает 3 open-source демо (guest-mode бот, guardian, бот со Stars-подпиской) + страницу с 3 пакетами; профиль на Contra; 10 откликов только на подходящие запросы | 21 | **$1 800** | 2 проекта × $700 + 4 клиента на поддержке × $100 | 0.2 | 8 | Скам-заказчики (сигналы, казино, airdrop) — отсеивать; только предоплата по этапам; USDT → банк — лимит 50 000 лей |
| TG-02 | Да: бот + LLM-проверка через API | Бот с бесплатным тарифом до 200 участников, Pro — 250 Stars; 20–30 GRAM на Telegram Ads по каналам для админов | 45 | **$360** | 120 групп × 250 Stars × $0.013 = $390 − LLM ≈ $30 | 0.05 | 3 | Ложные баны; конкуренты добавят ИИ; Rose бесплатный |
| TG-03 | Да | Manager-бот + шаблоны FAQ на UA/EN, 400 Stars/мес, 7 дней бесплатно | 50 | **$350** | 80 подписок × 400 Stars × $0.013 = $416 − LLM ≈ $64 | 0.04 | 3 | Бот читает личные переписки: запрет передачи третьим лицам без согласия (Bot Dev ToS 5.4) → нужно явное согласие на LLM-API; раскрытие ИИ (ст. 50 AI Act) |
| TG-04 | Да: удаление фона и проверка лица на CPU | Бот на 10 спецификаций стран, 75 Stars за фото; Telegram Ads 20 GRAM | 40 | **$470** | 500 фото × 75 Stars × $0.013 = $488 − сервер ≈ $20 | 0.05 | 2 | Биометрия — удалять за 24 ч, политика приватности; отказ консульства — нужен возврат Stars |
| TG-05 | Да: общий код с Apify-актерами | Бот RU/RO/UA; 5 бесплатных снимков, отчёт — 100 Stars; посевы в своих каналах | 45 | **$195** | 150 отчётов × 100 Stars × $0.013 (как CR-04) | 0.03 | 2 | Спроса не видно; бесплатные аналоги |
| TG-06 | Да | Мини-апп MVP (черновики + расписание), 200 Stars/мес; 10 бета-каналов | 50 | **$360** | 150 × 200 Stars × $0.013 = $390 − LLM ≈ $30 | 0.03 | 3 | Конкуренция с бесплатным; для постинга нужны права админа — доверие |
| TG-07 | Да (тексты флота, QA RU/RO владельцем; UA/EN — частично) | 2 канала × 30 постов; кросс-промо; платной накрутки нет | 90+ | **$80** | 2 × 150 000 просмотров × $0.074/1 000 ≈ $22 + предложенные посты ≈ $22 + Adsgram ≈ $30 | 0.01 | 1.5 | До 1 000 подписчиков дохода нет; реальный CPM неизвестен |
| TG-08 | Да | Бот PDF-утилит + Adsgram | 60 | **$120** | 40 000 MAU × $0.003 | 0.02 | 1 | Встроенные функции Telegram; ARPU мизерный |
| TG-09 | Да: флот уже сканирует Superteam (CR-01) | Бесплатный тизер-канал + платный Stars-канал по invite-ссылке с подпиской | 45 | **$260** | 80 подписчиков × 250 Stars × $0.013 | 0.03 | 1 | Ошибки в суммах и дедлайнах → проверять по первоисточнику; платный контент пересылают |
| TG-10 | Да | Канал с 20 подборками | 60+ | **$80** | 300 платящих рефералов × 150 Stars × 15% × $0.013 ≈ $88 | 0.02 | 1 | Нет данных о программах; риск спама |
| TG-11 | Да (2D, без GPU) | Прототип + Adsgram rewarded + 3 товара за Stars | 60+ | **$230** | 8 000 MAU × 1% × 200 Stars × $0.013 ≈ $208 + реклама 8 000 × $0.003 ≈ $24 | 0.02 | 2 | Привлечение пользователей дорогое, соседство с азартными |
| TG-12 | Да | Заявка на Champion Grant или ближайший хакатон | 90+ | **$0** (разово, сумма — нет данных) | нет данных | 0.01 | 2 | Программы закрыты или непрозрачны |
| TG-13 | Да: генерация через API | Бот UA/EN, 10 Stars за картинку, пакеты по 100; фильтры NSFW и лиц | 40 | **$273** | 3 000 изображений × 10 Stars × $0.013 = $390 − API 3 000 × $0.039 = $117 | 0.05 | 2 | Дипфейки и NSFW → строгие фильтры; маркировка синтетики (ст. 50 AI Act); цены API меняются |

### 2.3 Рейтинг и обоснование [оценка]
1. **TG-01** — единственный Telegram-кандидат с реальным шансом на деньги в течение 30 дней:
   - оплата в USDT без холда;
   - флот делает 80% работы;
   - через Upwork или SRL тот же навык даёт IT-доход по 7%.
   Слабое место — в каких каналах найти заказчиков без холодного спама. Нужны Contra, профильные чаты по их правилам, открытые демо.
2. **TG-02, TG-13, TG-04** — портфель Stars-ботов на общем каркасе: оплата, подписки, `/paysupport`, возвраты, аналитика. Каждый даёт меньше $500/мес, вместе — $1 000+ [оценка: 360 + 273 + 470 ≈ $1 100].
   Stars выгоднее реинвестировать в Telegram Ads по $0.02, чем выводить по $0.013.
3. **TG-03, TG-06** — новые API 2026, спрос не доказан. Второй эшелон.
4. **TG-09, TG-05** — дёшево, синергия с уже запланированными потоками (Superteam, Apify), но спроса не видно.
5. **TG-07, TG-08, TG-10, TG-11, TG-12** — потолок ниже $250 или тупик. Держать только как побочный продукт.

---

## 3. Ловушки и тупики (с доказательствами)

1. **Таргетинг РФ.**
   - Блокировка весной 2026 (~5% доступности без VPN в начале апреля) [press: OSW].
   - Stars из РФ покупают через посредников по СБП [blog: vc.ru 2026] — это обход платёжных блокировок, исключение проекта.
   - Сюда же **боты-перепродавцы Stars или Premium** для РФ.
2. **Иран и фарси.** Санкции OFAC/ЕС; Bybit исключает Иран [vendor, сверить со страницей Bybit] → риск заморозки средств.
3. **«Кейсы», «рулетки», крафт подарков, crash/mines-игры.**
   - В трекере 368 gambling + 266 casino мини-аппов;
   - в топе по MAU — боты-кейсы @gorillacasebot, @frogcasebot [vendor];
   - крафт подарков работает на шансах [official 09.02.2026].
   Это азартная механика — исключение.
4. **Tap-to-earn и airdrop-мини-аппы.** Hamster −86% за 3 месяца (2024) [press]; работают на токенах-обещаниях.
5. **VPN-боты** (680 в трекере) — обход блокировок РФ и Ирана. **Загрузчики и музыка** (TikTok Downloader — 3.48 млн MAU) — чужой контент и ToS. Всё исключения.
6. **Экзаменационные боты в Индии.** Блокировка Telegram MeitY 16–22.06.2026 из-за утечек NEET через каналы и боты [press/blog].
7. **Общие биржи фриланса по запросу «Telegram».** Freelancer.com, 26.09.2026: 5 вакансий, из них сигналы Quotex, «найти пользователя по нику», «VPS redirect for identity verification» (обход KYC) [provider data]. Брать только проверяемых заказчиков.
8. **Боты, которые повторяют встроенные функции**: ИИ-сводки, ИИ-редактор и перевод, скан документов, приветствия, опросы — с 01–08.2026 всё это есть в самом Telegram [official].
9. **Считать по цене покупателя.** $19.99 за 1 000 в сторе против $13 при выводе — завышение на 35% [official config + vendor adminhub].
10. **Оплата цифровых товаров мимо Stars внутри бота** — предупреждение, затем удаление из сторовых версий [official ToS 6.2].
11. **Возвраты:** Apple возвращает деньги до 21 дня, Stars списываются [official]. Товары, которые нельзя «отозвать» после чарджбэка, Telegram прямо не рекомендует продавать [official ToS 6.2.1].
12. **Темы в личных чатах бота** — 15% со всех покупок, пока функция включена [official].
13. **Гранты TON как план дохода** — репозиторий заархивирован 20.05.2026 [official GitHub API].
14. **Уведомления о госзакупках Молдовы в Telegram** — рынок занят Notis.md, у MTender свои бесплатные уведомления [vendor/official]. Ставить только с другой ценностью (аналитика, а у Notis «Tender Intelligence» уже «în curând»).
15. **Платный контент по Stars не защищён от пересылки** — «cannot completely eliminate the risk» [official Content Creator ToS 2.2.1]. Продавать только то, что устаревает (дайджесты, алерты).

---

## 4. Что не удалось проверить

- Выдаёт ли Fragment вознаграждения резидентам Молдовы и нужен ли KYC (Sumsub) для **вывода**. Официально: «may be unable… in certain countries», списка нет. Проверить первым выводом 1 000 Stars.
- Платит ли Fragment кому-то стейблкоинами («in some countries») и в каких странах.
- Выручка конкретных ботов в Stars: «Stars rating» в анонимном API трекера пустой; публичных раскрытий 2025–2026 не нашли.
- Реальные клиринговые CPM Telegram Ads по странам и темам: только пол 0.1 GRAM.
- Работает ли реклама Telegram в ботах и мини-аппах: в официальных документах «channel and bot owners», но у 4 758 мини-аппов в трекере флаг sponsored = 0.
- Число вакансий по TMA на Upwork (403) и Freelancehunt (403).
- Доля Telegram в Молдове (есть только 2023), Румынии и Турции за 2025–2026.
- Первичный приказ MeitY о блокировке в Индии (есть только блоги и пресса) и текущее состояние доступа в РФ на 09.2026.
- Страница Bybit о GRAM отдала 503 — даты взяты из поисковой выдержки. Поддержку USDT-TON и спот-пары GRAM/USDT проверить в аккаунте.
- Текущие условия Champion Grants TON: страница рендерится скриптом.
- Monetag: есть ли выплаты в USDT (на странице FAQ — только PayPal, Skrill, WebMoney, wire).
- Как квалифицировать для IT Park и налогов доход физлица в Stars и GRAM (база — к бухгалтеру).

---

## 5. Источники (прочитано 26.09.2026, если не указано иное)

**Official (Telegram, Fragment, госисточники, GitHub):**
- Telegram Bot Platform Developer ToS (6.2, 6.2.3–6.2.5, темы 15%, 3 года) — https://telegram.org/tos/bot-developers
- Terms of Service for Content Creators (50%, платные посты $0.013, холд Gram 2 дня / Stars 21 день, Fragment и страны) — https://telegram.org/tos/content-creator-rewards
- Terms of Service for Affiliate Programs — https://telegram.org/tos/affiliate-program ; запуск: блог 04.12.2024 (**старше 2025**) — https://telegram.org/blog/affiliate-programs-ai-sticker-search
- Telegram Stars ToS (платные сообщения 85%, региональные ограничения) — https://telegram.org/tos/stars
- Fragment Terms (GRAM по умолчанию, стейблкоины в некоторых странах, курс CoinMarketCap) — https://fragment.com/terms
- Конфигурация клиента (min/max вывода, курсы, 85% за предложенные посты) — https://core.telegram.org/api/config
- Stars для цифровых товаров — https://core.telegram.org/bots/payments-stars
- Bot API (подписка 30 дней, ≤10 000 Stars) — https://core.telegram.org/bots/api ; changelog (9.6 от 03.04.2026 — Managed Bots; 10.0 от 08.05.2026 — Guest Mode; 10.1 от 11.06.2026 — Join Request Queries; 10.2 от 14.07.2026 — эфемерные сообщения и события подписки; 10.3 от 24.08.2026) — https://core.telegram.org/bots/api-changelog
- Доход каналов и ботов от рекламы — https://core.telegram.org/api/revenue
- Telegram Ad Platform (min CPM 0.1 TON, 1 000+ подписчиков) — https://promote.telegram.org/getting-started
- Блог Telegram:
  - монетизация каналов, 31.03.2024 (**старше 2025**) — https://telegram.org/blog/monetization-for-channels
  - Star Messages, 07.03.2025 — https://telegram.org/blog/star-messages-gateway-2-0-and-more
  - предложенные посты, 01.07.2025 — https://telegram.org/blog/checklists-suggested-posts
  - поиск по постам, 31.07.2025 — https://telegram.org/blog/post-search-story-albums-and-more
  - ИИ-сводки, 03.01.2026 — https://telegram.org/blog/new-design-ai-summaries
  - крафт подарков, 09.02.2026 — https://telegram.org/blog/crafting-android-design-and-more
  - ИИ-редактор и Managed Bots, 31.03.2026 — https://telegram.org/blog/ai-editor-mighty-polls-and-more
  - Guest bots и Chat Automation, 07.05.2026 — https://telegram.org/blog/ai-bot-revolution-11-new-features
  - AI guardians, 11.06.2026 — https://telegram.org/blog/watch-apps-and-more
  - Communities и эфемерные сообщения, 14.07.2026 — https://telegram.org/blog/communities-editor-invisible-messages
  - приветствия и кнопки, 25.08.2026 — https://telegram.org/blog/welcome-messages-buttons-TG-13
- GitHub API, `ton-society/grants-and-bounties`: archived, pushed 20.05.2026 — https://github.com/ton-society/grants-and-bounties

**Provider docs / provider data:**
- CoinGecko API, Gram (prev. Toncoin) $1.47, 26.09.2026 — https://api.coingecko.com/api/v3/coins/the-open-network
- Bybit, TON → GRAM (по выдержке; страница 503) — https://announcements.bybit.com/en/article/bybit-to-support-toncoin-ton-rebrand-and-ticker-change-to-gram-gram--blt617f4bf48950ab77/
- Bybit, USDT в сети TON (2024, **старше 2025**) — https://www.coincarp.com/exchange/announcement/bybitbybit-to-support-usdt-on-ton-blockchain-blt7bbc02/
- Adsgram, монетизация — https://adsgram.ai/monetization
- Monetag, FAQ по TMA (обновлён 11.06.2026) — https://monetag.com/blog/telegram-mini-app-monetization-faq/ ; кейс 25.11.2024 (**старше 2025**) — https://monetag.com/blog/turning-traffic-into-50-a-day-a-telegram-mini-app-success-story/
- Google, цены Gemini API ($0.039 за картинку; отключение 2.5 Flash Image 02.10.2026, по выдержке) — https://ai.google.dev/gemini-api/docs/pricing
- Freelancer.com, «Telegram API Jobs», 26.09.2026 — https://www.freelancer.com/jobs/telegram-api/

**Press:**
- OSW, «Russia blocks Telegram and cracks down on VPNs», 17.04.2026 — https://www.osw.waw.pl/en/publikacje/analyses/2026-04-17/russia-blocks-telegram-and-cracks-down-vpns
- Meduza, 17.03.2026 — https://meduza.io/en/feature/2026/03/17/russia-was-expected-to-block-telegram-in-april-it-appears-to-have-done-it-two-weeks-early
- Hi-Tech Mail, 02.07.2026 — https://hi-tech.mail.ru/news/150565-ohvaty-telegram-v-rossii-upali-pochti-na-50/
- Sostav (Mediascope, март 2026) — https://www.sostav.ru/publication/polzovateli-telegram-v-rossii-sokratili-vremya-ispolzovaniya-v-marte-83018.html
- Internews Ukraine, медиапотребление 2025 — https://internews.ua/en/opportunity/media_trust_consumption_2025_release
- FT через Cointelegraph/TradingView, H1 2025 — https://www.tradingview.com/news/cointelegraph:01e9ad089094b:0-telegram-revenue-jumps-to-870m-in-h1-2025-2b-full-year-target-ft/
- TASS, 1 млрд MAU (03.2025) — https://tass.com/economy/1930999
- PANews, KYC на Fragment (11.2024, **старше 2025**) — https://www.panewslab.com/en/articles/uwm04yl8
- Protos, Hamster Kombat (2024, **старше 2025**) — https://protos.com/hamster-kombat-loses-nearly-260-million-players-in-just-three-months/
- Bancamea, госзакупки MD 2025 — https://bancamea.md/news/record-al-achizitiilor-publice-din-ultimul-deceniu-173-miliarde-de-lei-cheltuite-in-2025
- #diez, соцсети Молдовы (2023, **старше 2025**) — https://diez.md/2023/04/24/sondaj-tiktok-telegram-si-youtube-ce-retele-de-socializare-folosesc-cel-mai-des-moldovenii/
- Блокировка в Индии, июнь 2026 (блоги, первичный приказ не прочитан) — https://brilliantpala.org/blog/telegram-blocked-india-neet-ug/ ; https://academycheck.com/blog/telegram-ban-india-neet-ug-2026-restrictions

**Vendor / forum:**
- tgstats.org / tgadsspy.com, рейтинг мини-аппов и API (CC-BY-4.0), 20–26.09.2026 — https://tgstats.org/miniapps ; https://tgadsspy.com/api/v1/miniapps
- adminhub.tools, вывод Stars (проверено 09.09.2026) — https://adminhub.tools/blog/withdraw-telegram-stars/ ; стоимость Telegram Ads — https://adminhub.tools/blog/telegram-ads-cost/
- StarsFast, «5% комиссия» (дата не указана; противоречит official) — https://starsfast.com/en/blog/withdraw-telegram-stars-ton-fragment-guide
- dev.to/starsearn, 14.06.2026 — https://dev.to/starsearn/telegram-stars-economics-for-bot-developers-what-your-stars-are-actually-worth-in-2026-2742
- dev.to, PolySignal, 24.05.2026 [forum] — https://dev.to/__747bb5a1521/i-built-a-paid-telegram-bot-heres-what-telegram-stars-actually-pay-3fo
- Telm, антиспам-боты, 08.08.2026 — https://telm.com/blog/best-telegram-anti-spam-bots
- Metricgram, 17.03.2026 — https://metricgram.com/blog/telegram-group-management-tools-compared
- Qsbot (дата не указана) — https://qsbot.app/en
- Optimum Web, ИИ-бот для бизнеса 2026 — https://www.optimum-web.com/blog/telegram-ai-bot-for-business-2026/
- Upstaff, зарплаты 2026 — https://upstaff.com/salaries/telegram-bots-and-mini-apps/
- Kolodych, цены СНГ 2026 — https://kolodych.com/services/telegram-bot-developer
- Notis.md — https://notis.md/
- Demandsage (опрос Statista: Индия 45%, Бразилия 38%; дата опроса неизвестна) — https://www.demandsage.com/telegram-statistics/
- RichAds, статистика Telegram, обновлено 10.09.2026 — https://richads.com/blog/telegram-statistics/
- Datawallet, ограничения Bybit 2026 — https://www.datawallet.com/crypto/bybit-restricted-countries
- vc.ru, покупка Stars в РФ 2026 [blog] — https://vc.ru/money/3043269-kak-kupit-zvezdy-v-telegram-v-rossii

CSV с кандидатами: `notes/telegram_2026.csv`.

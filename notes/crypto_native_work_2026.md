# Крипто-нативная работа 2026: хакатоны, баунти, гранты, аудит-конкурсы, Web3-услуги с оплатой в стейблкоинах

Дата: 26.09.2026. Поток «crypto-native work» мастер-плана.
Только исследование: аккаунты не создавались, формы не отправлялись, ничего не покупалось. Публичные API (Colosseum Agents, Superteam Earn, пагинация витрины ETHGlobal) читались без регистрации.
Это исследование, а не юридическая или налоговая консультация.

**Метки:** [official] — закон, госорган; [provider docs] — правила или справка самой платформы; [provider data] — выгрузка из публичного API или страницы платформы, посчитанная нами; [press]; [vendor] — блог, агрегатор, джоб-борд; [forum]; [интерпретация]; [оценка] — с формулой.

**База проекта (не перепроверялась):** `STATUS.md` 2.5 и `notes/crypto_rails_2026.md` — Superteam Earn (USDC/USDG, Молдове доступны только Global-листинги, агентный API, CR-01), Sherlock (USDC, ≥2 валидных находки и ratio ≥20%), Immunefi (KYC от $500), Code4rena закрыт 13.05.2026, Contra платит USDC в Молдову (2%/1%), Web3-SEO (CR-02), x402 (CR-03), OSS-гранты (CR-05), аудит-конкурсы (CR-06), видео-баунти (CR-07); `notes/telegram_2026.md` — TON grants-and-bounties заархивирован 20.05.2026, TG-01 (боты для крипто-заказчиков), TG-12; крипто-доход получает физлицо, SRL крипту не получает (закон 62/2008); лимит вывода в банк — 50 000 лей/мес; закон о криптоактивах вступает в силу 17.03.2027 (ст. 55 — reverse solicitation).

**Допущения по умолчанию (вопросы не задавались):**
1. Получатель — физлицо-владелец (свой KYC, свой кошелёк → Bybit/BingX). Налоги — после первого дохода (решение 26.09).
2. Один аккаунт на платформе — на имя владельца; флот работает «под ним», владелец читает и понимает всё, что отправляется (этого требуют правила почти всех платформ, раздел 1.7).
3. Английский — только письменно; живые питчи и звонки — нет. Видео-демо — с TTS-озвучкой (проверить, принимают ли судьи).

---

## TL;DR

1. **Главный вывод: крипто-нативная «призовая» работа — лотерея с низким матожиданием и долгим сроком до денег.** Реальные доли призовых мест по данным самих платформ: Colosseum Frontier — 28 призов на 2 857 проектов (≈1%); Colosseum Agent Hackathon — 4 приза на 454 проекта (≈0.9%); ETHOnline 2026 — ~52 призовых места на 837 проектов (≈6%, средний приз ≈ $1 200); DoraHacks-хакатоны спонсоров — 3–5 мест на 190–237 проектов (1.3–2.6%) [provider data, 26.09.2026; расчёт — наш]. Деньги по хакатонам приходят через 30–75+ дней после старта. **Ни один хакатон не даёт первый доллар за 30 дней.**
2. **Индустрия закручивает гайки против ИИ-заявок** — это прямо бьёт по модели «флот шлёт много»: Immunefi банит за ИИ-отчёты [provider docs]; Cantina помечает ИИ-находки как Spam с последствиями для репутации и депозита [provider docs]; Drips Wave запрещает непроверенный LLM-код и больше одного аккаунта на человека [provider docs]; HackenProof ввёл платные подачи и пороги репутации [provider docs]; curl закрыл баг-баунти 31.01.2026 из-за «AI slop» (доля подтверждённых упала с >15% до <5% в 2025) [press: блог автора]; OnlyDust закрылся, потому что мейнтейнеры перестали принимать ИИ-вклады [provider]. ETHGlobal требует раскрывать использование ИИ и не принимает проекты, целиком сделанные ИИ, на партнёрские призы [provider docs].
3. **Лучшие кандидаты этого потока — не призы, а оплачиваемая работа для Web3-компаний в USDC** (уточнение CR-02 из базы):
   - **CN-06** — технический SEO/GEO для Web3-инфраструктуры без токенов (dev-tools, SDK, RPC, стейблкоин-платежи B2B), оплата USDC через Contra или прямой инвойс;
   - **CN-07** — docs-as-code и DevRel-контент (туториалы, sample-репозитории, SEO документации, llms.txt) для Web3 dev-tools.
   Спрос есть, но уже, чем казалось: на web3.career 71 SEO-вакансия, 68 — технический писатель, 225 — DevRel (сентябрь 2026) [vendor]; в SEO почти все — full-time в биржах (Binance, Bitpanda, Kraken, Crypto.com), объявлениям 2–11 месяцев.
4. **Единственная регулярная программа с «зарплатным» ритмом — Drips Wave (Stellar), CN-01:** 7-дневный спринт каждый месяц, пул $75 000, выплата USDC в сети Stellar, KYC обязателен, санкционные страны исключены (Молдова — нет) [provider docs/data, 26.09.2026]. В первой волне ~600 участников закрыли >3 000 PR при пуле $60 000 → в среднем ≈ $100 на участника [provider, 16.02.2026; расчёт наш].
5. **Сейчас открыт Colosseum Crypto World's Fair (CN-02):** 14.09–12.10.2026, $840 000 призов в стейблкоине CASH/USD, 83 призовых места, Молдовы нет в списке исключений [provider docs: официальные правила]. Но победителей объявят к 05.12.2026 — это не «быстрые деньги». Смысл — только если флот переиспользует готовый актив (x402-API или SEO-actor из других потоков) и владелец тратит ≤10 ч.
6. **Тупики:** RO/RU-локализация за крипто-баунти (на Superteam последние переводческие баунти — $30–35 в 2023–2024; на web3.career из 31 вакансии переводчика одна с русским, ни одной с румынским) [provider data; vendor]; Algora, Opire, IssueHunt — не крипта или без эскроу; Replit Bounties больше нет (редирект на Contra); гранты Arbitrum DAO завершены, у Base — только венчурный фонд, страница грантов TON исчезла [provider].
7. **Рекомендация:** CN-06 и CN-07 — как Web3-ветка ниши №1 (тот же навык, другой рельс оплаты). CN-01 (Drips Wave) — одна волна как тест в октябре. Хакатоны — максимум один (CN-02) и только на готовом активе. Аудит-конкурсы, баг-баунти смарт-контрактов, агентные хакатоны, RO/RU-локализация — не сейчас.

---

## 1. Что установлено

### 1.1 Хакатоны

| Платформа | Частота 2025–2026 | Призы | Правило об ИИ | Допуск / KYC | Выплата | Доля призовых мест |
|---|---|---|---|---|---|---|
| **ETHGlobal, онлайн (async)** | 3 за 12 мес.: ETHOnline 2025 (10–31.10.2025), HackMoney 2026 (30.01–11.02.2026), ETHOnline 2026 (04–16.09.2026) [provider] | $100k / $75k / $100k; партнёрские призы $200–2 500 за место [provider] | «AI tools… generally permitted», нужно документировать, где и как использован ИИ; «should be used to assist… not to create the entire project»; проекты целиком на ИИ могут не получить партнёрские призы и финал [provider docs: страница правил событий 2026] | Нужен **стейк криптой** для подтверждения места, возвращается при сдаче проекта [provider docs: ethglobal.com/rules]. KYC и страны на странице правил не указаны — нет данных | Финалистам — 1 000 USDC на участника «to their verified wallets» (ETHOnline 2025) [provider]; партнёрские призы — порядок выплаты нет данных | ETHOnline 2026: ~52 места (29 «1st/2nd/3rd» + 23 «up to N teams») на 837 проектов ≈ **6.2%**; ETHOnline 2025: ≥41 место на 652 ≈ 6.3%; HackMoney 2026 — 639 проектов [provider data: витрина, 33 проекта на страницу; расчёт наш] |
| **ETHGlobal, офлайн** | Cannes 03–05.04, NY 12–14.06, Lisbon 24–26.07, Tokyo 25–27.09, Mumbai 06–08.11.2026 [provider: X ETHGlobal; press] | Cannes: $150k+, 800+ участников; NY: $225k+, 232 проекта [press] | То же | Нужно физическое присутствие [provider docs] | То же | Не подходит: владелец не выступает очно и не говорит по-английски |
| **ETHGlobal: новое с ETHOnline 2026** | — | — | Треки «Extend Open Source» и «Ship a Feature»: можно принести свой репозиторий, если новая часть открыта и прежняя работа раскрыта [provider docs] | — | — | Важно для флота: можно развивать свой OSS-инструмент вместо «с нуля» |
| **Colosseum (Solana и мультичейн)** | 2 больших хакатона в год: апрель–май и сентябрь–октябрь; между ними Eternal (сейчас на паузе, приз $25k USDC раз в полгода) [provider] | Frontier (06.04–11.05.2026): 10 000+ участников, 2 857 проектов, $2.75 млн с инвестициями [provider blog, 26.06.2026]. **Crypto World's Fair (14.09–12.10.2026): $840 000**: $30k гран-при, 20 × $15k, 2 × $5k, треки Solana/Tempo/Hyperliquid/Zcash по $100k (10 × $10k), Ethereum L1/Base/Arbitrum/Robinhood Chain по $25k (5 × $5k) [provider docs: официальные правила] | В правилах World's Fair ограничений на ИИ нет; в FAQ: «We have backed non-technical founders… who built MVPs entirely with AI coding tools» [provider] | Исключены лица, находящиеся или проживающие в Афганистане, Беларуси, Кубе, Иране, КНДР, России, Сомали, Сирии, Крыму и оккупированных регионах Украины, Венесуэле, Йемене; **Молдовы нет** [provider docs]. Победа — после «Prize Acceptance Documents» и due diligence | Гран-при — «$30,000 Phantom CASH stablecoin», прочие — CASH; призы — лидеру команды на кошелёк [provider docs] | Frontier: 28 призов / 2 857 ≈ **1%**. World's Fair: 83 места; на 26.09 зарегистрировано 6 610 участников [provider]; по конверсии Frontier (2 857/10 000) ожидаем ~1 900–2 500 проектов → **≈3.3–4.4%** [оценка] |
| **Colosseum Agent Hackathon** | Один раз: 02–13.02.2026 [provider: skill.md] | $100 000 USDC: $50k / $30k / $15k / $5k «Most Agentic» [press: Genfinity, 02.02.2026] | Только агенты: «No human code allowed»; человек обязан «claim» агента для призов [press; provider docs] | Как у Colosseum | USDC | 4 приза / 454 сданных проекта (750 с черновиками) ≈ **0.9%** [provider data: agents.colosseum.com/api, 26.09.2026] |
| **DoraHacks (хакатоны спонсоров)** | Много мелких, онлайн [provider] | KeeperHub Agents Onchain (07–08.2026): $5 000 — $2 000/$1 200/$800 + 2 × $500 за онбординг-вклад (PR, шаблон, туториал); 190 BUIDL, 512 участников. BUIDL CTC 2026 Fall: $15 000 — $10 000/$3 000/$2 000; 237 BUIDL, 396 участников; дедлайн 13.09 → победители 20.09.2026 [provider] | Отдельных правил об ИИ в этих двух не найдено | Санкционные регионы (OFAC) исключены; CTC — ещё «no criminal record»; KeeperHub — финалисты **питчат вживую** [provider] | «Cash prizes are distributed via stablecoins» (KeeperHub) [provider] | KeeperHub: 5 мест / 190 ≈ 2.6%; CTC: 3 / 237 ≈ 1.3% [provider data; расчёт наш] |
| Encode Club, TON, Base (хакатоны) | Нет данных: страницы рендерятся скриптом, веб-поиск исчерпан | — | — | — | — | — |

**Вывод по хакатонам [оценка]:** матожидание на один проект — ETHOnline ≈ 6% × $1 200 ≈ $70 на один партнёрский трек (до 3 треков на проект → ≈ $210); World's Fair ≈ 3.8% × $10 100 ≈ $380; Agent Hackathon ≈ $220 на средний проект; DoraHacks — $26–63. Для сильной команды шанс выше среднего, но точной оценки нет. Все сроки выплат — 30–75+ дней.

### 1.2 Баунти-платформы (кроме Superteam — он в базе)

| Платформа | Статус (26.09.2026) | Выплата | KYC / допуск | Правила об ИИ |
|---|---|---|---|---|
| **Drips Wave — Stellar** | Работает. Волна раз в месяц на 7 дней; бюджет $60 000 (волны 1–3), **$75 000 (волны 4–9)**; волна 9 — 23–30.09.2026; 824 репозитория, 503 организации [provider data] | Очки → доля пула; **USDC в сети Stellar** на свой кошелёк или биржу с USDC-Stellar; тестовый перевод $1 [provider docs] | **KYC до подачи заявки на задачу**; исключены санкционные юрисдикции и страны из списков FATF; **один аккаунт на человека**, KYC — «by the natural person who actually uses it» [provider docs: terms] | Запрещено «code… generated by LLMs that are of low quality, untested, or not understood by the Contributor»; лимит 7 задач на организацию за волну [provider docs; provider blog] |
| Superteam Earn (обновление к CR-01) | Снимок 26.09.2026: 26 открытых листингов, из них 2 `AGENT_ALLOWED`; большинство — посты в X; dev-баунти «Build and Demo a Mermail Agent Skill» — $500 при 166 заявках (≈ $3 на заявку) [provider data: superteam.fun/api/listings] | USDC/USDG | База: Молдове — только Global | База: ИИ-спам помечается |
| Algora | Сменил фокус на найм («Hire the top 1% open source engineers»); баунти остались у отдельных проектов [provider] | База: только Stripe Express, не крипта | — | — |
| Opire | Работает, но **платёж не проходит через платформу**: «payments are arranged directly by the people involved»; минимум баунти $20 [provider docs] | Как договоритесь — эскроу нет | — | — |
| IssueHunt | Теперь японская платформа баг-баунти; выплата «via bank or PayPal» [provider] | Не крипта | — | — |
| Replit Bounties | replit.com/bounties перенаправляет на contra.com/replit («Hire Replit Experts») [provider, редирект 26.09.2026] | — | — | — |
| OnlyDust | **Закрыт**: «The OnlyDust chapter closes here»; за 4 года — $18 млн грантов 4 000 контрибьюторам; причина — мейнтейнеров завалили ИИ-кодом [provider, дата на странице не указана] | — | — | — |
| Gitcoin | На главной — кампании (Protocol Guild и др.) и GG24 как прошедший раунд; открытой доски баунти для разработчиков не видно [provider]. GG24 ≈ $1.8 млн (база) | Крипта | Gitcoin Passport (база) | — |

### 1.3 Гранты экосистем

| Экосистема | Что есть сейчас | Для нас |
|---|---|---|
| Solana Foundation | Гранты по вехам для public goods, конвертируемые гранты, RFP; «anyone with an internet connection»; суммы не указаны [provider: solana.org/grants-funding] | Возможен OSS-инструмент (CR-05 из базы). Сроки — нет данных |
| Superteam Microgrants | До $10 000, регионы «India, Southeast Asia, Eastern Europe, and Africa» [provider: solana.org] | Чаптера для Молдовы нет (база) → проверить, считается ли MD «Eastern Europe» |
| Arbitrum | Arbitrum DAO Grant Program, Trailblazer AI ($1 млн), Stylus Sprint — **«Program Complete / Inactive»**; активны Audit Program ($10 млн ARB на субсидии аудитов), Gaming Ventures, Alchemy-кредиты [provider: arbitrum.foundation/grants] | Для соло-разработчика грантов нет |
| Base | docs.base.org «get-funded» ведёт на Base Ecosystem Fund (pre-seed/seed инвестиции) и Base Batches (акселератор, $100k инвестиций) [provider] | Это доли в компании, не доход |
| TON | ton.org/en/grants перенаправляет на главную ton.org [provider, 26.09.2026]; репозиторий grants-and-bounties заархивирован (база) | Тупик до новых данных |
| Optimism (Retro Funding), NEAR | Нет данных: OP Atlas рендерится скриптом, near.org не открылся (TLS) | Проверить |

### 1.4 Аудит-конкурсы и баг-баунти

| Платформа | Правила об ИИ | KYC | Выплата | Для новичка |
|---|---|---|---|---|
| **Immunefi** | «Submitting AI-generated/automated scanner bug reports that lack the required information regarding the vulnerability's impact» — запрещено, грозит временным или постоянным баном; тестирование в mainnet — немедленный бан [provider docs: immunefi.com/rules] | KYC для выплаты; фальшивый KYC запрещён [provider docs]; от $500 (база) | Крипта (база) | Нужна экспертиза Solidity/Rust (база) |
| **Cantina** | Статус **Spam**: «irrelevant, low-quality, automated, AI-generated… Spam can carry reputation and deposit consequences» [provider docs] | KYC через Persona + скрининг OFAC; исключены санкционные страны [provider docs] | **USDC только в Ethereum mainnet**, мультисиг, еженедельный цикл [provider docs] | Нет данных о доле успешных новичков |
| **Sherlock** | Отдельного правила об ИИ нет; фильтр — ≥2 валидных находки и ratio ≥20% пожизненно (база) | Нет данных | USDC (база) | То же |
| **HackenProof** | Против спама — пороги репутации и **платные подачи** в части программ (взнос возвращается за валидный отчёт или дубликат) [provider docs] | KYC (AMLBot) — только для налоговых резидентов ЕС или по запросу компании [provider docs] → резиденту Молдовы — по запросу | С 22.05.2025 — USDC; минимум вывода 100 USDC; 2FA; свыше $5 000 суммарно — доп. проверка [provider docs] | Есть web2-поверхности бирж (OKX до $1 млн, BingX до $4 000, WhiteBIT до $10 000 и др.) [provider]; всего выплачено $26 млн+ 82 000+ хакерам за 85 000+ отчётов [provider] → ≈ $306 на поданный отчёт в среднем [оценка, распределение сильно скошено] |
| CodeHawks (Cyfrin) | First Flights — учебные, **без денег** (XP); есть AI First Flights с ИИ-проверкой [provider docs] | Для денежных конкурсов — KYC [provider docs] | — | Только тренировка |
| Code4rena | Закрыт 13.05.2026 (база) | — | — | — |

**Реальная доля выигрышей для новичков** в аудит-конкурсах — **нет данных** (платформы не публикуют). Косвенно: у curl доля подтверждённых отчётов упала до <5% в 2025 году из-за ИИ-мусора [press: daniel.haxx.se, 26.01.2026].

### 1.5 DevRel, контент и локализация (RO/RU) для крипто-проектов

- web3.career, сентябрь 2026 [vendor: джоб-борд]: SEO — 71, Translator — 31, Technical Writer — 68, Developer Relations — 225, Content Writer — 65 вакансий.
- Переводчики: из видимых позиций одна «Localization Specialist Translator Russian», **ни одной с румынским**, одна «UNPAID VOLUNTEER» [vendor].
- Superteam Earn: из 1 989 закрытых листингов переводческих — 4, по $30–35, 2023–2024 годы (**старше 2025**); языковые баунти 2026 — почти все у чаптера Ukraine, Молдове недоступны (регион) [provider data + база].
- Вывод: **платного спроса на RO/RU-локализацию крипто-проектов почти нет**; RU-аудитория крипто-бирж — это ещё и риск (санкции, РФ-исключения платформ).

### 1.6 SEO для крипто-проектов с оплатой в USDT/USDC: спрос и риски

**Спрос.** 71 SEO-вакансия на web3.career; на первой странице 15 позиций — почти все full-time в биржах и брокерах (Bitpanda, Binance, Kraken, Crypto.com — в том числе «SEO AEO Manager Sports Prediction»), объявлениям 2–11 месяцев; «freelance/part-time» упоминается 4–5 раз [vendor, 26.09.2026]. Контрактного асинхронного спроса меньше, чем предполагал CR-02 (база). Число Web3-SEO-агентств — нет данных.

**Юридические и репутационные риски:**
1. **Великобритания:** режим крипто-финпромоушена с 08.10.2023 «applies to all firms marketing cryptoassets to UK consumers, regardless of whether the firm is based overseas»; законных путей 4, все требуют авторизованного или зарегистрированного в FCA лица [official: fca.org.uk/firms/cryptoassets]. Контент или лендинги для биржи, нацеленные на UK, могут оказаться незаконной рекламой.
2. **ЕС (MiCA):** услуги неавторизованного CASP резидентам ЕС допустимы только по инициативе клиента (ст. 61 MiCA) — текст в этой сессии не открыт (EUR-Lex вернул пустой ответ) → **проверить**. Румыния — в ЕС.
3. **Молдова:** после 17.03.2027 любая реклама зарубежной биржи на Молдову снимает для неё исключение reverse solicitation (ст. 55 проекта; база). SEO/RO-контент, продвигающий неавторизованную биржу в Молдове, — риск.
4. **Google:** купля-продажа ссылок, «site reputation abuse», «scaled content abuse», «expired domain abuse» — нарушения спам-политик (обновлены 28.08.2026) [official: developers.google.com]. Крипто-казино и гемблинг — главные заказчики ссылок; исключены правилами проекта.
5. **Правила проекта:** не брать казино, prediction markets/«sports prediction», мемкоины, сигналы, продвижение токенов. Остаётся инфраструктура: кошельки, SDK, RPC/индексаторы, документация протоколов, B2B-стейблкоин-платежи.
6. **Оплата:** крипта необратима, эскроу вне Contra нет → предоплата по этапам (база CR-02).

### 1.7 Общий тренд 2026: ИИ-заявки — главный риск модели «флот шлёт много»

- Immunefi — бан за ИИ-отчёты; Cantina — Spam с последствиями для депозита; HackenProof — платные подачи; Drips Wave — запрет непонятого LLM-кода и мульти-аккаунтов; ETHGlobal — раскрытие ИИ; Superteam — ИИ-спам помечается (база) [provider docs].
- curl: «explosion in AI slop reports»; баг-баунти закрыт 31.01.2026; было 87 подтверждённых уязвимостей и >$100 000 выплат [press: блог автора curl, 26.01.2026].
- OnlyDust закрыт: «Low-skill contributors were flooding them with AI-generated code» [provider].
- Конкуренция: другие операторы уже гоняют агентов-«охотников за задачами» (например, GitHub-бот «TASK HUNTER», 14.09.2026, проверяет крипто-хакатоны на допуск и выплату) [forum/GitHub].
- **Следствие для флота [интерпретация]:** выигрывает только качество — мало заявок, каждая проверена владельцем и воспроизводима; один аккаунт на человека; никаких мульти-аккаунтов (это ещё и sybil — исключение проекта).

### 1.8 Рельсы выплат этого потока → Bybit/BingX

| Источник | Валюта и сеть | Попадание на биржу |
|---|---|---|
| Drips Wave | USDC, **Stellar** | Поддерживает ли Bybit/BingX депозит USDC-Stellar — **проверить в аккаунте**; запасной путь: кошелёк LOBSTR → обмен на XLM → депозит XLM [оценка] |
| Colosseum | **CASH** (стейблкоин Phantom), Solana; Agent Hackathon — USDC | CASH на биржах — нет данных → обмен CASH→USDC на Solana, затем депозит USDC-SOL (проверить) |
| Cantina | USDC, только Ethereum mainnet | Газ ERC-20 при каждом движении |
| HackenProof | USDC, сети — нет данных; минимум 100 USDC | Проверить |
| ETHGlobal | USDC на «verified wallet» (финалисты); партнёры — по-разному | Проверить по событию |
| Superteam | USDC/USDG (база) | USDG на Bybit — проверить (база) |
| Contra / прямой инвойс | USDC ERC-20 (Contra) / любая сеть по договору (база) | Да |

Вывод в банк Молдовы — ≤50 000 лей/мес через спецсчёт (база). Крипто-доход — физлицу, не SRL (база). После 17.03.2027 биржи могут ограничить Молдову → держать некастодиальные кошельки Stellar/Solana/EVM (база).

---

## 2. Кандидаты

Ранг: **P(первый $ ≤ 30 дней) × потолок на 6-й месяц / часы владельца в неделю** — все множители [оценка]. Для призов «потолок» — среднемесячное матожидание.

### 2.1 Таблица A — ниша и деньги

| ID | Ниша (формат × тема × рынок) | Что производим | Монетизация | Выплата | Крипта | Пересечение с базой |
|---|---|---|---|---|---|---|
| CN-01 | Ежемесячные OSS-спринты Drips Wave × задачи в репозиториях экосистемы Stellar (TS/JS-фронтенды, SDK, документация) × EN, глобально | Pull requests: фиксы, фичи, доки | Доля пула $75 000 за волну по очкам | USDC-Stellar → свой кошелёк → Bybit/BingX | yes | Новое |
| CN-02 | Хакатон Colosseum Crypto World's Fair (до 12.10.2026) × x402 pay-per-call API «SEO/AI-crawler audit для агентов» на трек Base или Solana × EN | 1 продукт + репозиторий + видео с TTS | Приз $5 000–15 000 (83 места) | CASH/USDC → Solana → Bybit | yes | Переиспользует CR-03 |
| CN-03 | Онлайн-хакатоны ETHGlobal (HackMoney/ETHOnline) × трек «Extend Open Source» для своего OSS SEO/агентного инструмента × партнёрские призы (ENS, The Graph, x402 и т. п.) × EN | Новая фича к своему репозиторию + интеграция SDK спонсора | Партнёрские призы $500–2 500 | USDC на верифицированный кошелёк | yes | Новое |
| CN-04 | Хакатоны спонсоров на DoraHacks × «онбординг-баунти» (PR в SDK спонсора, стартовый шаблон, туториал) + рабочая интеграция × EN | PR, шаблоны, туториалы | Побочные призы $500 + основные места | Стейблкоины (по хакатону) | yes | Новое |
| CN-05 | Superteam Earn Global × dev- и doc-баунти + листинги `AGENT_ALLOWED` × EN | Код, агентные скиллы, технические гайды | Призы USDC/USDG | Кошелёк Solana → Bybit | yes | Уточнение CR-01 (понижено) |
| CN-06 | Технический SEO/GEO с внедрением × Web3-инфраструктура без токенов (кошельки, SDK, RPC/индексаторы, сайты документации, B2B-стейблкоин-платежи) × EN, асинхронно | Фикс-пакеты: schema, CWV, индексация docs, llms.txt, AI-crawler-аудит | $300–1 500 за проект, ретейнер | Contra (USDC ERC-20) или прямой инвойс USDC/USDT → Bybit | yes | Уточнение CR-02 (добавлен фильтр рисков) |
| CN-07 | Docs-as-code и DevRel-контент × Web3 dev-tools и протоколы × EN | Туториалы с рабочим кодом, sample-репозитории, API-референс, SEO документации | Контракт $500–2 000/мес или за единицу | Contra / инвойс USDC | yes | Новое |
| CN-08 | Баг-баунти HackenProof × web2-поверхность бирж и кошельков (логика аккаунтов, IDOR, авторизация, утечки в вебе) × глобально | Отчёты с воспроизведением | Вознаграждение по severity | USDC, минимум вывода 100 | yes | Новое |
| CN-09 | Аудит-конкурсы смарт-контрактов (Sherlock, Cantina) + Immunefi × EVM/Solana | Находки (issues) с PoC | Доля пула / баунти | USDC (Cantina — ETH mainnet) | yes | Уточнение CR-06 |
| CN-10 | RO/RU-локализация и носительская QA × UI и документация некастодиальных кошельков и dev-tools (не бирж, не для MD/RO-маркетинга) × RO/RU | MTPE + QA владельцем | $0.05–0.15 за слово (база N11) | Contra / инвойс USDC | yes | Новое (крипто-версия N11) |
| CN-11 | Агентные хакатоны и `AGENT_ALLOWED`-баунти × флот как зарегистрированный агент, владелец «claim» × EN | Проекты, сделанные агентом | Призы USDC | USDC | yes | Новое |
| CN-12 | Public-goods OSS × валидатор метаданных Solana Actions/Blinks + OG/SEO × грант Solana Foundation по вехам | OSS-инструмент + отчёты по вехам | Грант | Нет данных о валюте (крипта или фиат) | partial | Уточнение CR-05 |

### 2.2 Таблица B — доказательства, осуществимость, тест, экономика

| ID | Спрос (2025–2026) | Конкуренция | Флот без лица и GPU | 14-дневный тест | Дней до $ | P30 | Потолок на 6-й мес. [оценка] | Часы/нед |
|---|---|---|---|---|---|---|---|---|
| CN-01 | Пул $75 000/волна (волны 4–9), волна каждый месяц [provider data] | Волна 1: ~600 участников, >3 000 PR на $60 000 → ≈ $100 на участника [provider] | Да: код и тесты — флот; владелец — KYC, заявки на задачи, переписка с мейнтейнерами, понимание каждого PR (правило) | Владелец проходит KYC; флот отбирает 10 задач «good first issue» в TS/JS; 3–5 заявок в волне 9 (до 30.09) или подготовка к волне 10 (ожидается ~23.10 по ритму) | 40 | 0.1 | **$375** = 0.5% очков × $75 000 (≈ 3–4 средних участника: 15–20 PR при лимите 7 задач на организацию) | 4 |
| CN-02 | $840 000, 83 места; 6 610 участников на 26.09 [provider] | ~1 900–2 500 проектов [оценка по конверсии Frontier] | Да (Colosseum принимает продукты, сделанные ИИ). Видео-питч — TTS, риск для оценки | Флот упаковывает x402-API из CR-03 как продукт на трек Base/Solana; владелец регистрируется, сдаёт до 12.10 | 75 (победители к 05.12) | 0.0 | **$65** = 3.8% × $10 100 × 2 хакатона в год / 12 | 3 |
| CN-03 | 3 онлайн-события за 12 мес., $75–100k каждое [provider] | 639–837 проектов на событие [provider data] | Частично: нельзя «целиком ИИ», нужно раскрытие и реальный вклад владельца; стейк криптой | Выбрать OSS-репозиторий флота, подготовить план фичи под 2–3 спонсора; ждать анонса HackMoney 2027 (даты — нет данных) | 140 | 0.0 | **$55** = 3 трека × 6% × $1 200 × 3 события / 12 | 3 |
| CN-04 | Хакатоны на $5–15k с побочными баунти [provider] | 190–237 BUIDL [provider] | Частично: финалисты часто питчат вживую → целиться в побочные призы | Найти 2 открытых хакатона с онбординг-баунти; сдать 1 PR/туториал в SDK спонсора | 35 | 0.05 | **$100** = 2 заявки/мес × 10% × $500 | 3 |
| CN-05 | Снимок 26.09: 26 открытых, 2 `AGENT_ALLOWED` [provider data] | Dev-баунти $500 при 166 заявках (≈ $3 на заявку) [provider data] | Да (агентный API, база) | Флот сканирует Global/`AGENT_ALLOWED`, владелец отправляет 3–4 проверенные работы | 30 | 0.1 | **$150** (ниже CR-01: $290) = 10 заявок × $15 | 3 |
| CN-06 | 71 SEO-вакансия в Web3, в основном full-time бирж [vendor]; спрос на контракты — нет данных | Web3-SEO-агентства есть, число — нет данных | Частично: аудит и код — флот; переписка EN асинхронно; владелец (15+ лет SEO) проверяет | Профиль Contra с 3 фикс-пакетами для Web3-инфраструктуры; 2 публичных разбора SEO документации популярных SDK (без упоминания токенов); 15 откликов без звонков; фильтр рисков 1.6 | 21 | 0.15 | **$1 500** = 2 проекта × $500 + ретейнер $500 | 8 |
| CN-07 | Technical Writer — 68, DevRel — 225 вакансий [vendor] | Нет данных | Частично: флот пишет и проверяет код; английский владелец проверяет лишь частично → риск качества | 3 туториала-образца с рабочим репозиторием (Stellar/Solana/EVM SDK) + профиль Contra; 10 откликов на контракты | 30 | 0.1 | **$1 000** = 1 контракт × $1 000/мес | 6 |
| CN-08 | $26 млн+ выплачено, 400+ программ [provider] | 82 000+ хакеров [provider] | Частично: нужен пентест-опыт; автоматическое сканирование с большим трафиком запрещено (Immunefi — аналогично) | Выбрать 2 программы бирж без платной подачи; ручной разбор веб-логики с помощью флота, без сканеров | 45 | 0.05 | **$150** = 1 низкий severity раз в 2 мес × $300 | 5 |
| CN-09 | Web3 баг-баунти >$162 млн (база) | Очень высокая; ИИ-спам наказывается | Частично: нет экспертизы Solidity/Rust | Один конкурс в режиме «только наблюдать» (база CR-06) | 90 | 0.01 | **$50** | 6 |
| CN-10 | 31 вакансия переводчика, 1 RU, 0 RO [vendor]; переводческие баунти $30–35 (2023–24) [provider data] | Нет данных | Да: MTPE — флот, QA RO/RU — владелец (его сильная сторона) | Профиль «RO/RU wallet/dev-tool localization» на Contra; 5 откликов | 30 | 0.03 | **$150** = 3 000 слов × $0.05 | 4 |
| CN-11 | Один агентный хакатон за год ($100k) [provider]; 2 листинга `AGENT_ALLOWED` сейчас [provider data] | 454 проекта на 4 приза [provider data] | Да — по определению | Ждать следующего агентного хакатона; сейчас — 1 заявка `AGENT_ALLOWED` | 90 | 0.02 | **$50** | 1 |
| CN-12 | Solana Foundation — гранты по вехам, открыты всем [provider]; Arbitrum/Base/TON — закрыты или не гранты [provider] | Нет данных | Да | Выпустить MVP OSS-валидатора, подать заявку | 90 | 0.02 | **$150** (как CR-05) | 2 |

### 2.3 Ранг

1. **CN-06** — 0.15 × 1 500 / 8 = **28.1**
2. **CN-07** — 0.1 × 1 000 / 6 = **16.7**
3. **CN-01** — 0.1 × 375 / 4 = **9.4**
4. **CN-05** — 0.1 × 150 / 3 = 5.0
5. CN-04 — 1.7; CN-08 — 1.5; CN-12 — 1.5; CN-10 — 1.1; CN-11 — 1.0; CN-09 — 0.08; CN-02 и CN-03 — 0 (деньги позже 30 дней; матожидание CN-02 ≈ $380 за один проект).

**Что делать [оценка]:**
- CN-06 + CN-07 — одна «Web3-витрина» на Contra параллельно с нишей №1 (Upwork). Тот же конвейер аудита, другой рельс (USDC).
- CN-01 — один тест в волне 10 (ожидается в конце октября): KYC сейчас, 10 задач в TS/JS, каждый PR владелец понимает и может объяснить.
- CN-02 — только если флот за 2 недели упакует уже строящийся x402-API (CR-03) — тогда хакатон бесплатно даёт внешний дедлайн, судей и портфолио для CN-06/07.
- Остальное — не сейчас.

---

## 3. Ловушки и тупики (с доказательствами)

1. **Массовые ИИ-заявки** — баны и штрафы: Immunefi (бан) [provider docs]; Cantina (Spam, депозит) [provider docs]; HackenProof (платные подачи) [provider docs]; Drips Wave (LLM-код без понимания запрещён) [provider docs]. curl закрыл баунти из-за ИИ-мусора, 31.01.2026 [press].
2. **Мульти-аккаунты, «команды» из агентов на разных людей, чужой KYC** — прямо запрещено: Drips Wave (один аккаунт, KYC тем, кто пользуется) [provider docs]; Sherlock ввёл критерий «2 valid issues» против бесконечных аккаунтов (база); Immunefi — «inauthentic KYC information» [provider docs]. Это sybil — исключение проекта.
3. **Ставка на хакатоны как на доход** — доли призов ~1–6% на проект, выплаты через 30–75+ дней (раздел 1.1).
4. **Живые питчи и офлайн-участие** — ETHGlobal офлайн требует присутствия [provider docs]; финалисты KeeperHub питчат вживую [provider]; владелец не говорит по-английски устно.
5. **«Пиши пост в X про токен» (Superteam)** — большинство открытых листингов 26.09 — продвижение токенов и событий в X (например, «Create twitter Post about the STREAM burn») [provider data] → продвижение токенов исключено правилами проекта, плюс нужен свой охват.
6. **RO/RU-локализация как крипто-ниша** — платного спроса почти нет (раздел 1.5); RO — MiCA, MD — ст. 55 после 17.03.2027 (раздел 1.6).
7. **SEO для бирж, казино, prediction markets** — FCA (UK), MiCA (ЕС), ст. 55 (MD), спам-политики Google; исключения проекта (раздел 1.6). Даже на web3.career есть «SEO AEO Manager Sports Prediction» [vendor].
8. **Algora / Opire / IssueHunt** — не крипта (Stripe, банк, PayPal) или платёж вне платформы без эскроу [provider docs; база].
9. **Replit Bounties, OnlyDust, Code4rena** — закрыты или перенаправлены [provider; база].
10. **Гранты Arbitrum DAO и Trailblazer AI** — «Program Complete / Inactive»; **Base** — это инвестиции, не гранты; **TON grants** — страница исчезла [provider].
11. **CodeHawks First Flights** — без денег (только XP) [provider docs]; не путать с доходом.
12. **Стейблкоины «не той сети»** — CASH (Colosseum), USDC-Stellar (Drips), USDG (Superteam) могут не приниматься биржей → потери на свопах и риск ошибки сети; Drips: «not responsible for funds lost due to incorrect addresses, missing Memos, incompatible wallets» [provider docs].

---

## 4. Что не удалось проверить

- Веб-поиск сессии исчерпан (200/200) — дальше читались только известные URL и публичные API.
- ETHGlobal: KYC для партнёрских призов, кто и когда платит, сумма стейка; даты следующего онлайн-события (HackMoney 2027).
- Colosseum: принимают ли видео-питч с TTS без ущерба для оценки; есть ли CASH на Bybit/BingX.
- Drips Wave: число участников и распределение выплат в волнах 4–9; сроки выплаты после волны; поддержка USDC-Stellar на Bybit/BingX.
- Sherlock — KYC и страны; Immunefi — актуальная страница KYC (справка отдаёт 403, порог $500 — из базы).
- Доля выигрышей новичков в аудит-конкурсах — платформы не публикуют.
- HackenProof — сети вывода USDC и комиссия.
- Encode Club, TON-хакатоны, Base-хакатоны, Optimism Retro Funding 2026, NEAR-гранты, Gitcoin GG25 — страницы рендерятся скриптом или не открылись.
- Superteam Microgrants — входит ли Молдова в «Eastern Europe».
- MiCA ст. 61 — текст не открыт (EUR-Lex пустой ответ).
- Число Web3-SEO/DevRel-контрактов без звонков — нет данных.
- Налог на крипто-призы и оплату в USDC для физлица — база (к бухгалтеру).

---

## 5. Источники (прочитаны 26.09.2026, если не указано иное)

**Хакатоны**
- ETHGlobal, правила событий (AI, «from scratch»), Tokyo 2026 — https://ethglobal.com/events/tokyo2026/info/details [provider docs]
- ETHGlobal, общие правила (стейк, Continuity-треки) — https://ethglobal.com/rules [provider docs]
- ETHOnline 2026 (04–16.09.2026, $100k, новые треки) — https://ethglobal.com/events/ethonline2026 ; призы — https://ethglobal.com/events/ethonline2026/prizes [provider]
- ETHOnline 2025 (10–31.10.2025) — https://ethglobal.com/events/ethonline2025 ; призы и пакет финалиста — https://ethglobal.com/events/ethonline2025/prizes [provider]
- HackMoney 2026 (30.01–11.02.2026, $75k) — https://ethglobal.com/events/hackmoney2026 [provider]
- Витрина ETHGlobal (пагинация, 33 проекта на страницу) — https://ethglobal.com/showcase?events=ethonline2026 (и ethonline2025, hackmoney2026) [provider data]
- ETHGlobal, календарь 2026 (X) — https://x.com/ETHGlobal/status/1992919708589576215 [provider, по поисковой выдержке]
- Crypto.news, ETHGlobal Cannes 2026 — https://crypto.news/ai-agents-privacy-and-prediction-markets-define-ethglobal-cannes-2026-finalists/ [press, 04.2026, по выдержке]
- Crypto Briefing, ETHGlobal NYC 2026 — https://cryptobriefing.com/ethglobal-nyc-hackathon-june-2026/ [press, 06.2026, по выдержке]
- Colosseum, Crypto World's Fair — https://colosseum.com/worldsfair ; официальные правила — https://colosseum.com/legal/Crypto%20World's%20Fair%20Hackathon%20Rules.pdf [provider docs]
- Colosseum, хакатоны и FAQ — https://colosseum.com/hackathon ; Eternal — https://colosseum.com/eternal [provider]
- Colosseum, победители Frontier (26.06.2026) — https://blog.colosseum.com/announcing-the-winners-of-the-solana-frontier-hackathon/ [provider]
- Colosseum Agent Hackathon, skill.md v1.8.0 — https://colosseum.com/skill.md ; API проектов — https://agents.colosseum.com/api/projects [provider docs / provider data]
- Genfinity, 02.02.2026 — https://genfinity.io/2026/02/02/solana-colosseum-launches-ai-agent-hackathon/ ; Blockonomi, 04.02.2026 — https://blockonomi.com/colosseum-launches-ai-agent-hackathon-on-solana-with-100000-prize-pool/ [press]
- DoraHacks, KeeperHub Agents Onchain — https://dorahacks.io/hackathon/agents-onchain/detail ; BUIDL CTC 2026 Fall — https://dorahacks.io/hackathon/buidl-ctc-2026-fall/detail [provider]
- GitHub, KeeperHub issue #2321 (05.09.2026) — https://github.com/KeeperHub/keeperhub/issues/2321 [forum]; «TASK HUNTER», 14.09.2026 — https://github.com/Inkh95/t3n-trusted-approval-agent/issues/12 [forum]

**Баунти и OSS**
- Drips Wave — https://www.drips.network/wave ; Stellar Wave (бюджеты волн) — https://www.drips.network/wave/stellar [provider data]
- Drips Wave, условия — https://docs.drips.network/wave/terms-and-rules ; вывод наград — https://docs.drips.network/wave/withdrawing-rewards ; очки — https://docs.drips.network/wave/points-and-rewards ; FAQ — https://docs.drips.network/wave/contributors/faq [provider docs]
- Drips, changelog волны 2 (16.02.2026) — https://www.drips.network/blog/posts/wave-2-changelog ; волны 7 (22.07.2026) — https://www.drips.network/blog/posts/wave-7-changelog ; гайд (20.05.2026) — https://www.drips.network/blog/posts/your-guide-to-contributing-well-in-wave [provider]
- Superteam Earn, открытые листинги — https://superteam.fun/api/listings [provider data]; закрытые листинги — выгрузка потока crypto_rails [provider data]
- Opire — https://opire.dev/home ; Costs & Payments — https://docs.opire.dev/rewards/pricing [provider docs]
- Algora — https://algora.io/ [provider]
- IssueHunt — https://issuehunt.io/ [provider]
- Replit Bounties → https://contra.com/replit (редирект) [provider]
- OnlyDust — https://www.onlydust.com/ [provider, дата не указана]
- Gitcoin — https://gitcoin.co/ [provider]

**Гранты**
- Solana, гранты — https://solana.org/grants-funding [provider]
- Arbitrum, гранты — https://arbitrum.foundation/grants [provider]
- Base, финансирование — https://docs.base.org/get-started/base-ecosystem-fund [provider]
- TON, гранты (редирект на главную) — https://ton.org/en/grants [provider]

**Аудит и баг-баунти**
- Immunefi, правила — https://immunefi.com/rules/ [provider docs]
- Cantina, конкурсы — https://docs.cantina.security/researchers/participation/competitions ; KYC — https://docs.cantina.security/researchers/joining/kyc ; выплаты — https://docs.cantina.security/researchers/joining/payout-schedule ; Bounty Terms — https://cantina.xyz/terms/bounties [provider docs]
- Sherlock, критерии выплат — https://docs.sherlock.xyz/audits/watsons/meeting-the-payout-criteria ; индекс документации — https://docs.sherlock.xyz/llms.txt [provider docs]
- HackenProof — https://hackenproof.com/ ; KYC — https://docs.hackenproof.com/dashboard/hacker-dashboard/kyc ; вывод — https://docs.hackenproof.com/dashboard/hacker-dashboard/withdraw-bounty ; требования к подаче — https://docs.hackenproof.com/bug-bounty/reports-basics/report-submission-requirements [provider docs]
- CodeHawks, First Flights — https://docs.codehawks.com/first-flights ; FAQ — https://docs.codehawks.com/faqs [provider docs, по выдержке]
- curl, «The end of the curl bug-bounty», 26.01.2026 — https://daniel.haxx.se/blog/2026/01/26/the-end-of-the-curl-bug-bounty/ [press: блог автора]
- Stingrai, перепись политик об ИИ-отчётах, 28.07.2026 — https://www.stingrai.io/blog/ai-generated-vulnerability-report-policies-census [vendor]

**Спрос и риски**
- web3.career, сентябрь 2026: SEO — https://web3.career/seo-jobs ; Translator — https://web3.career/translator-jobs ; Technical Writer — https://web3.career/technical-writer-jobs ; DevRel — https://web3.career/developer-relations-jobs ; Content Writer — https://web3.career/content-writer-jobs [vendor: джоб-борд]
- FCA, cryptoassets (финпромоушен, 08.10.2023; PS23/6, FG23/3) — https://www.fca.org.uk/firms/cryptoassets [official]
- Google Search, спам-политики (обновлено 28.08.2026) — https://developers.google.com/search/docs/essentials/spam-policies [official]
- MiCA (Регламент (ЕС) 2023/1114) — https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32023R1114 [official, текст не открыт — проверить]
- База: `STATUS.md`, `notes/crypto_rails_2026.md`, `notes/telegram_2026.md`, `notes/niches_b2b_services.md`, `notes/decision_niche_1.md`

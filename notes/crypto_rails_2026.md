# Крипто-рельсы выплат и их законность для резидента Молдовы (физлицо и Global Web SRL, IT Park)

Дата: 26.09.2026. Поток «crypto payout rails and legality» мастер-плана.
Только исследование: аккаунты не создавались, формы не отправлялись, ничего не покупалось. Публичные API (Superteam Earn, Notion-таблица Contra) читались без регистрации.
Это исследование, а не юридическая или налоговая консультация. Пункты «к юристу / бухгалтеру» — для молдавского юриста и бухгалтера.

**Метки:** [official] — закон, госисточник, проект закона на gov.md; [provider docs] — справка или документация провайдера; [provider data] — выгрузка из публичного API провайдера; [press]; [vendor] — блог продавца, агрегатора, конкурента; [forum]; [интерпретация]; [оценка] — с формулой.

**База проекта (не перепроверялась, `STATUS.md` 2.1–2.6):** Bybit — SEPA и SWIFT для Молдовы ограничены (список от 18.09.2026); BingX Card доступна Молдове (только траты); CoinGate — Молдова в списке, 1%; Cryptomus — штраф FINTRAC; Telegram Stars — $0.013 за Star, холд 21 день, рекламная доля 50% в TON; закон 308/2017 ст. 4(1^1) и 5(4^4); курс НБМ 25.09.2026: 1 USD = 17.7706 MDL.

**Допущения по умолчанию (вопросы не задавались):**
1. Крипто-доход получает **физлицо-владелец** на свой KYC-аккаунт Bybit/BingX или свой кошелёк. Global Web SRL получает только фиат на OTP (причина — раздел 3.4).
2. Налоги — после первого дохода (решение пользователя 26.09), но риски отмечены.
3. Язык работы с клиентами — EN письменно, RO/RU — с полной проверкой владельцем.

---

## TL;DR

1. **Получать крипту за свою работу из-за рубежа резиденту Молдовы прямо не запрещено**, но и прямо не разрешено. Запрет ст. 4(1^1) закона 308/2017 касается *оказания услуг с виртуальными активами* на территории Молдовы, а не получения оплаты [official; интерпретация]. Узкое место — не приём, а **вывод в банк Молдовы: не больше 50 000 лей в месяц** (≈ $2 814) «în/din adresa» зарубежных провайдеров, то есть в обе стороны, и **только через специальные счета** [official: пояснительная записка правительства к проекту закона, апрель 2026].
2. **Новый закон о рынке криптоактивов** (по прессе — № 180 от 24.08.2026, указ 773-X от 14.09.2026, опубликован 17.09.2026) **вступает в силу 17.03.2027** — через 6 месяцев после публикации. В тексте проекта нет запрета получать крипту за услуги. Министр финансов (15.01.2026) обещал запрет **платежей криптой на территории страны** (магазин ↔ покупатель); к экспорту услуг это прямо не относится [official + press; интерпретация]. После 17.03.2027 зарубежные биржи могут обслуживать резидентов только «по исключительной инициативе клиента» (ст. 55 проекта) — **риск, что Bybit/BingX ограничат Молдову**.
3. **Для SRL крипта не подходит.** Закон 62/2008: юрлица проводят платежи по валютным операциям только через банковские или платёжные счета [official, по поисковой выдержке]. Плюс аудит IT Park требует подтверждения оплаты. Держать схему «SRL → фиат на OTP, физлицо → крипта» [интерпретация; к бухгалтеру].
4. **Рабочие крипто-рельсы для Молдовы (проверено на страницах провайдеров):**
   - **Creem** — выплата в USDC (Polygon), 2%, минимум $50;
   - **Contra** — USDC для Молдовы «YES», комиссия 2% (Pro — 1%);
   - **Deel** — USDC/USDT на свой кошелёк, 2% + $1, минимум $5; список стран не опубликован;
   - **Superteam Earn** — призы в USDC/USDG на кошелёк; есть **официальный API для ИИ-агентов**; Молдова — только Global-листинги;
   - **Bybit Pay Send & Receive** — перевод между пользователями Bybit без комиссии, до $100k в месяц;
   - **x402** — оплата API агентами в USDC прямо на свой кошелёк;
   - **Telegram Stars/TON**;
   - прямые инвойсы в стейблкоинах (Request Finance Free — $0).
5. **Не платят криптой или недоступны Молдове:** Polar, Dodo, Lemon Squeezy, Gumroad, Upwork, Algora; Stripe stablecoin payouts для Connect (MD нет в списке); Stripe приём стейблкоинов (только US и превью ЕС/HK/MX/CH); Coinbase Business (только US и Сингапур) — значит, и крипто-выплаты Whop; Code4rena (закрылся 13.05.2026).
6. **Лучшие ниши, которые работают именно благодаря крипто-выплате** [оценка, раздел 5]:
   - **CR-02** — технический SEO/GEO для Web3-компаний с оплатой в USDC через Contra и прямые инвойсы;
   - **CR-03** — платные по вызову SEO-API для ИИ-агентов через x402;
   - **CR-01** — Global-баунти Superteam Earn через агентный API.

   Все три — дополнение к нише №1 (Upwork + Apify), а не замена.

---

## 1. Платформы, MoR и маркетплейсы: платят ли криптой (a)

### 1.1 Платят криптой, Молдова подходит или вероятно подходит

- **Creem (MoR для SaaS и цифровых продуктов).**
  - «Creem also supports payouts in USDC using the Polygon Network… Fee: 2% of the payout volume» [provider docs: docs.creem.io/…/payouts, дата не указана, прочитано 26.09.2026].
  - Выплата на банк стоит $7/€7 или 1% (что больше). Минимум $50/€50, выплаты 1-го и 15-го числа, холд 7–12 дней.
  - При онбординге физлицом или бизнесом получатель выплаты должен совпадать с KYC.
  - Молдова в списке стран Creem (база `niches_software.md` C2).
- **Contra (маркетплейс фрилансеров).**
  - Таблица «Supported Payout Methods», строка Moldova: Crypto USDC **YES**, Local Bank Transfer **YES (Stripe)**, PayPal YES, Payoneer YES, SWIFT NO, USD Bank NO [provider docs: Notion-таблица из help.contra.com, дата не указана].
  - USDC — только сеть ERC-20 [provider docs / vendor].
  - Комиссия за крипто-вывод — 2% на Free, 1% на Pro [provider docs: help.contra.com, 12.05.2026].
  - Лимит — $10k в день на все выплаты [provider docs, по поисковой выдержке].
- **Deel (подрядчик; платит клиент, у которого есть Deel).**
  - «Stablecoins Transfer»: USDC и USDT. Сети USDT — ERC-20, TRC-20, BEP-20, Polygon, Tempo; сети USDC — ERC-20, Base, Polygon, BEP-20, Solana.
  - Комиссия 2% + $1, минимум $5.
  - Ограничения: «Withdrawals to accounts in the USA and UK are not supported»; для граждан некоторых стран нужен Proof of Location [provider docs: help.letsdeel.com, обновлено 29.07.2026; комиссии — 15.04.2026].
  - Молдова в явном виде не упомянута — «eligible countries» → **проверить**.
  - Другой путь — Coinbase: USDC $5 до $300 и 1.6% сверх, минимум $10 (нужен аккаунт Coinbase).
- **Superteam Earn (экосистема Solana).**
  - Призы в USDC/USDG выплачиваются «to the wallet associated with the winner's Superteam Earn account».
  - KYC нужен для листингов, которые спонсирует Superteam или Solana; выплата — в течение 7 дней после формы [provider docs: Superteam Handbook FAQ].
  - Официальный агентный интерфейс [provider docs: superteam.fun/skill.md, 26.09.2026]: регистрация агента, листинги `AGENT_ALLOWED` / `AGENT_ONLY`, отправка работ через API. «Agents do not complete OAuth, wallet signing, or KYC. A human must claim the agent for payouts».
  - Регионы: у каждого листинга есть поле `region`. Молдова не входит в чаптер Balkan (11 стран, в том числе Румыния) и Ukraine [provider data] → доступны только **Global**-листинги.
- **Sherlock (аудит-конкурсы).**
  - Выплаты в USDC. Условия: не меньше 2 валидных находок и «issues ratio ≥ 20%» [provider docs: docs.sherlock.xyz].
  - KYC и страны на странице не указаны → **проверить**.
- **Immunefi (баг-баунти).**
  - Выплаты в крипте. KYC (Onfido) — при выигрыше от $500. Запрещены страны под OFAC/UNSC [provider docs: справка Immunefi, по поисковой выдержке, дата неизвестна]. Молдовы в списке нет.
- **Telegram (база).**
  - Stars → Fragment → TON.
  - Реклама: 50% дохода владельцам публичных каналов от 1 000 подписчиков, вывод в TON через Fragment [official: telegram.org/blog, 2024 — **старше 2025 года**, правило действует; vendor: invitemember.com 2026].
- **Gitcoin.** GG24 (октябрь–ноябрь 2025) распределил около $1.8 млн в криптовалюте [provider: gitcoin.co case study]. Даты GG25 — нет данных.
- **Stripe Global Payouts в USDC.** «USDC payouts are available to businesses located in the United States, sending to recipients with a crypto wallet anywhere in the world» (private preview) [provider docs: docs.stripe.com/global-payouts/recipient-requirements, прочитано 26.09.2026]. Значит, американская платформа на Stripe может заплатить молдаванину в USDC — **частично, зависит от платформы**.

### 1.2 Не платят криптой (для Молдовы)

- **Polar** — выплаты только через Stripe Connect Express. Минимум для MDL — $40; с 12.05.2026 холд 7 дней [provider docs: polar.sh/docs/…/payouts].
- **Stripe stablecoin payouts for Connect** — «only available to platforms based in the US… Payouts to companies… aren't supported». В списке стран-получателей **MD нет**, RO есть [provider docs: docs.stripe.com/connect/stablecoin-payouts]. Отсюда вывод [интерпретация]: крипто-выплаты Braintrust, которые идут через Stripe, для Молдовы, вероятно, недоступны → проверить.
- **Dodo Payments** — принимает стейблкоины от покупателей (USDC, USDP, USDG; версия 1.97.6 от 07.05.2026), но выплачивает только на банк. Молдова — №103 в списке стран [provider docs].
- **Whop** — «Coinbase payouts: Withdrawals must go to a Coinbase wallet… customers must buy using crypto» [provider docs: docs.whop.com]. Coinbase Business доступен только в США и Сингапуре [vendor/press, по выдержке] → для Молдовы тупик.
- **Lemon Squeezy, Gumroad** — выплаты в фиате (банк или PayPal) [vendor: getly.store, fungies.io 2026; база `STATUS.md`].
- **Upwork** — крипто-вывода нет [vendor: acctual.com / vaultleap 2026]. Тест стейблкоин-выплат через Payoneer (LatAm) — [vendor], не подтверждено.
- **Algora** — только Stripe Express с KYC [vendor: gigs.sh; GitHub issue]. Доступна ли Молдова — проверить.
- **Payoneer** — анонс «stablecoin capabilities… select markets in Q2 2026, broader availability rolling out throughout the year» (через Bridge) [provider: пресс-релиз 17.02.2026]. Для Молдовы — нет данных; аккаунта у владельца нет.
- **Code4rena** — сворачивается с 13.05.2026, клиентов и исследователей забирает Immunefi [press: The Block, 13.05.2026; X Code4rena].

---

## 2. Прямой приём крипты за свои продукты (b)

| Сервис | Молдова | Комиссия | Расчёт | Статус / риск |
|---|---|---|---|---|
| **CoinGate** | Да (база, страница от 22.05.2026) | 1% [vendor/provider pricing] | EUR (SEPA от €50 бесплатно, база) или USDC на свой кошелёк; USDT снят после MiCA [vendor: обзоры 2026, проверить на coingate.com] | Лицензированный провайдер из Литвы. **Лучший выбор для чекаута**. Вывод в банк упирается в лимит 50 000 лей |
| **Bybit Pay Send & Receive** | Для KYC-пользователей из поддерживаемых стран (Молдова у Bybit не ограничена — база) | «There will be no transaction fees charged by Bybit»; 1% при конвертации в USDT | Внутренний перевод по UID или QR. Лимиты: $30k за операцию, $40k в день, $100k в месяц, $400k в год [provider docs: FAQ Bybit Pay, 15.09.2026] | Годится, если у клиента есть Bybit. Статус merchant partner — по заявке |
| **MoonPay Commerce (бывший Helio)** | Нет данных | 2% (1% с HelioX Pass), свопы 0.25%, автоконвертация в фиат 0.5% [provider docs: docs.hel.io/docs/pricing-fees] | Крипта на кошелёк; поддерживает x402 | Страны мерчантов — проверить |
| **BTCPay Server (self-hosted)** | Не зависит от страны | 0 комиссий, некастодиальный [provider docs: FAQ BTCPay] | BTC и Lightning; альткоины — через плагины. Стейблкоины — проверить | Флот может поднять на Hetzner. KYC нет — но AML-обязанности это не снимает [интерпретация] |
| **x402 (свой API)** | Не зависит (USDC на свой адрес) | CDP Facilitator: 1 000 оплат в месяц бесплатно, дальше $0.001; проверка верификации бесплатна; KYT/OFAC-скрининг [provider docs: docs.cdp.coinbase.com] | USDC на Base, Polygon, Arbitrum, Solana | Нужен ли аккаунт CDP и доступен ли он Молдове — проверить. Есть альтернативные фасилитаторы |
| **Binance Pay merchant** | Молдовы нет в списке ограничений B2C [provider docs, 28.05.2026] | Нет данных | — | Аккаунта Binance у владельца нет |
| **Stripe stablecoin payments** | **Нет**: приём — бизнесам в US, private preview — ЕС, HK, MX, CH [provider docs] | — | — | Тупик |
| **Coinbase Commerce / Business** | **Нет**: только US и Сингапур [vendor/press, выдержка] | — | — | Тупик |
| **NOWPayments** | **Риск**. ToS FD Transfers LLC (Сент-Винсент, обновлено 31.08.2026): «not rendered to residents… of the EU, UK, USA, UAE… Russian Federation, or any jurisdiction where the use of cryptocurrency services is restricted or prohibited by applicable law» [provider docs] | — | — | В Молдове услуги с виртуальными активами запрещены (308/2017) → формально подпадает. Не использовать |
| **Cryptomus** | — | — | — | **Ловушка**: FINTRAC оштрафовал Xeltox Enterprises (Cryptomus) на C$176 960 190 за 2 593 нарушения, в том числе за неподачу STR по CSAM, ransomware, обходу санкций [official: fintrac-canafe.canada.ca, 22.10.2025; штраф наложен 16.10.2025]. Компания подала апелляцию [press: Globe and Mail] |
| **Request Finance** | Счета — да; бизнес-счёт с KYB — нет данных | План Free — $0 (неограниченные инвойсы в стейблкоинах или фиате). Starter — $50 в месяц, выход в фиат 1% + $10 (локальный перевод) или $30 (SWIFT) [provider docs: requestfinance.com/pricing, 26.09.2026] | Клиент платит на ваш кошелёк | Удобно для B2B-инвойсов в USDC |

---

## 3. Право Молдовы (c)

### 3.1 Закон 308/2017 (действует) — лимит 50 000 лей
- Ст. 4(1^1): оказывать услуги с виртуальными активами на территории Молдовы запрещено, в том числе «auxiliară/suplimentară» к основной деятельности (база `STATUS.md`; подтверждено пояснительной запиской правительства [official: gov.md, проект 338/MF/BNM/2026, апрель 2026]).
- Лимит — официальная формулировка из пояснительной записки [official]: «respectarea de către entitățile raportoare a limitei de 50 000 de lei pe parcursul unei luni la efectuarea tranzacțiilor de către clienții rezidenți **în/din adresa** prestatorilor de servicii privind activele virtuale autorizați în alte state **cu condiția deschiderii conturilor speciale**».
  - Лимит **двусторонний**: касается и зачислений от биржи в банк Молдовы.
  - Нужен **специальный счёт** в банке.
  - 50 000 / 17.7706 ≈ **$2 814 в месяц** [оценка по курсу НБМ от 25.09.2026].
- С 28.10.2022 действует циркуляр НБМ: банкам и небанковским PSP прекратить посредничество в платежах на крипто-платформы и из них [official: там же].
- **Не установлено:** считается лимит по всем банкам или по одному; распространяется ли на юрлица (формулировка «clienții rezidenți» — [интерпретация]: вероятно, да); как открывается «специальный счёт» в OTP → **к юристу и в OTP письменно**.

### 3.2 Закон о рынке криптоактивов (2026)
- **Номер:** «Law No. 180 from August 24» [press: tuk.md, 17.09.2026]. Это единственный источник → **проверить по Monitorul Oficial**. Дата сходится со вторым чтением 24.08 (база).
- **Промульгация и публикация:** указ 773-X от 14.09.2026; опубликован в Monitorul Oficial 17.09.2026 [press: moldpres.md, 17.09.2026; logos-pres.md].
- **Вступление в силу — расхождение:**
  - заголовок Moldpres: «a fost publicată… și a intrat în vigoare»;
  - текст той же новости и logos-pres: через 6 месяцев, **17.03.2027**;
  - ст. 104(1) проекта: «Prezenta lege intră în vigoare în termen de 6 luni de la data publicării» [official: проект, апрель 2026];
  - Legitimus и tuk.md — «июнь 2027»: это оценка, сделанная до принятия закона.
  - **Доверяем 17.03.2027:** так следует из текста статьи проекта, и так пишут два СМИ; заголовок Moldpres противоречит тексту самой новости.
- **Модель — MiCA:**
  - надзор — CNPF (кроме e-money токенов, их регулирует НБМ);
  - CASP — только SRL или SA с офисом в Молдове (ст. 53);
  - штрафы — до 15% оборота [official: проект; press].
- **Зарубежные биржи (ст. 55 проекта).** Без авторизации можно обслуживать резидента, только если услугу он запросил «la inițiativa sa exclusivă». Любая реклама на Молдову это исключение снимает [official: проект].
  - Риск [оценка]: после 17.03.2027 Bybit/BingX могут перестать регистрировать или обслуживать резидентов Молдовы. Для сравнения — пример Binance в ЕС [vendor: datawallet, «с 01.07.2026 Binance не обслуживает резидентов ЕС» — проверить].
- **Оплата криптой за товары и услуги:**
  - Министр финансов Андриан Гаврилицэ, 15.01.2026: «plățile cu criptomonede pe teritoriul țării nu vor fi permise» — по аналогии с запретом расчётов в валюте внутри страны [press: bancamea.md, 15.01.2026].
  - Europa Liberă, 05.08.2026: магазин или ресторан «nu are voie să afișeze prețurile în Bitcoin sau să accepte criptomonede direct în casa de marcat»; можно через авторизованных процессоров с конвертацией в леи [press]. Point.md, 07.08.2026 — то же.
  - В тексте проекта (апрель 2026) явного запрета **нет**: grep по «mijloc de plată», «plăți», «interzi…» ничего не нашёл [official: проект; интерпретация]. Итоговый текст закона не прочитан.
  - Вывод [интерпретация]: запрет касается **внутренних** расчётов (резидент ↔ резидент на территории страны). Получение USDC от иностранного клиента или платформы за экспорт услуг законом прямо не урегулировано → **серая зона, к юристу**.
- **Налоги:**
  - В законе налоговых норм нет. Пояснительная записка прямо говорит, что нужно менять Codul fiscal отдельно; правительство должно внести предложения в течение 6 месяцев (ст. 104(4)) [official: проект].
  - Пресса:
    - физлица — налогом облагается половина прибыли по ставке 12%, то есть фактически 6% [press: Europa Liberă, 05.08.2026] — это совпадает с текущим режимом прироста капитала;
    - компании — 12% [press];
    - «если выводишь в банк Молдовы — декларируешь в ГНС» [press].
  - Налоговая политика 2027 (в парламенте): прирост капитала — 12% со всей суммы (база) → выгода 50% может пропасть.
  - Крипта, полученная как **оплата за услуги**, — это, скорее всего, обычный доход по рыночной стоимости на дату получения, а не прирост капитала [интерпретация; к бухгалтеру].
  - Разъяснение Monitorul Fiscal о налоге при продаже криптовалюты физлицом (28.12.2023 — **старше 2025 года**) — за платной подпиской, не прочитано.

### 3.3 DAC8 и CARF
- **DAC8** действует в ЕС с 01.01.2026 (база). Отчитываются CASP из ЕС о пользователях — резидентах стран ЕС. Резидент Молдовы — не «reportable user» по DAC8 [интерпретация]. Указывать немецкий адрес — ловушка (база, раздел 2.7).
- **CARF:** Молдовы **нет** в списке OECD «Jurisdictions committed to implement the CARF» (обновлён 14.09.2026: 46 стран — обмен к 2027, 27 — к 2028, 4 — к 2029, 4 не взяли обязательств) [official: oecd.org]. Нет её и в CARF-MCAA (статус на 03.03.2026) [official]. Автоматического обмена данными о крипте с Молдовой пока нет. Это не отменяет обязанность декларировать доход.
- ОАЭ (юрисдикция Bybit) — обмен по CARF к 2028 [official]. Если Молдова присоединится позже, данные пойдут.

### 3.4 Физлицо vs SRL (IT Park)

| Вопрос | Физлицо-резидент | Global Web SRL (IT Park) |
|---|---|---|
| Получать USDC за услуги или продукт от иностранного клиента или платформы | Прямого запрета нет. Запрет 308/2017 — на *оказание VASP-услуг* [интерпретация]. Серая зона | **Не рекомендуется.** Закон 62/2008: юрлица проводят платежи по валютным операциям только через банковские или платёжные счета [official, по выдержке из вопросов и ответов НБМ / BNM]; для аудита MITP нужно подтверждение оплаты (`it_park_verified.md`) |
| Налог | 12% как обычный доход (если без регистрации — законность под вопросом, база). Для antreprenor independent нужен выделенный счёт у молдавского PSP — крипта в режим не вписывается (база) | 7% с оборота, если доход признан и задокументирован. Как учитывать крипту — национального стандарта нет, нет данных → к бухгалтеру |
| Вывод в MDL/EUR | ≤ 50 000 лей в месяц через специальный счёт | Та же норма «clienții rezidenți», вероятно [интерпретация] |
| Риск после 17.03.2027 | Биржи могут уйти (ст. 55) | То же + лицензирование CASP |

**Рекомендация [интерпретация]:**
- IT-выручка (SaaS, софт, Apify, Upwork-разработка) → SRL, фиат на OTP.
- Крипто-ниши (раздел 5) → физлицо, стейблкоины на Bybit/BingX или свой кошелёк; траты — BingX Card; вывод в MDL — в пределах 50 000 лей в месяц.
- Перед масштабом свыше ~$2 800 в месяц — юрист.

---

## 4. Легальный вывод крипта → MDL/EUR и его цена (d)

| Путь | Статус для Молдовы | Стоимость | Уверенность |
|---|---|---|---|
| Bybit → SEPA/SWIFT → OTP | **Нет**: ограничено для Молдовы (база, 18.09.2026) | — | Высокая |
| BingX → SEPA | **Нет**: SEPA только для 32 стран ЕЭЗ и Швейцарии, Молдовы нет [provider docs: FAQ BingX SEPA] | Для доступных стран: 0.035% + €0.28 | Высокая |
| BingX Card (Visa, Wirex) | Да, только траты (база) | 1% + 1% FX + 1.5% (суммируются ли — проверить, база) | Средняя |
| Bybit → свой Kraken → SEPA (Bank Frick и др.) → OTP (Молдова в SEPA) | **Проверить малой суммой.** Kraken: SEPA (Bank Frick) €1, минимум €2; SWIFT USD $14, минимум $100; SWIFT EUR €5, минимум €100 [provider docs: support.kraken.com, 03.09.2026]. «Availability… may be limited to specific regions»; Bank Frick «not available to restricted countries». Молдовы нет в сторонних списках ограничений Kraken [vendor]; официальный список не прочитан. Кто обслуживает резидентов Молдовы в Kraken — не установлено | ~€1 + спред + сеть (~$1) [оценка] | Низкая–средняя |
| Bybit P2P USDT/MDL | Страница Bybit P2P для MDL есть [provider] | Спред — нет данных | Не рекомендуется: AML и «треугольные» мошенничества (база). Вне банковского лимита формально, но с риском блокировки счёта |
| Request Finance Business: off-ramp | KYB для Молдовы — нет данных | 1% + $10/$30 (Starter, $50 в месяц) [provider docs] | Низкая |
| Держать в USDC/USDT | Без ограничений | Только сетевые комиссии | Решение пользователя: крипты достаточно |

**Ориентир:** реальный легальный вывод на OTP — ≈ $2 800 в месяц на человека, через специальный счёт [оценка]. Всё сверх этого — траты с карты или хранение в стейблкоинах.

---

## 5. Кандидаты: ниши, которые существуют только или лучше всего работают благодаря крипто-выплате

Формула ранга: **P(первый $ ≤ 30 дней) × потолок на 6-й месяц / часы владельца в неделю**. Все множители — [оценка].

### 5.1 Таблица A — ниша и деньги

| ID | Ниша (формат × тема × рынок) | Что продаём | Монетизация | Выплата | Крипта |
|---|---|---|---|---|---|
| CR-01 | Global-баунти Superteam Earn: код, демо, агентные скиллы, технические гайды для экосистемы Solana (EN) через официальный агентный API + профиль владельца | Работы на баунти (PR, демо, доки) | Призы в USDC/USDG | Кошелёк Solana → Bybit (поддержку USDG проверить) | yes |
| CR-02 | Технический SEO/GEO с внедрением для Web3-инфраструктуры (кошельки, dev-tools, сайты документации L2) — EN, асинхронно | Фикс-пакеты: schema, CWV, индексация, llms.txt, AI-crawler audit | $300–1 500 за проект, ретейнер | Contra (USDC ERC-20, 2%/1%) + прямые инвойсы в USDC/USDT (Request Finance Free) → Bybit | yes |
| CR-03 | Платные по вызову SEO- и веб-API для ИИ-агентов через x402 (CrUX CWV lookup, аудит robots.txt для AI-краулеров, валидатор schema) + зеркало в Apify | Вызов API | $0.005–0.05 за вызов в USDC | USDC (Base/Solana) на свой адрес | yes |
| CR-04 | Telegram-бот «аудит сайта по ссылке» (SEO + скорость + доступность) для малого бизнеса RO/UA/KZ/RU, отчёт на RU/RO | Пакеты отчётов | 50–150 Stars за отчёт | Stars → Fragment → TON → Bybit (холд 21 день) | yes |
| CR-05 | Open-source dev-tools для Solana (GitHub Action — валидатор метаданных Blinks/Actions и OG/SEO) под крипто-гранты: Superteam Global и Gitcoin | OSS + отчёты по грантам | Гранты в USDG/USDC | Кошелёк | yes |
| CR-06 | Аудит-конкурсы Web3 и баг-баунти (Sherlock, Cantina, Immunefi): флот делает статический анализ и LLM-триаж, владелец фильтрует | Находки (issues) | Доля призового фонда в USDC | Кошелёк | yes |
| CR-07 | Безликие видео-объяснялки (60–120 с) о протоколах Solana для видео-баунти Superteam Global, EN (готовый конвейер: сценарий → картинки → TTS → ffmpeg) | Видео | Призы в USDC | Кошелёк | yes |
| CR-08 | Безликий Telegram-канал на EN «AI coding tools digest» с рекламной долей Telegram (50% в TON) | Контент-канал | Ads revenue share в TON | Fragment → TON → Bybit | yes |

### 5.2 Таблица B — доказательства, осуществимость, тест, экономика

| ID | Спрос (2025–2026) | Конкуренция | Флот без лица и GPU | 14-дневный тест | Дней до $ | P30 | Потолок на 6-й месяц [оценка] | Часы/нед |
|---|---|---|---|---|---|---|---|---|
| CR-01 | 606 закрытых стейблкоин-листингов на ≈$1.99 млн за 12 месяцев; выборка 189: Global — 58% листингов и 63% призов. Dev-баунти 2026: 94, медиана приза $1 000 [provider data: API superteam.fun, 26.09.2026]. Грант «Agentic Engineering» — Global, $200, одобрено $62.2k на 311 получателей, сейчас приём на паузе [provider data] | Высокая: у Global-баунти медиана 105 заявок; dev — 41.5 заявки и ~$14.6 приза на заявку. Треды в X — $2.3 на заявку (не брать). Открыто всего 2 листинга `AGENT_ALLOWED` из 26 | Да: код, тесты, демо, доки. Владелец — профиль, claim, KYC, контакт в Telegram | Флот ежедневно сканирует Global и `AGENT_ALLOWED`, отправляет 6–8 dev- и док-заявок; владелец проверяет каждую | 21–45 | 0.2 | 10 заявок × $14.6 × 2 (качество) ≈ **$290** | 3 |
| CR-02 | web3.career: 71 SEO-вакансия в Web3 (сентябрь 2026) [vendor: job board]; 133 в мае 2026 [выдержка]; у Crypto.com — 6 SEO-ролей (февраль 2026). У Superteam SEO-листингов за 12 месяцев всего 2 → спрос в основном вне баунти | Web3-SEO-агентства есть; число — нет данных | Частично: аудит и код — флот; переписка EN асинхронно; финальная проверка — владелец (15+ лет SEO) | Профиль Contra + 3 фикс-пакета; лендинг «Web3 technical SEO»; 15–20 откликов на контрактные или парт-тайм роли без звонков; **без холодных рассылок** | 14–30 | 0.2 | 2 проекта × $750 + 1 ретейнер $500 = **$2 000** | 8 |
| CR-03 | x402: >100 млн транзакций на Base к концу I кв. 2026; на транзакции от $1 приходится 95% объёма [press/analytics: Chainalysis, 03.06.2026]. Доход отдельного продавца — нет данных | Нет данных (x402scan требует JS) | Да: тот же код, что для Apify actors | Задеплоить 3 эндпоинта с x402 (CDP или альтернативный фасилитатор), описать для x402 Bazaar и MoonPay Commerce x402 | 7–14 | 0.3 | 5 000 вызовов × $0.02 = **$100** | 1 |
| CR-04 | Telegram >1 млрд MAU [press 2026]; по нише — нет данных | Нет данных | Да | Бот + 3 пакета Stars; посевы в своих каналах и чатах по правилам; RU не основной рынок | 25–40 (холд 21 день) | 0.1 | 150 покупок × 100 Stars × $0.013 = **$195** | 2 |
| CR-05 | GG24: ~$1.8 млн (октябрь–ноябрь 2025) [provider]; «Agentic Engineering»: 311 грантов по $200 [provider data]. Региональные гранты Solana Foundation до $10k — **Молдова не покрыта** | Нет данных | Да | Выпустить OSS-инструмент, подать на все Global-гранты | 30–90 | 0.05 | Гранты неравномерны: ~$150 в месяц в среднем | 2 |
| CR-06 | Доступно >$162 млн в Web3 баг-баунти (март 2026) [vendor: блог Sherlock]; Code4rena закрыт 13.05.2026 [press] | Очень высокая, конкурсы «шумные» [vendor/medium 2026] | Частично: нужна экспертиза Solidity/Rust, которой у владельца нет | 1 конкурс Sherlock в режиме «только наблюдать»: сравнить находки флота с итоговым отчётом | 45–90 | 0.03 | **$200**, дисперсия огромная | 6 |
| CR-07 | Видео-баунти за 12 месяцев: 61, $87.5k, медиана приза $800, ~$20.3 на заявку. Global-выборка: медиана $550, 98 заявок, $7.8 на заявку [provider data] | Высокая | Да (конвейер уже есть); часть баунти требует постить в свой X | 4 видео на Global-баунти (правила об ИИ-контенте проверить) | 21–45 | 0.1 | 8 заявок × $15 = **$120** | 2 |
| CR-08 | Доля 50% от рекламы Telegram, порог 1 000 подписчиков [official 2024 — старше 2025]; CPM $1–10+ [vendor 2026] | Высокая | Да | Канал + 30 постов; без накрутки (исключение проекта) | 60+ | 0.02 | 180k просмотров × $1.5 CPM × 50% × 50% заполняемость = **$67** | 1 |

**Ранг** (P × потолок / часы):
1. CR-02 — 50;
2. CR-03 — 30;
3. CR-01 — 19;
4. CR-04 — 10;
5. CR-07 — 6;
6. CR-05 — 3.8;
7. CR-08 — 1.3;
8. CR-06 — 1.

**Почему именно крипта:**
- CR-02 — Web3-клиенты платят в стейблкоинах, а SEO — не IT-доход, так что его лучше держать вне SRL;
- CR-03 — агентские микроплатежи возможны только в стейблкоинах;
- CR-01, CR-05, CR-06, CR-07 — призы выплачиваются только в крипте;
- CR-04, CR-08 — Telegram платит только в TON.

**Риски по кандидатам:**
- **CR-01:**
  - 42% листингов закрыты по регионам (у Молдовы нет чаптера);
  - ИИ-спам помечается и больше не редактируется (skill.md);
  - какой KYC-провайдер у Superteam и проходит ли Молдова — нет данных;
  - поддержка USDG на Bybit/BingX — проверить.
- **CR-02:**
  - многие вакансии — full-time со звонками;
  - исключить казино, prediction markets, мемкоины и «сигналы»;
  - крипто-оплата необратима: вне Contra нет эскроу → брать 50% предоплаты;
  - налог — серая зона.
- **CR-03:**
  - значительная часть объёма x402 — спекуляции (мемкоин PING, IV кв. 2025, Chainalysis);
  - слабая discovery;
  - копеечные суммы;
  - доступен ли аккаунт CDP для Молдовы — проверить.
- **CR-04:**
  - замедление Telegram в РФ (база);
  - покупка Stars из РФ может идти через серых посредников — не таргетировать РФ;
  - расхождение по KYC на Fragment (база).
- **CR-05:** программа грантов на паузе; региональные гранты Молдове недоступны; репозиторий TON grants-and-bounties заархивирован 20.05.2026 [provider/выдержка].
- **CR-06:** нет экспертизы; ложные находки портят ratio; для Sherlock нужно ≥20% валидных; в Immunefi KYC от $500.
- **CR-07:** в правилах баунти может требоваться свой аккаунт в X и охват.
- **CR-08:** без накрутки 1 000 подписчиков набираются медленно.

---

## 6. Матрица рельсов: источник → платит ли криптой → комиссия → минимум → KYC → законность → уверенность

Законность — [интерпретация]; «ФЛ» — физлицо-резидент, «SRL» — Global Web SRL.

| Источник | Крипта | Комиссия | Минимум | KYC | ФЛ | SRL | Уверенность |
|---|---|---|---|---|---|---|---|
| Creem | Да, USDC (Polygon) | 2% от выплаты | $50/€50 | Да, KYC/KYB | Серая зона, не запрещено | Лучше банк ($7 или 1%) | Высокая (docs) / средняя (право) |
| Contra | Да, USDC (ERC-20); MD = YES | 2% (Pro — 1%) | Нет данных | Да | Серая зона | Лучше Local bank через Stripe (для MD = YES) | Высокая (таблица провайдера, дата неизвестна) |
| Deel | Да, USDC/USDT, много сетей | 2% + $1 | $5 | Да + Proof of Location для части граждан | Серая зона | Банк (SWIFT $5–10, минимум $100) | Средняя (страна не подтверждена) |
| Superteam Earn | Да, USDC/USDG | Нет данных | — | KYC для листингов Superteam/Solana | Серая зона | Не подходит | Высокая (docs + API) |
| Sherlock / Cantina / Immunefi | Да, USDC / крипта | — | ≥2 валидных находки (Sherlock) | Immunefi — от $500 | Серая зона | Не подходит | Средняя |
| Gitcoin и крипто-гранты | Да | — | — | Паспорт Gitcoin и др. | Серая зона | Не подходит | Средняя |
| Telegram Stars / реклама | Да, TON | Stars ~$0.013 (база) | 1 000 Stars [vendor, база] | Fragment — расхождение (база) | Серая зона | Бот — IT, но документы для аудита проблемны (база) | Средняя |
| x402 | Да, USDC | Фасилитатор: 1 000 бесплатно, дальше $0.001 | — | KYT по адресам; аккаунт CDP — проверить | Серая зона | Не подходит | Средняя |
| Bybit Pay Send & Receive | Да | 0 (1% при конвертации) | — | KYC Bybit | Серая зона | Не подходит | Высокая (FAQ 15.09.2026) |
| CoinGate (свой чекаут) | Да, расчёт в USDC или EUR | 1% | Вывод EUR от €50 (база) | KYB/KYC | Серая зона | EUR на OTP — возможно, в пределах лимита и через специальный счёт (проверить) | Средняя |
| MoonPay Commerce | Да | 2% (1%) | — | Нет данных | Серая зона | — | Низкая (страна) |
| BTCPay Server | Да (BTC/LN) | 0 | — | Нет | Серая зона | Не подходит | Высокая (технически) |
| Stripe Global Payouts USDC (от US-платформ) | Да (private preview) | Нет данных | — | Требования платформы | Серая зона | — | Средняя |
| Payoneer (стейблкоины) | Анонсировано, Q2 2026+ | Нет данных | — | Да | — | — | Низкая |
| Polar, Dodo, Lemon Squeezy, Gumroad, Upwork, Algora | Нет | — | — | — | Фиат | Фиат | Высокая |
| Whop (Coinbase), Stripe stablecoin (приём и Connect), Coinbase Business | Нет для Молдовы | — | — | — | — | — | Высокая |
| NOWPayments | Формально исключает | — | — | — | Риск по ToS | — | Средняя |
| Code4rena | Закрыт | — | — | — | — | — | Высокая |

---

## 7. Ловушки и тупики (с доказательствами)

1. **Cryptomus** — рекордный штраф FINTRAC C$176.96 млн; компания не подавала отчёты о подозрительных операциях по CSAM, ransomware и обходу санкций [official, 22.10.2025]. Не использовать ни для приёма, ни для обмена.
2. **NOWPayments** — ToS от 31.08.2026 исключает юрисдикции, где крипто-услуги «restricted or prohibited by applicable law». Молдова (308/2017) под это подпадает. Сущность — в Сент-Винсенте [provider docs].
3. **Крипто-выплаты Whop** — только через Coinbase Commerce и только за покупки криптой; Coinbase Business — только US и Сингапур [provider docs + выдержка]. Тупик.
4. **Stripe stablecoin: Connect и приём** — MD нет в списках; Connect работает только с US-платформами и только с физлицами [provider docs].
5. **Вывод через Bybit и BingX SEPA** — Молдовы нет (база + FAQ BingX). Не пытаться указать адрес в ЕС — это ложное резидентство (исключение проекта; DAC8 — база 2.7).
6. **P2P USDT/MDL как основной канал** — риск AML и приёма «грязных» денег от контрагента; банк может заблокировать счёт (база). Лимит 50 000 лей формально обходится, но по сути это обход контроля → не рекомендуется.
7. **Крипта на счёт SRL** — противоречит правилу «платежи юрлиц только через счета» (закон 62/2008, выдержка) и усложняет аудит IT Park [интерпретация].
8. **Сделать ставку на биржу после 17.03.2027** — ст. 55 (reverse solicitation): зарубежные биржи могут ограничить Молдову. Держать часть средств в self-custody, иметь 2 биржи [оценка риска].
9. **X-треды на Superteam** — ~$2.3–3.8 приза на заявку при 128–142 заявках [provider data]. Работа за копейки; и для контента нужен свой охват.
10. **Code4rena** — закрыт 13.05.2026 [press]. Старые гайды «как заработать на C4» устарели.
11. **TON Footsteps / grants-and-bounties** — репозиторий заархивирован 20.05.2026 [provider GitHub, по выдержке] → программа, видимо, изменилась; проверить перед ставкой на TON-баунти.
12. **«Лучшие крипто-шлюзы» из партнёрских подборок** (passimpay, eco.com, 0xprocessing и т. п.) — не доказательство доступности для Молдовы; использовались только страницы провайдеров.

---

## 8. Что не удалось проверить

- Итоговый текст закона о рынке криптоактивов: номер 180 от 24.08.2026 (один источник), статья в Monitorul Oficial, есть ли в финальной редакции запрет на расчёты криптой и изменения 308/2017 (отмена ст. 4(1^1) и 5(4^4)). Прочитан только проект правительства (апрель 2026).
- Полный текст ст. 5(4^4) закона 308/2017 и закона 62/2008 (legis.md и bnm.md недоступны: 403/503). Лимит и «специальные счета» взяты из пояснительной записки правительства и поисковой выдержки legis.md.
- Как OTP открывает «специальный счёт» для операций с VASP; считается ли лимит по всем банкам и распространяется ли на SRL.
- Налог на крипту, полученную как оплата услуг (обычный доход или прирост капитала); учёт крипты в SRL (стандарта или разъяснения ГНС не найдено; статья Monitorul Fiscal от 28.12.2023 за платной подпиской).
- Входит ли Молдова в CRS (выдержка «joined as a full participant in 2025» — источник не открыт).
- Deel stablecoin: есть ли Молдова в «eligible countries».
- Superteam: KYC-провайдер и допуск Молдовы; поддерживает ли Bybit/BingX депозиты USDG (Solana) и USDC (Polygon).
- Kraken: кто обслуживает резидентов Молдовы и доступна ли им Bank Frick SEPA; официальный список ограниченных стран.
- MoonPay Commerce, Binance Pay — комиссии и допуск молдавских мерчантов; BTCPay — стейблкоин-плагины.
- Нужен ли аккаунт Coinbase CDP для x402 и доступен ли он Молдове; реальные доходы продавцов x402.
- Cantina и Immunefi — актуальные правила KYC и выплат (страницы 403).
- Payoneer stablecoin — в каких странах запущен.
- Число Web3-SEO-вакансий, которые допускают асинхронную работу без звонков.
- Действующая страница CoinGate о расчёте в USDC и снятии USDT (есть только вторичные обзоры).

---

## 9. Источники (все прочитаны или открыты 26.09.2026, если не указано иное)

**Право Молдовы и международное**
- Проект закона о рынке криптоактивов 338/MF/BNM/2026 с пояснительной запиской (апрель 2026) — https://gov.md/sites/default/files/media/documents/sedinte-de-guvern/2026-04/338-MF-BNM-2026.pdf [official]
- Moldpres, 17.09.2026 — https://www.moldpres.md/rom/economie/doc-legea-privind-piata-criptoactivelor-a-fost-publicata-in-monitorul-oficial-si-a-intrat-in-vigoare [press]
- Logos-Press, ~17–18.09.2026 — https://logos-pres.md/en/news/the-law-on-the-crypto-asset-market-will-come-into-force-on-17-march-2027/ [press]
- TUK.md, 17.09.2026 — https://tuk.md/vse-jasno/razbory/kriptovaljutu-v-moldove-legalizovali-razbiraem-novyj-zakon-o-rynke-kriptoaktivov/ [press]
- Bancamea.md, 15.01.2026 (заявление министра) — https://bancamea.md/news/moldova-va-avea-lege-pentru-criptomonede-in-2026-dar-fara-plati-cripto-1582 [press]
- Europa Liberă Moldova, 05.08.2026 — https://www.europalibera.md/a/bitcoin-la-bancomat-si-taxe-pe-castiguri-cum-vor-fi-reglementate-criptomonedele-in-moldova/33822503.html [press]
- Point.md, 07.08.2026 — https://point.md/ru/novosti/ekonomika/v-moldove-razreshat-kriptobankomaty-bitkoinom-mozhno-budet-platit-v-kafe/ [press]
- Legitimus.md (до принятия, дата не указана) — https://www.legitimus.md/ru/articles/proekt-zakona-o-kriptoaktivakh-v-moldove-2026-licenzija-trebovanija [vendor]
- LP308/2017, поисковая выдержка — https://www.legis.md/cautare/getResults?doc_id=146050&lang=ro [official, страница за Cloudflare]
- Delucru.md, 04.12.2024 (**старше 2025 года**) — https://www.delucru.md/articles/sunt-sau-nu-interzise-criptomonedele-in-republica-moldova [press]
- Закон 62/2008 (страница НБМ, 503; использована выдержка) — https://www.bnm.md/ro/content/legea-nr62-xvi-din-21-martie-2008-privind-reglementarea-valutara-cu-modificarile-conform [official]
- Monitorul Fiscal, 28.12.2023 (**старше 2025 года**, за платной подпиской) — https://monitorul.fisc.md/regimul-de-impozitare-a-venitului-obtinut-de-persoana-fizica-rezidenta-a-republicii-moldova-din-instrainarea-criptovalutei/
- OECD, CARF commitments, 14.09.2026 — https://www.oecd.org/content/dam/oecd/en/networks/global-forum-tax-transparency/commitments-carf.pdf [official]
- OECD, CARF-MCAA signatories, 03.03.2026 — https://www.oecd.org/content/dam/oecd/en/topics/policy-issues/tax-transparency-and-international-co-operation/carf-mcaa-signatories.pdf [official]
- FINTRAC, 22.10.2025 — https://fintrac-canafe.canada.ca/new-neuf/nr/2025-10-22-eng [official]

**Провайдеры (выплаты)**
- Creem, payouts (дата не указана) — https://docs.creem.io/merchant-of-record/finance/payouts [provider docs]
- Contra, crypto payout fee, 12.05.2026 — https://help.contra.com/en/articles/13119448-crypto-payout-fee [provider docs]
- Contra, payout methods, 26.03.2025 — https://help.contra.com/en/articles/9322938-payout-methods-for-freelancers-on-contra ; таблица стран (Notion, дата не указана) — https://www.notion.so/contrahq/9b8855f93eca48c39dca4b6bacbb1e70 [provider docs]
- Deel, Stablecoins Transfer, 29.07.2026 — https://help.letsdeel.com/hc/en-gb/articles/23524211726481 ; комиссии, 15.04.2026 — https://help.letsdeel.com/hc/en-gb/articles/14391381019537 [provider docs]
- Superteam Earn FAQ — https://docs.superteam.fun/the-superteam-handbook/community/faqs/superteam-earn-faq ; агенты — https://superteam.fun/earn/agents/ и https://superteam.fun/skill.md ; API листингов и грантов — https://superteam.fun/api/listings , https://superteam.fun/api/grants ; регион Balkan — https://superteam.fun/earn/regions/balkan/ [provider docs / provider data]
- Stripe, stablecoin payouts for Connect — https://docs.stripe.com/connect/stablecoin-payouts ; приём стейблкоинов — https://docs.stripe.com/payments/stablecoin-payments ; Global Payouts — https://docs.stripe.com/global-payouts/recipient-requirements [provider docs]
- Polar, payouts — https://polar.sh/docs/features/finance/payouts [provider docs]
- Dodo Payments, payouts и страны — https://docs.dodopayments.com/features/payouts/payout-structure , https://docs.dodopayments.com/miscellaneous/accepted-countries-and-territories ; changelog 1.97.6, 07.05.2026 [provider docs]
- Whop, payout methods — https://docs.whop.com/manage-your-business/manage-payouts/payout-methods [provider docs]
- Payoneer, пресс-релиз 17.02.2026 — https://www.payoneer.com/press/payoneer-to-launch-stablecoin-capabilities-powered-by-bridge-bringing-secure-always-on-digital-money-to-global-businesses/ [provider]
- Sherlock, payout criteria — https://docs.sherlock.xyz/audits/watsons/meeting-the-payout-criteria [provider docs]; обзор рынка баунти, март 2026 — https://sherlock.xyz/post/best-web3-bug-bounties-in-2026-the-highest-paying-programs-on-every-platform [vendor]
- Immunefi, KYC (выдержка) — https://immunefisupport.zendesk.com/hc/en-us/articles/18327648101649-KYC-requirements [provider docs]
- The Block, 13.05.2026 (Code4rena) — https://www.theblock.co/news/regulation/2026-05-13-immufefi-absorb-code4rena-bug-bounty-customers-shutdown-decision-401179 [press]
- Gitcoin GG24 — https://gitcoin.co/case-studies/gg24-first-funding-round-of-gitcoin-3-0 [provider]
- Telegram, монетизация каналов (2024, **старше 2025 года**) — https://telegram.org/blog/monetization-for-channels ; InviteMember 2026 — https://blog.invitemember.com/telegram-ads-in-2026-setup-costs-and-requirements/ [vendor]
- Getly / Fungies о выплатах Gumroad и Lemon Squeezy (2026) — https://www.getly.store/alternatives/gumroad , https://fungies.io/creem-vs-gumroad-vs-lemon-squeezy-2026/ [vendor]
- Algora — https://gigs.sh/p/algora [vendor]

**Чекауты и выход в фиат**
- Bybit Pay FAQ, 15.09.2026 — https://www.bybit.com/en/help-center/article/FAQ-Bybit-Pay [provider docs]
- Binance Pay Merchant B2C Restrictions, 28.05.2026 — https://www.binance.com/en/support/faq/detail/942c5c12e00b494e9bc3e2ab31f7da19 [provider docs]
- MoonPay Commerce, комиссии — https://docs.hel.io/docs/pricing-fees [provider docs]
- BTCPay Server FAQ — https://docs.btcpayserver.org/FAQ/General/ [provider docs]
- NOWPayments / FD Transfers LLC ToS, 31.08.2026 — https://nowpayments.io/doc/fd-tos.pdf [provider docs]
- Coinbase CDP x402 Facilitator — https://docs.cdp.coinbase.com/x402/core-concepts/facilitator [provider docs]; комиссия с 01.01.2026 — https://x.com/CoinbaseDev/status/1995564027951665551 [provider]
- Chainalysis, x402 on Base, 03.06.2026 — https://www.chainalysis.com/blog/x402-agentic-payments-adoption/ [press/analytics]
- Request Finance, pricing — https://www.requestfinance.com/pricing [provider docs]
- CoinGate, поддерживаемые страны — https://coingate.com/supported-countries (база, 22.05.2026) [provider docs]
- BingX, EUR через SEPA — https://bingx.com/en/support/articles/15111048067343 [provider docs]
- Kraken: вывод 03.09.2026 — https://support.kraken.com/articles/360000423043-cash-withdrawal-options-fees-minimums-and-processing-times- ; депозит 17.08.2026 — https://support.kraken.com/articles/360000381846-cash-deposit-options-fees-minimums-and-processing-times- ; Bank Frick 18.08.2026 — https://support.kraken.com/articles/360032773251-bank-frick-funding-provider [provider docs]
- Datawallet (Kraken, Binance EU) — https://www.datawallet.com/crypto/kraken-countries [vendor]
- web3.career, SEO-вакансии, сентябрь 2026 — https://web3.career/seo-jobs [vendor: job board]

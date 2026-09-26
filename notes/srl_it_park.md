# Поток «SRL и IT Park» — заметки исследования A

Дата: 26.09.2026. Курс НБМ на 25.09.2026: 1 USD = 17.7706 MDL (база проекта, `STATUS.md`).
Это исследование, а не юридическая или налоговая консультация.

**Ограничение метода.** Прокси-сервер сессии блокирует прямую загрузку страниц всех доменов `.md` (sfs.md, monitorul.fisc.md, legis.md, mitp.md, mf.gov.md, gov.md), а также pwc.com и kpmg.com. Поэтому все факты взяты из **выдержек поисковой выдачи** (заголовок и фрагмент страницы), а не из прочитанного полного текста. Метка [official] означает, что фрагмент принадлежит официальному сайту, но сама статья закона целиком не прочитана. Для решений всё нужно перепроверить по полному тексту — «verify».

Дата публикации у многих фрагментов не видна. Где она известна, она указана в списке источников.

> **Поправка 26.09.2026 (от пользователя): Global Web SRL уже резидент IT Park.** Исследователь исходил из того, что SRL в стандартном режиме, поэтому выводы TL;DR 3, 8, 9 и «практический вывод» про новую SRL в IT Park для Global Web SRL неприменимы. Что меняется:
> - Порог окупаемости IT Park уже пройден, минимум на работника платится в любом случае. Дополнительная IT-выручка облагается по **7%** — если 7% от оборота уже не меньше минимума [оценка, проверить с бухгалтером].
> - Льгота 0% на нераспределённую прибыль резидентам IT Park **не положена** (п. 1 ниже).
> - Дивиденды резидента IT Park: единый налог их, по всей видимости, не покрывает → 6% у источника (8% с 2027, если примут) — **проверить** по ст. 11 закона 77/2016.
> - НДС остаётся: экспорт услуг — 0% с вычетом.
> - **Главное ограничение — правило 70%.** YouTube AdSense, партнёрки, инфопродукты в IT-долю не входят. Потолок не-IT дохода внутри SRL ≈ IT-выручка × 30/70 [оценка]. Всё, что сверх, — угроза статусу резидента; такие доходы вести вне Global Web SRL (antreprenor independent на себя, 15%, или отдельная SRL) — проверить с бухгалтером.
> - SaaS, софт, расширения, API, мини-аппы, разработка (58.29, 62.01, 63.11) — вести через Global Web SRL под 7%.

---

## TL;DR

1. **Порог НДС уже не 1.5 млн, а 1.7 млн MDL с 01.03.2026** [press, несколько СМИ + VATupdate 25.02.2026]. Базу проекта нужно обновить. Добровольно сняться с учёта по НДС из-за оборота ниже порога **нельзя**: такое предложение отклонено [vendor: VATupdate 20.06.2026; verify].
2. **IVAO 4% для Global Web SRL недоступен.** Режим только для ÎMM, которые не зарегистрированы плательщиками НДС [official SFS + PwC]. Global Web SRL — плательщик НДС и сняться с учёта не может (п. 1). Чтобы получить 4%, нужна **новая SRL без НДС**. На 2027 год предложено ужесточение: доля консалтинга, при превышении которой 4% недоступен, снижается с 60% до 25% [press, verify].
3. **Стандартный режим SRL в 2026 году:** 12% налога на прибыль, но для ÎMM действует **0% на нераспределённую (реинвестированную) прибыль**, продлён на 2026 год законом 318 от 31.12.2025 [press/KPMG]. При выплате дивидендов 12% всё равно платится. Итог при изъятии денег: 12% + 6% × 0.88 = **17.28%**. Политика на 2027 год продлевает 0% до 2029 года и поднимает порог права на него со 100 до 200 млн MDL [press].
4. **НДС на экспорт услуг:** услуги по ст. 111(1)(e) НК (консалтинг, информационные, компьютерные, реклама, права ИС — перечень verify) нерезиденту — это экспорт услуг по **ставке 0% с правом на вычет** (ст. 104 lit. a) [official SFS, выдержка]. Это не «освобождено» и не «вне объекта».
5. **Дивиденды:** 6% окончательно у источника [official SFS/vendor]. На 2027 год предложено 8%: правительство одобрило 08.09.2026, парламент принял в первом чтении (по прессе 10.09.2026) [press]. Взносов на дивиденды нет. Дивиденды дешевле зарплаты: около 17% против около 32% на уровне минимальной зарплаты.
6. **IT Park:** 7% с продаж, но не меньше **30% × 17 400 = 5 220 MDL в месяц на каждого работника** в 2026 году [official SFS + press]. Проект повышения до 35% в итоговый закон **не вошёл** [vendor/press; verify]. Режим гарантирован до 2035 года; в политике на 2027 год его обещают не трогать [press].
7. **Главная проблема IT Park для этого оператора — правило 70%.** Выручка YouTube AdSense, партнёрские комиссии, реклама/SMM и инфо-/медиапродукты **не входят** в список CAEM ст. 8 закона 77/2016 [official-выдержка + vendor]. Подходят: собственный софт и SaaS (58.29, 62.01, 63.11), разработка на заказ, IT-консалтинг. Доля проверяется ежемесячно и за год.
8. **Порог рентабельности IT Park при одном работнике:** 7% × R = 5 220, то есть R ≈ 74 571 MDL ≈ **$4 196 в месяц** [estimate]. При $300 и $1 500 в месяц IT Park с работником невыгоден. Кроме того, есть обязательный ежегодный аудит (цена — нет данных) и членский взнос (формула есть, сумм нет).
9. **Сравнение при изъятии всей прибыли (без расходов) [estimate]:** SRL 12% + дивиденды = 17.28%; IVAO + дивиденды = 9.76% (только новая SRL без НДС); IT Park с 1 работником — 97.9% / 19.6% / 7.0% при $300 / $1 500 / $5 000; IT Park без работников (если допустимо — verify) = 12.58%.

---

## 1. Стандартный режим SRL: 12% или IVAO 4%

**12% налог на прибыль (general regime).**
- Ставка 12% [PwC taxsummaries, выдержка; vendor].
- **0% на нераспределённую прибыль для ÎMM** — продлено на 2026 год (закон 318, опубл. 31.12.2025) для ÎMM, которые не распределяют дивиденды и соблюдают отчётность [press: KPMG TaxNewsFlash 02.2026, выдержка].
  - Условия 2026: оборот или активы до 100 млн MDL, до 249 работников. Раздел G CAEM (торговля) — по более жёстким условиям.
  - Исключены: ÎI, крестьянские хозяйства, резиденты СЭЗ, **резиденты IT Park**, финансовый сектор [press/vendor: stiri.md, telegraph.md, Incorpore].
  - При выплате дивидендов 12% с прибыли, из которой они платятся, уплачивается до 25-го числа следующего месяца (ст. 80¹) [vendor: contabilsef.md, выдержка].
  - Эффективная ставка при распределении — 17.28% [vendor: Incorpore; формула проверена: 12% + 88% × 6%].
- Расходы (API, подрядчики, зарплаты) вычитаются. Это единственный из трёх режимов, где расходы уменьшают налог.

**IVAO (impozit pe venitul din activitatea operațională), ст. 54¹ НК.**
- 4% с операционного дохода, расходы не учитываются [official SFS, выдержка].
- Субъекты: ÎMM, **не зарегистрированные плательщиками НДС**.
  - Исключение для плательщиков НДС: когда >50% поставок освобождены от НДС **без права на вычет** и общий объём ≤ 1.5 млн MDL [press: mf.gov.md/monitorul.fisc.md о поправках 2026, выдержка].
  - К экспорту услуг это исключение не относится: экспорт идёт по ставке 0% **с правом** на вычет (раздел 2).
- Исключены ÎMM, у которых >60% выручки — консалтинг в сфере бизнеса и управления [vendor: dad.md, выдержка]. Предложение на 2027 год — снизить до 25% [press: moldovamatters.md/ logos-pres; verify].
- **Может ли Global Web SRL перейти на IVAO:** **нет**, пока она плательщик НДС.
  - Добровольная отмена регистрации при обороте ниже порога не предусмотрена, предложение отклонено [vendor: VATupdate 20.06.2026] — verify, ask accountant.
  - Вариант: **новая SRL**, не плательщик НДС, на IVAO — до порога НДС 1.7 млн MDL в год ≈ $95 700 в год ≈ $7 975 в месяц [estimate: 1 700 000 / 17.7706].
  - Экспорт по ставке 0% — облагаемые поставки, поэтому, видимо, входит в расчёт порога — verify.
  - Риск: дробление бизнеса или перевод выручки из Global Web SRL — ask accountant.
- Порог НДС:
  - 1.2 → 1.5 млн с 01.01.2026 (закон 318/2025);
  - 1.5 → **1.7 млн с 01.03.2026** [press: moldpres, agora 19.02.2026, VATupdate 25.02.2026; KPMG 03.2026 пишет о предложении повысить ещё — статус verify].
  - Источники расходятся: база проекта (1.5 млн) устарела; доверяем 1.7 млн — несколько независимых СМИ и налоговых вестников после голосования.

## 2. НДС на экспорт услуг

- **Правило.** Место поставки для услуг по ст. 111(1)(e) — место нахождения (или домицилий/резиденция) получателя. Если получатель вне Молдовы, это экспорт услуг, **ставка НДС 0% с правом на вычет** (ст. 104 lit. a; ст. 93 п. 11) [official: sfs.md «Locul livrării», baza generalizată nr. 10/19, выдержка; monitorul.fisc.md — «servicii de programare nerezidenților»].
  - Прямо названы: консалтинговые и информационные услуги, компьютерные услуги, услуги, оказанные электронными средствами, реклама [official-выдержки]. Полный перечень lit. (e), в том числе передача прав ИС, — verify по legis.md.
- **B2B и B2C.** Критерий в lit. (e) — «sediul, domiciliul sau reședința» получателя, то есть по формулировке годится и физлицо-нерезидент [interpretation — verify, ask accountant].
  - Услуги **вне** перечня lit. (e) подпадают под общее правило (место поставщика). Тогда НДС 20% — ask accountant для каждого вида дохода.
- **YouTube / Google AdSense.** Платит Google (для Европы — Google Ireland; YPP Google квалифицирует как роялти — `STATUS.md`). Для SRL это, по логике, предоставление прав или рекламная услуга нерезиденту, то есть экспорт 0%. **Молдавского разъяснения конкретно по YouTube не найдено** — verify, ask accountant.
- **MoR (Paddle, Creem, Polar, Lemon Squeezy).** По модели MoR платформа покупает продукт и перепродаёт его конечному покупателю от своего имени. Поэтому клиент SRL — **сам MoR** (иностранное юрлицо), и поставка — B2B-экспорт по ставке 0% [interpretation; модель MoR — provider docs в заметках A]. SRL не нужно определять страну каждого покупателя. Документы: договор или условия MoR, payout statements, инвойс SRL на MoR (или self-billing) — ask accountant.
- **Партнёрские комиссии** (посредничество / реклама нерезиденту) — вероятно, lit. (e), 0% — verify.
- Резидент IT Park **остаётся плательщиком НДС**, если зарегистрирован: 7% НДС не заменяет [vendor: Incorpore/ducont, выдержка].

## 3. Дивиденды и изъятие прибыли

- **2026 год:** 6% — окончательное удержание у источника с дивидендов физлицу-резиденту (ст. 90¹) [official: sfs.md baza generalizată nr. 81, выдержка; vendor: Incorpore].
- **2027 год (проект):** 8%.
  - Правительство одобрило 08.09.2026 [official: gov.md, mf.gov.md — заголовки].
  - Первое чтение в парламенте — 54 голоса [press: radiochisinau, ipn, logos-pres]; дата по выдержке — 10.09.2026, verify.
  - Второе чтение — нет данных.
- **Дивиденды резидента IT Park:** 7% их не покрывает, удержание у источника платится отдельно [vendor: dad.md]. Ставка, по-видимому, общая (6%) — verify.
- **Способы изъятия:**
  1. **Дивиденды.** Нет CNAS/CNAM. При 0% на реинвестиции — 12% при распределении + 6% = 17.28% (2027: 19.04%) [estimate].
  2. **Зарплата администратору** в SRL (общий режим). Пример при минимальной зарплате 6 300 MDL (2026) [press: gov.md, monitorul.fisc.md]:
     - работодатель платит CNAS 24% = 1 512; стоимость — 7 812;
     - работник платит CNAM 9% = 567;
     - налог на доход: 12% × (6 300 − 567 − 2 475 личной льготы) = 390.96;
     - на руки 5 342.04, нагрузка ≈ **31.6%** от стоимости для работодателя [estimate; формулы выше].
     - Зарплата уменьшает базу 12%, но при 0% на реинвестиции это почти не помогает.
     - Личная льгота 29 700 в год действует только при доходе ≤ 360 000 в год [vendor: buget.md/wizcontabil].
  3. **Зарплата в IT Park** — окончательно обложена 7%, дополнительных налогов нет [official-выдержка mitp.md FAQ].
- **Медстраховка владельца без зарплаты.** Если он нигде не застрахован, фиксированная премия CNAM на 2026 год — **12 636 MDL** (скидка при оплате до 31.03) [official: cnam.md 31.12.2025; press]. Нужна ли она учредителю-администратору без трудового договора — ask accountant.
- **Вывод:** в общем режиме SRL дивиденды выгоднее зарплаты (≈17% против ≈32%). Но без зарплаты нет пенсионного стажа — осознанный выбор владельца.

## 4. IT Park (Moldova IT Park, закон 77/2016)

| Параметр | Значение | Источник / уровень |
|---|---|---|
| Налог | единый налог 7% с дохода от продаж (ст. 369 НК) | [official] sfs.md baza generalizată 167; mitp.md |
| Что заменяет | налог на прибыль, подоходный налог с зарплат, CNAS, CNAM, налог на недвижимость, дорожный, часть местных | [vendor] Incorpore; [official-выдержка] mitp.md |
| Что не заменяет | НДС; удержания у источника (дивиденды, аренда, покупки у физлиц) | [vendor] dad.md, ducont |
| Минимум | 30% прогнозной средней зарплаты × число работников × месяцы; 2026: 17 400 × 30% = **5 220 MDL в месяц на работника** | [official] sfs.md 167; [press] contabilsef, incorpore |
| Кто считается работником | работавший ≥1 дня по **индивидуальному трудовому договору** с резидентом | [official] sfs.md 167 (выдержка) |
| Администратор | учредитель ÎI, который им же руководит, работником не является [official SFS]. **Администратор SRL** работником считается, только если с ним заключён трудовой договор — interpretation, verify. Можно ли быть резидентом с 0 работников и минимумом 0 — источники неясны: «любая компания, независимо от числа работников» и «при нулевом доходе платится минимум» [vendor]. Ask MITP/accountant | |
| 30% или 35% | 35% был в проекте правительства 2023 года (monitorul.fisc.md, newsmaker). По вендорам 2026 года, в итоговый закон **не вошёл**; 2026 считается по 30% [vendor/press]. Особое мнение: одна выдержка связывает 35% с законом 415 от 22.12.2023 (МО 12.01.2024). Доверяем 30%: так пишут расчёты SFS и нескольких бухгалтерий за 2026 год. Есть страница консультаций particip.gov.md «modificarea Legii 77/2016» (id 11116) — дата и содержание нет данных, verify | |
| Правило 70% | ≥70% выручки от продаж — из разрешённых видов деятельности, проверяется ежемесячно и за год (допускается до 2 месяцев несоблюдения в год — vendor) | [official-выдержка] mitp.md решения о ежегодной проверке; [vendor] Incorpore |
| Разрешённые CAEM (ст. 8) | 58.21 (издание игр), 58.29 (прочее ПО), 62.01, 62.02, 62.03, 62.09, 63.11 (обработка данных, хостинг), 63.12 (веб-порталы), 72.19 (НИОКР — verify), 85.59 (только IT-обучение); с 12.02.2024 — 82.20 (call-centre, только экспорт) и 78.30 (IT-staffing, только экспорт). Всего «17 кодов» по Incorpore — полный список verify по MITP «Ghid de eligibilitate 12.2024» | [press] monitorul.fisc.md; [vendor] |
| Форма | источники расходятся: «SRL или SA» (база проекта) и «SRL или ÎI» (fmd.md). Для оператора неважно — есть SRL | verify |
| Гарантия | до 2035 года (срок работы парка — до 2037); в политике на 2027 год режимы с гарантиями сохраняются; премьер Tofan: «режим IT Park не изменится» | [vendor] Incorpore; [press] logos-pres |
| 0% на реинвестиции | резидентам IT Park **не доступен** | [press] |
| Регистрация | онлайн-заявка через портал itpark.md/mitp.md, рассмотрение 10–15 рабочих дней, затем договор резидентства; 7% — со следующего месяца. Сама процедура бесплатна | [vendor] |
| Взнос резидента | первый месяц: **150 MDL** (mitp.md FAQ) или 50 MDL (другая выдержка). Доверяем 150 — официальный FAQ. Дальше MAX(бюджет MITP / прогнозный доход всех резидентов × прогнозный доход резидента / 12; минимальный месячный взнос). Сумма минимального взноса — **нет данных** | [official-выдержка] mitp.md |
| Аудит | обязательная ежегодная проверка (ISRS 4400, agreed-upon procedures) аудитором из реестра, за счёт резидента, для всех резидентов. Цена — **нет данных** (фирмы дают индивидуальную оценку) | [official-выдержка] mitp.md решения 135/2024; [vendor] |

**Подходят ли доходы оператора под правило 70%** (interpretation — ask MITP до подачи заявки):

| Доход | Вероятный CAEM | Подходит? |
|---|---|---|
| YouTube AdSense (YPP) | 59.11 / 60.x / роялти | **Нет**, не в списке ст. 8 |
| Партнёрские комиссии | 73.11 / 74.90 / посредничество | **Нет**; реклама, SMM и медиа «не считаются IT автоматически» [vendor: i-avocat] |
| Собственный SaaS или расширения через MoR | 58.29 / 63.11 | **Вероятно да**, если это собственное ПО; продажа через MoR — это продажа лицензий/доступа реселлеру. Verify: как MITP смотрит на MoR-выплаты |
| Цифровые продукты: шаблоны кода, плагины | 58.29 | вероятно да |
| Цифровые продукты: e-books, курсы, стоки | 58.1x / 85.5x / 74.20 | **Нет** (85.59 — только IT-обучение) |
| B2B-услуги ИИ-агентов: разработка, автоматизация, обработка данных | 62.01 / 62.02 / 62.09 / 63.11 | да |
| B2B-услуги: SEO, контент, переводы | 73.11 / 74.30 | **нет** |
| Telegram Stars / реклама в каналах | 63.12? / 73.1x | неясно, verify |
| Лидген-сайт pickaroofer.com (продажа лидов) | 63.12 или 73.11 | неясно, ask MITP |

**Следствие.** Global Web SRL (SEO-агентство + YouTube + партнёрки) почти наверняка не выполнит 70%. IT Park имеет смысл только для отдельной SRL, где ≥70% выручки — софт и SaaS, и только примерно от $4 200 в месяц выручки при одном работнике.

## 5. Сравнение нагрузки [estimate]

Допущения:
- выручка = прибыль (расходов нет, платформенные и банковские комиссии не учтены);
- вся прибыль изымается в том же году;
- экспорт по НДС 0%, НДС не влияет;
- курс 17.7706;
- без бухгалтерии, аудита и взноса MITP (нет данных), без премии CNAM 12 636 MDL в год (≈1 053 в месяц), если она нужна.

Формулы (R — месячная выручка в MDL):
- A. SRL 12% + дивиденды: 0.12R + 0.06 × 0.88R = 17.28% R (2027: 0.12 + 0.08 × 0.88 = 19.04%).
- B. SRL IVAO + дивиденды: 0.04R + 0.06 × 0.96R = 9.76% R (2027: 11.68%). **Только новая SRL без НДС.**
- C1. IT Park, 1 работник = владелец, всё на зарплату: max(0.07R; 5 220). Зарплата окончательно обложена. Нужно R ≥ зарплата + налог; зарплата ≥ минимальной 6 300 при полной ставке (для неполной — verify).
- C0. IT Park, 0 работников, изъятие дивидендами: 0.07R + 0.06 × 0.93R = 12.58% R (2027: 14.44%). Допустимость — verify.

| Выручка в месяц | R, MDL | A: SRL 12% + див. | B: IVAO + див. | C1: IT Park, 1 работник | C0: IT Park, 0 работников (verify) |
|---|---|---|---|---|---|
| $300 | 5 331.18 | 921.23 (17.28%) | 520.32 (9.76%) | 5 220 (97.9%) — **нереально**: выручки не хватает даже на минимальную зарплату | 670.66 (12.58%) |
| $1 500 | 26 655.90 | 4 606.14 (17.28%) | 2 601.62 (9.76%) | 5 220 (19.58%) | 3 353.31 (12.58%) |
| $5 000 | 88 853.00 | 15 353.80 (17.28%) | 8 672.05 (9.76%) | 6 219.71 (7.00%) | 11 177.71 (12.58%) |
| 2027, $5 000 | 88 853.00 | 16 917.61 (19.04%) | 10 378.03 (11.68%) | 6 219.71 (7.00%) | 12 830.37 (14.44%) |

- Порог IT Park при одном работнике: 5 220 / 0.07 = 74 571 MDL ≈ $4 196 в месяц [estimate].
- Если в режиме A расходы составляют, например, 30% выручки, налог 12% считается с 70%. Тогда A ≈ 0.7 × 17.28% = 12.1% от выручки [estimate]. Для B и C расходы не учитываются.
- Для сравнения — antreprenor independent (база проекта): 15% до 1.2 млн MDL в год. Но из своей же SRL этот режим получить нельзя (ст. 88(8)).

**Практический вывод [estimate]:**
- до ~$4 000 в месяц — Global Web SRL в общем режиме, 0% на реинвестиции, изъятие дивидендами (~17.3%). Либо новая SRL без НДС на IVAO (~9.8%), если это одобрит бухгалтер;
- от ~$4 200 в месяц IT-выручки (SaaS, разработка) — отдельная SRL-резидент IT Park (~7% + аудит + взнос).
- YouTube и партнёрки в IT Park не заводить.

---

## Вопросы бухгалтеру / юристу (ask accountant)

1. Может ли Global Web SRL (плательщик НДС) сняться с учёта по НДС в 2026–2027 годах при обороте < 1.7 млн? Если нет — открывать ли новую SRL на IVAO, и нет ли риска переквалификации как искусственного дробления?
2. Место поставки и ставка НДС (0% экспорт или 20%) для каждого дохода: YouTube AdSense от Google Ireland/LLC, MoR-выплаты (Paddle, Creem, Polar), партнёрские комиссии, Telegram (Fragment/TON), B2C-услуги физлицам-нерезидентам. Какие документы подтверждают экспорт?
3. Кто клиент при продаже через MoR: MoR или конечный покупатель? Выставлять ли инвойс на MoR, или хватит self-billing statement?
4. Действует ли 0% на реинвестиции для Global Web SRL (CAEM, не раздел G), и как считается 12% при последующих дивидендах?
5. Нужна ли фиксированная премия CNAM 12 636 MDL владельцу-администратору без трудового договора?
6. IT Park: может ли SRL быть резидентом без единого работника (администратор по договору мандата)? Какой тогда минимум налога?
7. IT Park: как MITP классифицирует SaaS-выручку через MoR, продажу шаблонов и плагинов, лидген-сайт, Telegram-ботов с оплатой в Stars — ask MITP письменно.
8. Минимальный месячный взнос MITP и типичная цена ежегодного аудита для резидента с 1 работником.
9. Ставка на дивиденды резидента IT Park (6% или иная) и будет ли 8% с 2027 года.
10. Попадают ли экспортные поставки по 0% в расчёт порога НДС 1.7 млн для новой SRL?

## Что не удалось проверить

- Полные тексты ст. 54¹, 104, 111, 369 НК и закона 77/2016 (ст. 8) на legis.md — домены `.md` заблокированы прокси. Всё — по выдержкам поиска.
- Полный актуальный список CAEM IT Park («17 кодов») — не прочитан.
- Минимальный месячный взнос MITP и цена аудита — нет данных.
- Первый месяц: 150 или 50 MDL — расхождение (доверяем 150, официальный FAQ).
- Судьба проекта 35% — есть только вторичные подтверждения, что он не принят. Консультация particip.gov.md id 11116 — содержание неизвестно.
- Отклонение добровольной отмены НДС — только вендорский источник (VATupdate).
- Дата первого чтения политики-2027 (10.09.2026) — по выдержке, verify. Статус второго чтения — нет данных.
- Ужесточение IVAO (60% → 25%) — вошло ли в одобренный правительством проект — verify.
- Налоговый режим YouTube-дохода SRL в Молдове — нет официального разъяснения.
- KPMG 03.2026: «предложено дальнейшее повышение порога НДС» — содержание не прочитано.

## Источники (дата публикации, если видна; доступ 26.09.2026, только выдержки поиска)

Официальные:
- SFS, baza generalizată nr. 167 «Impozitul unic aferent rezidenților parcurilor IT» — https://www.sfs.md/en/generalization-database-question/167 [official], дата n/a
- SFS, baza generalizată nr. 79 (IVAO) — https://sfs.md/ro/intrebare-baza-de-date-generalizare/79 [official]
- SFS, «Locul livrării» nr. 10 и nr. 19 — https://sfs.md/ro/intrebare-baza-de-date-generalizare/10 , https://sfs.md/ro/intrebare-baza-de-date-generalizare/19 [official]
- SFS, nr. 81 «Reținerea finală a impozitului din dividende» — https://sfs.md/ro/intrebare-baza-de-date-generalizare/81 [official]
- Monitorul Fiscal, «Întreprinderea … prestează servicii de programare nerezidenților» — https://monitorul.fisc.md/questions/intreprinderea-in-baza-contractului-presteaza-servicii-de-programare-nerezidentilor.html/ [official-изд. SFS]
- Monitorul Fiscal, «Parcurile IT. Ce modificări se propun?» — https://monitorul.fisc.md/parcurile-it.-ce-modificari-se-propun/ [press/official], ~2023
- Monitorul Fiscal, «Din 12 februarie în parcul IT vor fi permise noi genuri de activitate» — https://monitorul.fisc.md/din-12-februarie-in-parcul-it-vor-fi-permise-noi-genuri-de-activitate/ , 2024
- Monitorul Fiscal, «Din 1 martie 2026 pragul de înregistrare … TVA va fi majorat» — https://monitorul.fisc.md/din-1-martie-2026-pragului-de-inregistrare-in-calitate-de-platitor-de-tva-va-fi-majorat/ , 2026
- MF, «Modificările efectuate în Codul fiscal pentru anul 2026» — https://www.mf.gov.md/ro/content/modific%C4%83rile-efectuate-%C3%AEn-codul-fiscal-pentru-anul-2026-privind-impozitul-pe-venit-tva [official]
- MF / Guvern, «Politica fiscală și vamală pentru anul 2027, aprobată de Guvern» — https://gov.md/ro/comunicate-de-presa/politica-fiscala-si-vamala-pentru-anul-2027-aprobata-de-guvern ; https://mf.gov.md/en/node/135263 [official], 08.09.2026
- Guvern, минимальная и средняя зарплата 2026 — https://gov.md/ro/comunicate-de-presa/guvernul-aprobat-cuantumul-salariului-minim-si-mediu-pentru-anul-2026 [official], 12.2025
- CNAM, премия в фиксированной сумме 2026 — https://cnam.md/7774/cnam-va-demara-pe-1-ianuarie-procesul-de-achitare-a-primei-de-asigurare-medicala-obligatorie-in-suma-fixa-pentru-anul-2026/ [official], 31.12.2025
- MITP FAQ — https://mitp.md/why-mitp/faq/ ; tax calculator — https://mitp.md/why-mitp/tax-calculator/ ; Ghidul Rezidentului — https://mitp.md/wp-content/uploads/2026/05/Ghidul-Rezidentului-MITP_ro.pdf (05.2026); Decizie nr. 135 (verificare anuală 2024) — https://mitp.md/p/public/files/Decizie%20nr.135%20_MITP_verificarea%20anuala%202024_finala_30.12.2024.signed.pdf (30.12.2024) [official]
- particip.gov.md, консультация по изменению закона 77/2016 — https://particip.gov.md/ro/document/stages/anunt-consultari-publice-privid-modificarea-legii-nr772016-cu-privire-la-parcurile-pentru-tehnologia-informatiei/11116 [official], дата n/a

Пресса:
- VATupdate, 25.02.2026 — https://www.vatupdate.com/2026/02/25/moldova-raises-vat-registration-threshold-to-1-7-million-lei-effective-march-1-2026/
- VATupdate, 20.06.2026 «Moldova Maintains Strict VAT Registration Rules» — https://www.vatupdate.com/2026/06/20/moldova-maintains-strict-vat-registration-rules/ [vendor/press]
- agora.md, 19.02.2026 — https://agora.md/2026/02/19/plafonul-de-inregistrare-tva-majorat-la-17-milioane-de-lei-noua-regula-va-fi-aplicata-din-1-martie
- Moldpres, порог 1.7 млн — https://www.moldpres.md/rom/economie/mai-putine-firme-obligate-sa-plateasca-tva-plafonul-de-inregistrare-tva-a-fost-majorat-la-1-7-milioane-de-lei (2026)
- KPMG TaxNewsFlash 02.2026 (закон 318/2025) — https://kpmg.com/us/en/taxnewsflash/news/2026/02/moldova-increase-vat-registration-one-year-extension-exemption-smes.html ; 03.2026 — https://kpmg.com/us/en/taxnewsflash/news/2026/03/tnf-moldova-proposed-additional-increase-in-vat-registration-threshold.html
- stiri.md / telegraph.md / radiochisinau.md — 0% на реинвестиции в 2026: https://stiri.md/article/economic/cota-zero-la-impozitul-pe-profit-reinvestit-va-fi-mentinuta-si-in-2026 (конец 2025)
- ziar.md «Impozitul pe dividende – 8% în 2027» — https://ziar.md/impozitul-pe-dividende-8-in-2027-tofan-daca-scoti-profitul-din-companie-il-taxam-daca-il-reinvestesti-te-incurajam/ (2026)
- ipn.md / radiochisinau — первое чтение политики-2027: https://ipn.md/politica-bugetar-fiscala-pentru-2027-aprobata-de-parlament-in-prima-lectura-opozitia-critica-documentul (09.2026)
- logos-pres.md «Vasile Tofan: Moldova IT Park tax regime will remain unchanged» — https://logos-pres.md/en/news/vasile-tofan-the-it-parks-tax-regime-will-not-change/ (2026)
- logos-pres.md «The number of tax regimes will be reduced» — https://logos-pres.md/en/news/the-number-of-tax-regimes-will-be-reduced-which-ones-will-remain/ (2026)
- moldovamatters.md «A Deep Dive into the Proposed 2027 Tax Reform» — https://www.moldovamatters.md/p/a-deep-dive-into-the-proposed-2027 (2026)
- newsmaker.md, проект 35% / call-centre — https://newsmaker.md/ro/call-centre-in-it-park-si-impozite-mai-mari-ce-spun-expertii-despre-noul-proiect-surpriza-al-guvernului (~2023, старше 2025, контекст)

Вендоры и бухгалтерии:
- Incorpore: Moldova IT Park — https://incorpore.md/en/moldova-it-park/ ; минимум на работника 2026 — https://incorpore.md/ro/blog/mitp-minimum-employee-floor-calculation/ ; 0% реинвестиции — https://incorpore.md/ro/blog/moldova-0-reinvested-profits-tax/ (2026)
- dad.md: «Ce impozite achită rezidenții IT Park» — https://dad.md/dad-accountant/ce-impozite-achita-rezidentii-it-park/ ; «4% sau 12%» — https://dad.md/dad-accountant/ce-regim-de-impozitare-sa-alegi/ (дата n/a)
- i-avocat.md, IT Park Resident guide — https://i-avocat.md/en/blogs/news/rezident-it-park-ghid-complet-pentru-antreprenorii-din-republica-moldova (дата n/a)
- fmd.md: IT Park — https://fmd.md/blog/cum-sa-devii-rezident-moldova-it-park-cerinte ; порог НДС — https://fmd.md/eng/blog/new-vat-threshold-in-moldova-from-march-1-2026 (2026)
- colenco.legal, 13.04.2026 — https://colenco.legal/ro/blog/2026-04-13-it-park-moldova-resident-status
- ducont.md, IT Park vs SRL 2026 — https://ducont.md/en/calculator-it-park/ ; bizonaire FAQ — https://bizonaire.com/en/articles/faq-about-moldova-it-park
- contabilsef.md: «Achitarea prealabilă a impozitului în cazul repartizării dividendelor» — https://www.contabilsef.md/achitarea-prealabila-a-impozitului-in-cazul-repartizarii-dividendelor ; «A fost actualizat cadrul legal … parcurilor IT» — https://www.contabilsef.md/a-fost-actualizat-cadrul-legal-ce-reglementeaza-activitatea-parcurilor-it/
- PwC Worldwide Tax Summaries, Moldova corporate — https://taxsummaries.pwc.com/moldova/corporate/taxes-on-corporate-income (обновление 2026, выдержка)
- buget.md / wizcontabil — расчёт зарплаты 2026: https://www.buget.md/en/calculator-salarii-2026-moldova
- surucinschi.md / audititpark.md — аудит IT Park (цены не опубликованы)

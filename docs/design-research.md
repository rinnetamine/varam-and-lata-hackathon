# Design and terminology research for "Mana VSAA"

Collected 09.10.2026 from the live portal and public VSAA pages before building the dashboard. Everything in `public/vsaa.*` and `server/benefits.py` follows these notes.

## 1. The problem (from the hackathon brief)

Latvija.gov.lv lists VSAA services under their technical names, a newborn triggers six separate benefit applications, searching "bērna pabalsts" returns dozens of municipal services from other novadi, a first-time VSAA user has an incomplete profile (only a bank account is actually missing), the other parent's data cannot be shown, and the existing VSAA dashboard shows pensions but not what is actionable now (unpaid sick-leave certificates, unused benefits, missing social contributions).

## 2. Visual tokens measured on latvija.gov.lv (computed styles)

| Token | Value | Where it is used on the portal |
| --- | --- | --- |
| Typeface | `Ubuntu, sans-serif` (400 / 500 / 700) | Everything; body 14 px, nav 16–18 px |
| Text | `#1c1c1c`; secondary `#2d313b`; muted `#8e949f` | Body copy, labels |
| Accent | `#a01b36` (burgundy) | Links, primary buttons (`Ienākt Mana Latvija.lv`), badges, counts |
| Outline blue | `#678cbc` | Accordion panel borders, outline buttons, nav pills |
| Band | `#e9f2fc` with border `#c1d2e5` | Header and hero background |
| Light line | `#dae6f3`; panel grey `#f7f7fa` | Card separators, muted panels |
| Error | `#e7231f` | Validation |
| Radius | 6 px | Buttons and panels |
| Headings | h1 52 px / 700, h2 32 px / 700 | Page titles |
| Primary button | `#a01b36`, white, 500 weight, 12 px 10 px padding | `Ienākt Mana Latvija.lv →` |
| Outline button | 1 px `#678cbc`, 10 px 20 px padding | `Skatīt visus padomus` |

Stylesheet origin: `eservices.viss.gov.lv/EservicePlatform.Assets/.../HTMLSDK/css/style.css` (the VISS e-service platform SDK, shared across state e-services).

Patterns seen: accordion panels with a chevron (`Digitālie padomi`, `Dzīves situācijas`), life-situation pages as a list of expandable steps each ending in `Saistītie pakalpojumi`, "Mana Latvija.lv" dashboard with account switcher, `E-adrese 37 Nelasīti` / `Paziņojumi 4` count tiles and outline `Skatīt …` buttons.

## 3. Official terminology (Latvija.gov.lv catalogue names)

Life situations:

- `Bērna gaidīšana un piedzimšana` — https://latvija.gov.lv/LifeSituations/22503
- `Slimības lapa un rīcība saslimšanas gadījumā` — https://latvija.gov.lv/LifeSituations/23773
- `Bezdarbnieku pabalsts un darba meklēšana` — https://latvija.gov.lv/LifeSituations/22291

VSAA services (all end in "piešķiršana un izmaksāšana"):

`Maternitātes pabalsta`, `Paternitātes pabalsta`, `Bērna piedzimšanas pabalsta`, `Bērna kopšanas pabalsta`, `Vecāku pabalsta`, `Ģimenes valsts pabalsta`, `Slimības pabalsta`, `Bezdarbnieka pabalsta` … piešķiršana un izmaksāšana. The e-service that shows decisions is `VSAA informācija un pakalpojumi` (https://latvija.gov.lv/Services/45686).

Other terms used as on the portal: `darbnespējas lapa A/B`, `VPVKAC` (vienotie valsts un pašvaldību klientu apkalpošanas centri), `NVA bezdarbnieka statuss`, `NVA CV un vakanču portāls`, `e-adrese`, `Pieteiktie pakalpojumi`, `Dzīves situācijas`, `Pakalpojumu ieteikumi`.

## 4. Benefit rules used in the prototype (likumi.lv and VSAA pages, verified 09.10.2026)

| Benefit | Amount / period | Who | Apply within | Decision |
| --- | --- | --- | --- | --- |
| Maternitātes | 80 % (10. p.); 56 + 56 days, 70 + 56 with early care, +14 for complications or multiple births (5. p.) | mother (employee / self-employed; insurance 3/6 or 6/24 months, 4. p.) | 6 months from the insured event (25. p.) | 10 working days |
| Paternitātes | 80 % (10.³ p.; VSAA applies coefficient 1.46); 10 working days per child (10.¹ p.); leave granted within 6 months of birth (Darba likuma 155. p.) | father (insurance 3/6 or 6/24 months) | 6 months from first day of leave | 10 working days |
| Bērna piedzimšanas | one-time 600 EUR for births from 01.01.2026 (MK 1546, 2. p., MK 815/2025); 421.17 EUR for births up to 31.12.2025 | one parent (VSP likuma 8. p.) | 6 months from birth (18. p.) | 8 working days |
| Bērna kopšanas | 298 EUR/month to 1.5 years (MK 1609, 2. p.); 42.69 EUR/month from 1.5 to 2 years only for children born up to 02.11.2026 (transition) | one parent, employment irrelevant; with parental benefit — the same person (7. p. 2. d.) | 6 months; later claims paid for the previous 6 months only (18. p.) | 22 working days |
| Vecāku | 60 % (13 months) or 43.75 % (19 months) of the average contribution wage (10.⁶ p.); 75 % of that while working in 2026; 2 non-transferable months per parent until age 8 | one parent (employee / self-employed; insurance 3/6 or 6/24 months) | 6 months from requested start (25. p.) | 10 working days |
| Ģimenes valsts | 25 EUR for one child, 100 for two, 225 for three, 100 per child for four or more (6. p. 2.² d.); piemaksa 160 EUR for a child with a disability (MK 864, 6. p.); from age 1 to 16 (20 while studying, incl. higher education from 2026) | one parent | 24 months from first birthday; later claims paid for 24 months back (18. p. 1.¹ d.) | 10 working days |
| Slimības | from day 10 of certificate B (days 1–9 employer, certificate A); max 26 weeks / 52 weeks in 3 years | employee / self-employed | 6 months from first day of incapacity | 10 working days |
| Bezdarbnieka | 50–65 % of the average wage by insurance record (7. p.); full → 75 % → 50 % → 45 % over 8 months (9. p.) | NVA unemployed status (3. p.), record ≥ 1 year, 12 of last 16 months (5. p.) | granted from the day of application (13. p.) | within a month |

These are simplifications for the demo; see `server/benefits.py` for the act, article and URL behind each rule (laws: "Par maternitātes un slimības apdrošināšanu" likumi.lv/ta/id/38051, Valsts sociālo pabalstu likums 68483, Darba likums 26019, "Par apdrošināšanu bezdarba gadījumam" 14595; regulations: MK 1546 → 202714, MK 1609 → 202854 and its 2026 amendment 365450, MK 864 → 328673). The earlier draft of this prototype used 421.17 EUR for the childbirth benefit and an "8th day" rule; both were corrected on 09.10.2026 after checking MK 1546 as amended by MK 815/2025.

## 5. Open data used

- `VSAA administrēto pakalpojumu saņēmēju skaits` (LM, CC0) — recipients per municipality, 12.2025 → `public/data/vsaa-statistics.json`
- `Ģimenes valsts pabalsta saņēmēji` (VSAA, CC0) — recipients by number of children, 06.2026 → `public/data/gimenes-valsts-pabalsts.json`
- `Vakances` (NVA, CC0, daily CSV) — 1 373 vacancies on 09.10.2026, aggregated per municipality → `public/data/nva-vacancies.json`
- Existing imports: VZD addresses (CC BY 4.0) for the declared municipality, Riga service catalogue (CC0).

Municipality names in the three datasets match the VZD address snapshot (`Rīga`, `Jūrmala`, `… novads`), which is what links a person's declared address to local statistics and vacancies.

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

## 4. Benefit rules used in the prototype (VSAA pages, read 09.10.2026)

| Benefit | Amount / period | Who | Apply within | Decision |
| --- | --- | --- | --- | --- |
| Maternitātes | 80 % of average contribution wage; 56/70 + 56/70 days | mother (employee / self-employed) | 6 months from first day of pregnancy leave | 10 working days |
| Paternitātes | 80 % × coefficient 1.46; 10 working days, taken by 6 months of age | father | 6 months from first day of leave | 10 working days |
| Bērna piedzimšanas | one-time 421.17 EUR; decision not before day 8 | one parent | 6 months from birth | 8 working days |
| Bērna kopšanas | 298 EUR/month to 1.5 years (from 01.01.2026) | one parent, employment irrelevant | 6 months from the right arising | 22 working days |
| Vecāku | depends on wage; 13 or 19 months; 2 non-transferable months per parent until age 8 | one parent (employee / self-employed) | 6 months from requested start | 10 working days |
| Ģimenes valsts | 25 / 50 / 75 / 100 EUR per child by number of children; from age 1 to 16 (20 if studying) | one parent | 24 months from first birthday | 10 working days |
| Slimības | from day 10 of certificate B (days 1–9 employer, certificate A); max 26 weeks / 52 weeks in 3 years | employee / self-employed | 6 months from first day of incapacity | 10 working days |
| Bezdarbnieka | by wage and insurance record; 100 % → 75 % → 50 % → 45 % over 8 months | NVA unemployed status + 12 of last 16 months contributions | apply NVA and VSAA the same day | within a month |

These are simplifications for the demo; see `server/benefits.py` for the source link per benefit.

## 5. Open data used

- `VSAA administrēto pakalpojumu saņēmēju skaits` (LM, CC0) — recipients per municipality, 12.2025 → `public/data/vsaa-statistics.json`
- `Ģimenes valsts pabalsta saņēmēji` (VSAA, CC0) — recipients by number of children, 06.2026 → `public/data/gimenes-valsts-pabalsts.json`
- `Vakances` (NVA, CC0, daily CSV) — 1 373 vacancies on 09.10.2026, aggregated per municipality → `public/data/nva-vacancies.json`
- Existing imports: VZD addresses (CC BY 4.0) for the declared municipality, Riga service catalogue (CC0).

Municipality names in the three datasets match the VZD address snapshot (`Rīga`, `Jūrmala`, `… novads`), which is what links a person's declared address to local statistics and vacancies.

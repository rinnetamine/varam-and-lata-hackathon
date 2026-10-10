# Open data used in the Faketvija.lv prototype / Prototipā izmantotie atvērtie dati

Audited 2026-10-09 against the catalogue metadata saved in `data/metadata/` and the publishers' licence declarations on data.gov.lv. Nothing in this project is fetched from a live government API at runtime: every dataset is a snapshot bundled in the repository (or re-importable with the scripts named below). The visible attribution page is `public/data-licenses.html`; this file is the complete inventory.

Audits 2026-10-09 pēc `data/metadata/` saglabātajiem kataloga metadatiem un publicētāju licenču norādēm data.gov.lv. Neviena datu kopa netiek ielādēta no valsts API darbības laikā — visas ir repozitorijā iekļauti momentuzņēmumi (vai atkārtoti importējamas ar norādītajiem skriptiem). Redzamā atsauču lapa ir `public/data-licenses.html`; šī datne ir pilnais saraksts.

## 1. Valsts adrešu reģistra atvērtie dati (State Address Register)

| | |
| --- | --- |
| Publisher / Publicētājs | Valsts zemes dienests |
| Catalogue / Katalogs | https://data.gov.lv/dati/dataset/varis-atvertie-dati (id `6b06a7e8-dedf-4705-a47b-2a7c51177473`) |
| Resources / Resursi | `aw_pilseta.csv`, `aw_novads.csv`, `aw_pagasts.csv`, `aw_ciems.csv`, `aw_iela.csv`, `aw_eka.csv` (URLs, sizes and SHA-256 in `data/manifest.json`) |
| Licence | CC BY 4.0 — https://creativecommons.org/licenses/by/4.0/ (legal code saved in `data/licenses/CC-BY-4.0.html`) |
| Attribution required / Atsauce | Yes: dataset name, publisher, licence link and a note of changes — given on `public/data-licenses.html` and on the profile page next to the address. |
| Retrieved / Iegūts | 2026-10-09T13:09:27Z (`data/manifest.json`) |
| Local files / Datnes | `public/data/addresses.json` (five sample building addresses per municipality, bundled), `public/data/municipalities.json` (index, bundled), `public/data/addresses/<code>.json` (full snapshot, generated locally, not in Git), `data/raw/varis-atvertie-dati/*.csv` (not in Git) |
| Use / Lietojums | A demo person's declared address (random sample, fictional association) and the municipality lookup that links the person to local statistics and vacancies. |
| Transformation / Pārveide | Active records only (`STATUSS=EKS`); municipality resolved through the parent-code hierarchy; selected fields; CSV → JSON grouped by municipality. No apartment-level addresses. |
| Mode / Režīms | Bundled sample + locally generated full snapshot (`python3 scripts/import_open_data.py`). |
| Limitations / Ierobežojumi | Snapshot, not a live register; building/land addresses only; the people living at these addresses are invented. |

## 2. Pašvaldības pakalpojumu apraksti (Riga municipal service descriptions)

| | |
| --- | --- |
| Publisher | Rīgas dome |
| Catalogue | https://data.gov.lv/dati/dataset/pasvaldibas-pakalpojumu-apraksti (id `87626b5c-3e9a-47f4-a647-ad6562984499`) |
| Resource | `3.datu_kopa_pasvaldibas_pakalpojumi.csv` (resource id `b2aa7539-57a2-4d5d-8c4e-2d7de542ef58`) |
| Licence | CC0 1.0 — https://creativecommons.org/publicdomain/zero/1.0/ (legal code in `data/licenses/CC0-1.0.html`) |
| Attribution | Not required by CC0; source kept for provenance. |
| Retrieved | 2026-10-09T13:09:27Z |
| Local files | `public/data/riga-services.json` (bundled), `data/raw/pasvaldibas-pakalpojumu-apraksti/` (not in Git) |
| Use | Service-discovery experiment on the services page; not used by the VSAA dashboard. |
| Transformation | CSV → JSON, fields unchanged. |
| Mode | Bundled. |
| Limitations | Riga only; five records; the publisher warns the data is incomplete; one record is marked suspended. Not a current service catalogue. |

## 3. Ģimenes valsts pabalsta saņēmēji (State family benefit recipients)

| | |
| --- | --- |
| Publisher | Valsts sociālās apdrošināšanas aģentūra (VSAA) |
| Catalogue | https://data.gov.lv/dati/dataset/gimenes-valsts-pabalsta-sanemeji (id `4aad1c1c-835a-45cc-8315-133dfeb9d90c`) |
| Resource | `gimenes_valsts_pabalsti_06-2026.xlsx` (resource id `8ea423c5-ac07-4f29-8592-0fc7123c6a1e`) |
| Licence | CC0 1.0 |
| Attribution | Not required; source and publisher shown on the dashboard and the attribution page. |
| Retrieved | 2026-10-09 (import 13:09Z; JSON conversion the same day) |
| Local files | `public/data/gimenes-valsts-pabalsts.json` (bundled); original XLSX in `data/raw/` (not in Git) |
| Use | "Mana pašvaldība atvērtajos datos" panel: recipients by number of children in the person's municipality versus the national total. |
| Transformation | Worksheet rows copied into a JSON array with named columns; values unchanged; territory names trimmed. |
| Mode | Bundled; manual conversion (the importer does not yet regenerate it). |
| Limitations | Aggregate counts for June 2026, not benefit rules, amounts or personal records. |

## 4. VSAA administrēto pakalpojumu saņēmēju skaits (Recipients of VSAA-administered services)

| | |
| --- | --- |
| Publisher | Labklājības ministrija |
| Catalogue | https://data.gov.lv/dati/dataset/vsaa-adm-pakalpojumu-sanemeju-skaits (id `280fef64-8ffd-40f2-897f-23728f2b500e`) |
| Resource | `vsaa_pakalpojumu_sanemeji_12-2025.xlsx` (resource id `5cb182e0-f7f2-441e-bf5c-3ae27e16ff47`) |
| Licence | CC0 1.0 |
| Attribution | Not required; shown anyway. |
| Retrieved | 2026-10-09 |
| Local files | `public/data/vsaa-statistics.json` (bundled); original XLSX in `data/raw/` (not in Git) |
| Use | Same panel: sickness, unemployment, maternity, paternity, parental/childcare and family-benefit recipients per municipality. |
| Transformation | Rows copied to JSON with named columns; values unchanged. |
| Mode | Bundled; manual conversion. |
| Limitations | December 2025 counts only; statistics, not eligibility. |

## 5. Vakances (NVA job vacancies)

| | |
| --- | --- |
| Publisher | Nodarbinātības valsts aģentūra (NVA) |
| Catalogue | https://data.gov.lv/dati/dataset/vakances (id `cb6831cb-1d89-44a3-b889-b43c411df4fe`) |
| Resource | `vakances-2026-10-09.csv` (resource id `7f68f6fc-a0f9-4c31-b43c-770e97a06fda`, updated daily) |
| Licence | CC0 1.0 |
| Attribution | Not required; source and licence shown under the vacancies panel. |
| Retrieved | 2026-10-09 |
| Local files | `public/data/nva-vacancies.json` (bundled) |
| Use | "Sociālās iemaksas un darbs": number of vacancies and up to three sample vacancies in the person's municipality, with links to the NVA CV and vacancy portal. |
| Transformation | 1 373 rows aggregated to counts per municipality and per category; three sample vacancies per municipality kept (title, category, salary range, deadline, place, portal id); municipality derived from the `Vieta` field; two unparseable place values folded into their city. |
| Mode | Bundled daily snapshot; no runtime fetch. |
| Limitations | A single day's snapshot; the full list lives on https://cvvp.nva.gov.lv/. |

## 6. Personu vārdi (First-name statistics)

| | |
| --- | --- |
| Publisher | Pilsonības un migrācijas lietu pārvalde (PMLP) |
| Catalogue | https://data.gov.lv/dati/dataset/personu-vardi (id `ac246d11-d5d6-445e-a6c7-8f5013460335`) |
| Resource | `Vardi-dz-20260701.csv` (resource id `10f0bb84-dd18-44e9-9a80-dc1515a4b3a9`) |
| Licence | CC0 1.0 (declared `license_id: CC0-1.0` in `data/metadata/personu-vardi.json`; the catalogue entry has no licence URL, so the Creative Commons legal code in `data/licenses/CC0-1.0.html` is referenced) |
| Attribution | Not required; shown on the attribution page. |
| Retrieved | 2026-10-09T17:31:50Z (`public/data/person-names.json`, SHA-256 recorded there) |
| Local files | `public/data/person-names.json` (bundled, 200 names), `data/metadata/personu-vardi.json` |
| Use | First names of the fictional children in `server/data/children.db`. |
| Transformation | The 100 most frequent alphabetic single first names per gender; title case. |
| Mode | Bundled; re-import with `python3 scripts/import_person_names.py`. |
| Limitations | Aggregate name counts, not personal records. |

## Benefit rules (not a dataset) / Pabalstu noteikumi

The benefit amounts, periods and deadlines in `server/benefits.py` are summaries of legislation and VSAA guidance read on 2026-10-09 (likumi.lv consolidated texts; vsaa.gov.lv service descriptions; latvija.gov.lv life situations). They are not open data and carry no licence claim; the legal citations are listed on `public/data-licenses.html` (section "Pabalstu noteikumi un tiesiskais pamats") and in `docs/design-research.md`.

## Generated and fictional data / Ģenerētie un izdomātie dati

The following are **not** open data and must never be described as official:

- People in `server/data/people.db`: names combined from fixed lists in `server/seed_people.py`, personas kodi in the `DDMMYY-XXXXX` format with invented birth dates and random suffixes, `example.com` e-mail addresses, random phone numbers, addresses sampled from dataset 1 (the association is fictional), the demo administrator account.
- Children in `server/data/children.db`: first names sampled from dataset 6, surnames inherited from the fictional parent, invented personas kodi and birth dates, invented mother/father links and "receiving" flags.
- Bank customers and test IBANs in `server/data/bank.db` (`LVxxTEST…`, checksum-valid, no real bank).
- Social-insurance contribution history, sick-leave certificates, applications, decisions and e-address messages created by the seeder or by using the prototype.
- Municipal benefit rules are not modelled at all; the dashboard only links to the Latvija.gov.lv life situation for the person's municipality.

## Licence status / Licenču statuss

No unresolved licence or attribution issue was found: datasets 2–6 are CC0 1.0 and dataset 1 (CC BY 4.0) is attributed with a licence link and a description of changes wherever its data appears. Latvija.gov.lv logos, wordmarks and design assets are not used; the portal's typeface (Ubuntu, Ubuntu Font Licence) is loaded from Google Fonts. The project reproduces the portal's colours and layout conventions only, as a design study for a hackathon prototype.

## Benefit calculator (verified 10 October 2026)

The local browser calculator covers maternity, paternity, childbirth, childcare, parental and family state benefits. Inputs stay in browser memory and are not submitted or persisted. It uses public rules, not personal open data or VSAA registry access. Sources are linked in `public/data-licenses.html#calculator-sources` alongside the existing legal references.

- [Official VSAA calculators](https://www.vsaa.gov.lv/lv/kalkulatori): authenticated forecasts for maternity and parental benefits, among other services. External authentication is independent of the prototype.
- [Paternity rules](https://www.vsaa.gov.lv/lv/pakalpojumi/paternitates-pabalsta-pieskirsana-un-izmaksasana): 80% of the daily contribution wage, coefficient 1.46, ten working days for one child; daily payment rounded to cents.
- [2026 changes](https://www.vsaa.gov.lv/lv/jaunums/izmainas-vsaa-pakalpojumos-2026-gada): childbirth payment 600 EUR for births from 1 January 2026; childcare monthly rate 298 EUR and transitional 42.69 EUR for ages 18–24 months for children born by 2 November 2026 inclusive; working parental-benefit recipients receive 75% of the main portion during 2026.

Maternity uses entered daily contribution wage and 112/126/140 calendar days. Parental estimates use entered daily wage, 28–31 calendar days and 60%/43.75% for the selected 13/19-month total period. Family state benefit uses the number of eligible children covered by one recipient (25/100/225 EUR for 1/2/3 children, 100 EUR per child for 4+). These are illustrative estimates under 2026 rules, not an entitlement or combined household payout calculation. Insurance qualification, non-transferable parental portions, maternity offsets, twins and disability supplements, cross-border cases and benefit compatibility are outside this tool. Agency pages are cited as guidance; no page content, logos or calculator implementation was copied.

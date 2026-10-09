# Kopā — e-pakalpojumu prototype

A minimal Latvian website exploring how several public services could be combined around one life event. This is a hackathon demo, not an official government portal. All flows are illustrative. A small demo backend checks fictional personas kodi against a database of invented people; there is no real authentication or connection to government systems.

The centrepiece is **Mana VSAA** (`public/vsaa.html`): a dashboard in the Latvija.gov.lv visual style that shows a signed-in person's current social-insurance situation instead of a service catalogue — the six newborn benefits with official names, amounts and deadlines, unpaid sick-leave certificates, a contribution gap that calls for NVA registration, reminders, and open-data context for the person's municipality. See [docs/design-research.md](docs/design-research.md) for the portal tokens, terminology and benefit rules it follows.

## Run with Docker

Install Docker with Docker Compose (Docker Desktop includes both), then run:

```sh
docker compose up --build -d
```

Open http://localhost:8080/login.html to preview the demo login, then open **Mana VSAA** from the profile. The root page shows the portal landing-page mockup. nginx serves `public/` and proxies `/api/` to the Python demo server in the `api` container; the people database lives in the `people-data` Docker volume.

Stop the website:

```sh
docker compose down
```

After changing files, run `docker compose up --build -d` again to rebuild.

## Develop locally

The website uses plain HTML, CSS, and JavaScript, with no build tools or package dependencies. The demo server uses only the Python 3 standard library. For a local preview without Docker:

```sh
python3 server/app.py
```

This serves `public/` and the API at http://127.0.0.1:8080 and creates `server/data/people.db` on first start. A plain static server (`python3 -m http.server`) still shows the pages, but login needs `server/app.py`.

## Demo login and sessions

- `server/seed_people.py` generates 4 fictional Latvian people (name, surname, e-mail on `example.com`, phone, personas kods in the `DDMMYY-XXXXX` format with fictional birth dates and random suffixes). `python3 server/seed_people.py --list` prints them so you can pick a code; `--reset` regenerates them.
- `POST /api/login` takes `{"personasKods": "..."}`, looks the code up and returns a random bearer token plus the person. Only a SHA-256 hash of the token is stored, and sessions expire after 7 days.
- `GET /api/me` validates the token; `POST /api/logout` revokes it.
- `public/auth.js` keeps the token in `localStorage`, so a reload or new tab stays signed in. The profile and services pages redirect to login without a valid session; a rejected token signs the user out, while an unreachable server keeps the cached session.
- `python3 server/test_api.py` checks the API end to end against a throwaway database, including the VSAA dashboard flows.

A personas kods alone is not a credential in any real system. This works only because the data is fictional; never use it with real people or codes.

## Mana VSAA dashboard

`public/vsaa.html` + `vsaa.js` + `vsaa.css` render `GET /api/vsaa/dashboard` for the signed-in person. The demo database carries four fictional situations, assigned by person id (`python3 server/seed_people.py --list` prints which code opens which):

| id % 4 | Situation | What the dashboard shows |
| --- | --- | --- |
| 1 | Newborn (18 days) with a partner, plus a closed, unpaid darbnespējas lapa B | Six child benefits with status and deadline countdown, "notify the other parent", sick-leave claim |
| 2 | The other parent of that newborn | Same child from the other role; one-per-family benefits show "Pieteicis otrs vecāks" once claimed |
| 3 | Child at 11 months, benefits already granted, one unpaid lapa B | Granted statuses, "ģimenes valsts pabalsts available from the first birthday" reminder |
| 0 | Social contributions stopped two months ago | Contribution strip with the gap, NVA registration + unemployment benefit in one step, NVA vacancies in the municipality |

Actions, all confined to the prototype database:

- `POST /api/vsaa/apply` — prefilled application (name, personas kods, declared address, child or certificate come from the registers; only the IBAN and, for vecāku pabalsts, the 13/19-month choice are asked). Saves the IBAN to the profile and drops a confirmation into the e-address inbox.
- `POST /api/vsaa/notify-other-parent` — the other parent's details are never shown (privacy); VSAA sends them an e-address message listing the benefits available to their role and which ones only one parent can receive, so the family can compare.
- `POST /api/vsaa/profile` — bank account and the "send reminders to e-address" switch. With reminders on, every unclaimed benefit, unpaid certificate and contribution gap is delivered once as an inbox message.
- `GET /api/vsaa/vacancies` — NVA open-data vacancies for the person's declared municipality.

Benefit rules live in `server/benefits.py` with a source link per benefit; they are simplified summaries of public VSAA pages read on 09.10.2026, not eligibility decisions. Dates in the demo scenarios are generated relative to the first server start; run `python3 server/seed_people.py --reset` to regenerate them.

## Current interface

- `public/index.html` — portal landing-page mockup.
- `public/login.html` — demo login; enter a personas kods from the demo database to open the profile.
- `public/profile.html` — demo profile showing the signed-in person's data and a simulated inbox notice about services related to a child's birth.
- `public/pakalpojumi.html` — illustrative service list opened from the inbox notice.
- `public/vsaa.html`, `public/vsaa.js`, `public/vsaa.css` — Mana VSAA dashboard (see above).
- `public/styles.css` and `public/auth.css` — responsive portal and login styles.
- `public/app.js` — text-size toggle.
- `public/auth.js` — login request, token storage, session restore, route guarding and log out.
- `server/` — demo API (`app.py`), VSAA dashboard logic (`vsaa.py`), benefit rules (`benefits.py`) and the fictional people database (SQLite).
- `docs/design-research.md` — Latvija.gov.lv design tokens, official terminology and benefit rules gathered before building.
- `Dockerfile`, `nginx.conf`, and `compose.yaml` — Dockerized static hosting plus the demo API.

This is not government authentication and does not connect to Latvija.gov.lv, eParaksts, or email. Use only the invented personas kodi from the demo database. The profile notice and service descriptions are illustrative and do not confirm eligibility or submit applications.

## Further work

1. Add real service application flows only after verifying official eligibility, deadlines, and requirements.
2. Integrate address selection and municipality lookup using the imported open data.
3. Verify the complete flow in Docker once the Docker daemon is running.

## Open data

Import licensed data snapshots with `python3 scripts/import_open_data.py`. See [data/README.md](data/README.md) for sources, licenses, attribution, generated files and limitations. Import before rebuilding Docker to include nationwide address JSON. The small address sample remains available without the bulk import.

Three further CC0 snapshots converted on 09.10.2026 feed the Mana VSAA dashboard and are committed as JSON: `public/data/vsaa-statistics.json` (VSAA recipients per municipality, 12.2025), `public/data/gimenes-valsts-pabalsts.json` (family state benefit recipients, 06.2026) and `public/data/nva-vacancies.json` (NVA vacancies aggregated per municipality, daily CSV). Sources and licences are listed on `public/data-licenses.html`.

### Demo inbox

SQLite `messages` stores each user's demo notifications, message body, received timestamp and nullable `read_at`. Startup seeds one fictional newborn-service message per user without duplicating it or resetting read status. Authenticated `GET /api/messages` returns only the current user's messages and unread count; `POST /api/messages/<id>/read` saves a read timestamp only for that user's message. Opening mail in the profile marks it read and updates the overview count. No external email is sent or received.

### First-login bank account

Users without an IBAN are directed to `bank-account.html` after login and when entering guarded pages. The authenticated `POST /api/iban` endpoint normalizes and validates a Latvian IBAN's format and MOD-97 checksum, then saves it on that user's record. Subsequent logins open the profile directly; the saved IBAN appears in My data. This does not verify account ownership or make payments. Use only demo IBANs. Existing people receive a nullable IBAN column without resetting records.

### Family showcases and mock bank

- `server/data/people.db`: portal users, sessions, inbox, applications and employment history.
- `server/data/children.db`: three fictional children, first/last names, birth dates, DDMMYY-XXXXX codes, mother/father references and receiving flags per benefit and parent.
- `server/data/bank.db`: fictional bank customers keyed by personas kods, their test IBANs and active status. This simulates a bank registry; no external bank is contacted.

Fresh databases seed four adult accounts. The first four demonstrate no child, one newborn, two children with already granted benefits, and a mother with no recorded father. Users 2 and 3 share one child; user 3 has a second child, and user 4 has a child with no recorded father. Users beyond the first four and their dependent records are removed. There are three distinct children and four parent-child links. Portal `children` rows retain compatibility IDs for existing application foreign keys; the separate child registry is authoritative for family details and dashboard reads.

First names are sampled from the imported PMLP **Personu vārdi** CC0 statistics (`python3 scripts/import_person_names.py`). Surnames are inherited from the fictional father, or mother when no father is recorded. Family links, birth dates, identifiers and bank records are fictional. Source metadata and transformation notes are saved; the source/licence page includes attribution.

A **Demo panelis** button appears on every HTML page, including login. It lets you inspect people, children, parent benefit flags and bank records and copy each user's personas kods or test IBAN. This is a read-only public demo inspector, not a production administrator login. Set `DEMO_ADMIN_ENABLED=0` to disable its API. Keep these registries fictional.

Both `/api/iban` and VSAA profile/application forms check the bank registry: the IBAN must exist, be active and belong to the signed-in user's personas kods. Use the user's IBAN from the demo panel; an arbitrary checksum-valid account is rejected. Existing profile IBANs that fail this check are cleared once during migration, so those users are asked again on next login.

The separate registries are created beside the configured `DB_PATH`, inside the existing persistent Docker volume. Docker mounts the tracked name snapshot read-only. Startup is idempotent and retains family/payment records; `--reset` explicitly clears all demo registries. Local pre-migration backups are excluded from Git.

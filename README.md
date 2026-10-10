# Born Digital · Faketvija.lv

We are **Born Digital**, a team building this project for the **VARAM un LATA atvērto datu hakatons**. Our idea is to make the first steps after a child’s birth easier: bring relevant public services into one personalised journey, so parents can see what support is available, when to apply and what happens next.

**Faketvija.lv** is our working prototype of that journey. Inspired by the government portal Latvija.gov.lv, it combines child-related benefits, reminders, applications and messages in one interface. The playful name and visible prototype notices distinguish it from an official service.

> This is a hackathon demonstration. People and family relationships are fictional. Authentication, banking, applications, decisions and email delivery are simulated locally; nothing is submitted to VSAA, eParaksts or another government system.

## The problem we address

A newborn brings several administrative tasks. Different benefits have different eligibility conditions, application periods and payment rules, and some can be received by only one parent. Finding the correct service and understanding the next step can take time.

Our prototype starts with the family’s situation rather than a long service catalogue. It shows relevant support now, future steps as a child grows, and the applications already submitted.

## What the project offers

- **Personal overview:** messages, available benefits, deadlines, children and an actionable support roadmap.
- **Mana VSAA:** child-specific benefit information, application status, reminders and links to official sources. Choosing a child filters the associated information.
- **Benefit applications:** profile-derived details, a confirmation step, a saved application and an inbox acknowledgement.
- **Planning tools:** calculators and expandable roadmap previews, including 12- and 24-month scenarios for fixed-rate benefits.
- **Sick-leave and contribution pages:** separate views of certificates, contribution history and related actions.
- **Inbox, notifications and history:** persistent messages, read status and recorded activity. A parent can send a child-related notification to the other parent without seeing that parent’s personal information.
- **Bank-account setup:** checks IBAN format, checksum, existence and ownership against a separate fictional bank registry.
- **Administrator register:** review, approve or reject applications and send the corresponding decision to the applicant’s inbox.
- **Presentation tools:** a public demo panel for inspecting fixtures, switching accounts and clearing saved IBANs, plus an animated phone popup showing a fictional newborn-service email.
- **Latvian and English:** a persistent language preference, responsive layouts and a text-size control.

The six child-related benefits represented are:

| Latvian name | English description |
| --- | --- |
| Maternitātes pabalsts | Maternity benefit |
| Paternitātes pabalsts | Paternity benefit |
| Bērna piedzimšanas pabalsts | Childbirth benefit |
| Bērna kopšanas pabalsts | Childcare benefit |
| Vecāku pabalsts | Parental benefit |
| Ģimenes valsts pabalsts | Family state benefit |

## Open data and sources

The prototype uses snapshots from Latvia’s open-data portal, **data.gov.lv**:

| Publisher | Data | How we use it |
| --- | --- | --- |
| PMLP | First-name statistics | Generate fictional names from gender-separated name lists |
| Valsts zemes dienests | State Address Register | Assign sample addresses to fictional users and identify municipalities |
| VSAA | Benefit-recipient statistics | Show municipality-level context |
| NVA | Vacancy data | Show employment opportunities by municipality |

Names are combined into fictional identities. Surnames, personal codes, contact details, family relationships, account numbers and insurance histories are generated; they are not records of real residents. Building addresses may come from real open data, but the residents assigned to them are invented.

The datasets have individual licence requirements: PMLP/VSAA/NVA snapshots listed in the inventory use CC0; VZD address data uses CC BY 4.0 with attribution. These dataset licences do not constitute a licence for the entire project.

[OPEN_DATA.md](OPEN_DATA.md) records the complete dataset inventory, licences, retrieval dates, local files and transformations. [data/README.md](data/README.md) describes the import workflow. The website’s **Datu avoti un licences** page presents attribution and benefit-specific legal references. [docs/design-research.md](docs/design-research.md) documents design and service research.

## Demo scenarios

The current dataset contains five parent accounts, administrator 999 and six children across three households.

| Account IDs | Scenario |
| --- | --- |
| **1–2** | Mother and father with one child born three days before the scenario was seeded |
| **3–4** | Mother and father with two children; several benefits are already granted |
| **5** | Single mother with three children |
| **999** | Administrator with access to the application register |

Each parent has one closed, unpaid B sick-leave record and contribution history. Seeded applications have matching confirmation and decision messages. Dates are fixed when the dataset is seeded; restarting the server does not make the children younger or erase subsequent actions.

The demo panel intentionally exposes fictional fixtures for presentation. It is separate from the administrator register, which requires an admin session. It must not be used with real personal data.

## How it is built

The frontend uses plain **HTML, CSS and JavaScript**. The backend uses the **Python standard library** and **SQLite**, with no Python package installation or frontend build step required.

Three databases separate the portal and simulated registries:

| Database | Contents |
| --- | --- |
| `people.db` | Users, hashed sessions, messages, applications, contributions and sick-leave records |
| `children.db` | Children, birth dates, personal codes, parent links and benefit flags |
| `bank.db` | Fictional bank customers and accounts |

The backend checks application eligibility against the fictional records and uses database constraints to prevent duplicate applications. Decisions and messages persist. Sessions use random bearer tokens with only their hashes stored in SQLite; logout revokes the token and returns to the homepage.

Docker Compose runs an nginx frontend and a Python API. nginx proxies `/api/` requests to the API container, while a named volume retains database state.

```text
public/             Website, translations, calculators and bundled data snapshots
server/             API, benefit rules, registry logic and database seeder
scripts/            Open-data import tools
data/              Source metadata, manifests and saved dataset licences
docs/              Design and service research
compose.yaml        Frontend/API services and persistent database volume
CHANGELOG.md        Detailed changes since the previous release
```

## Scope and limitations

- The interface follows Latvija.gov.lv conventions, but is an independent prototype.
- Enter only fictional personal codes and test IBANs from the demo panel. Personal-code-only login is not suitable for real authentication.
- Reminder and email controls create messages inside the prototype inbox; they do not send external email or official e-address messages.
- Benefit rules are simplified simulations. Estimates use documented assumptions and current modelled rates; they do not confirm entitlement, future rates or payment dates.
- Family-state forecast previews assume one eligible child. Use the full calculator to explore a recipient’s eligible-child count rather than adding child previews together.
- The first run of the v4 showcase migration replaces earlier fictional scenarios. Later starts preserve the new records and user actions.
- The existing `server/test_api.py` needs scenario-fixture updates: it still expects the previous seven-parent dataset. Targeted temporary checks of the new showcase and application lifecycle have passed; the legacy suite is not currently a passing release check.

## Run and present the project

### Option 1: Docker

Install Docker with Docker Compose, then run from the repository root:

```sh
docker compose up --build -d
```

Open **[http://localhost:8080/](http://localhost:8080/)**. After changing source files, run the same command again to rebuild the containers.

Stop the containers while retaining the database volume:

```sh
docker compose down
```

If another local server already uses port 8080, stop it before starting Docker.

### Option 2: Local Python server

With Python 3 installed, run from the repository root:

```sh
python3 server/app.py
```

Open **[http://localhost:8080/](http://localhost:8080/)**. The server serves both the website and API and initialises the local databases in `server/data/`. Stop it with `Ctrl+C`.

A static file server alone cannot run login, banking or application functionality.

### Suggested presentation flow

1. Open the homepage phone popup, open Gmail and follow the newborn-service email into the portal.
2. Open **Demo panelis** and choose a scenario. Copy its personal code for the login flow, or use the quick account-switch button.
3. If bank setup appears, copy that user’s IBAN from the demo panel and save it.
4. Explore the profile roadmap, future benefit previews and calculator.
5. Open **Mana VSAA**, choose a child and submit an available benefit after reviewing the confirmation.
6. Check the acknowledgement in the applicant’s inbox, then switch to **999** and review or decide the application.
7. Return to the applicant and check the changed status and decision message. Switch between both parents to demonstrate child-related notifications.

### Inspect or reset the demo data

List local accounts and their personal codes:

```sh
python3 server/seed_people.py --list
```

To regenerate the fictional dataset, **stop the local server and back up the databases first**. Resetting removes existing sessions, applications and messages:

```sh
python3 server/seed_people.py --reset
python3 server/app.py
```

For Docker, list or reset the database inside the API container:

```sh
docker compose exec api python3 seed_people.py --db /data/people.db --list
```

To reset, stop the services first, then run the seeder in a temporary container using the existing volume:

```sh
docker compose stop
docker compose run --rm api python3 seed_people.py --db /data/people.db --reset
docker compose up -d
```

Reset commands replace demo data. Local `server/data/` files and the Docker volume are separate stores; resetting one does not reset the other.

### Refresh open-data snapshots

The repository already includes the sample snapshots needed for the demo. To re-import data, use the scripts from the repository root:

```sh
python3 scripts/import_open_data.py
python3 scripts/import_person_names.py
```

Review source metadata and licence requirements in [OPEN_DATA.md](OPEN_DATA.md) before distributing updated snapshots. Rebuild the Docker frontend after updating bundled data.

# Kopā — e-pakalpojumu prototype

A minimal Latvian website exploring how several public services could be combined around one life event. This is a hackathon demo, not an official government portal. All flows are illustrative. A small demo backend checks fictional personas kodi against a database of invented people; there is no real authentication or connection to government systems.

## Run with Docker

Install Docker with Docker Compose (Docker Desktop includes both), then run:

```sh
docker compose up --build -d
```

Open http://localhost:8080/login.html to preview the demo login. The root page shows the portal landing-page mockup. nginx serves `public/` and proxies `/api/` to the Python demo server in the `api` container; the people database lives in the `people-data` Docker volume.

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

- `server/seed_people.py` generates 60 fictional Latvian people (name, surname, e-mail on `example.com`, phone, personas kods in the `DDMMYY-XXXXX` format with fictional birth dates and random suffixes). `python3 server/seed_people.py --list` prints them so you can pick a code; `--reset` regenerates them.
- `POST /api/login` takes `{"personasKods": "..."}`, looks the code up and returns a random bearer token plus the person. Only a SHA-256 hash of the token is stored, and sessions expire after 7 days.
- `GET /api/me` validates the token; `POST /api/logout` revokes it.
- `public/auth.js` keeps the token in `localStorage`, so a reload or new tab stays signed in. The profile and services pages redirect to login without a valid session; a rejected token signs the user out, while an unreachable server keeps the cached session.
- `python3 server/test_api.py` checks the API end to end against a throwaway database.

A personas kods alone is not a credential in any real system. This works only because the data is fictional; never use it with real people or codes.

## Current interface

- `public/index.html` — portal landing-page mockup.
- `public/login.html` — demo login; enter a personas kods from the demo database to open the profile.
- `public/profile.html` — demo profile showing the signed-in person's data and a simulated inbox notice about services related to a child's birth.
- `public/pakalpojumi.html` — illustrative service list opened from the inbox notice.
- `public/styles.css` and `public/auth.css` — responsive portal and login styles.
- `public/app.js` — text-size toggle.
- `public/auth.js` — login request, token storage, session restore, route guarding and log out.
- `server/` — demo API and fictional people database (SQLite).
- `Dockerfile`, `nginx.conf`, and `compose.yaml` — Dockerized static hosting plus the demo API.

This is not government authentication and does not connect to Latvija.gov.lv, eParaksts, or email. Use only the invented personas kodi from the demo database. The profile notice and service descriptions are illustrative and do not confirm eligibility or submit applications.

## Further work

1. Add real service application flows only after verifying official eligibility, deadlines, and requirements.
2. Integrate address selection and municipality lookup using the imported open data.
3. Verify the complete flow in Docker once the Docker daemon is running.

## Open data

Import licensed data snapshots with `python3 scripts/import_open_data.py`. See [data/README.md](data/README.md) for sources, licenses, attribution, generated files and limitations. Import before rebuilding Docker to include nationwide address JSON. The small address sample remains available without the bulk import.

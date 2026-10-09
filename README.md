# Kopā — e-pakalpojumu prototype

A minimal Latvian website exploring how several public services could be combined around one life event. This is a hackathon demo, not an official government portal. All flows are illustrative; there is no authentication, backend, or connection to government systems.

## Run with Docker

Install Docker with Docker Compose (Docker Desktop includes both), then run:

```sh
docker compose up --build -d
```

Open http://localhost:8080/login.html to preview login. The root page is intentionally blank.

Stop the website:

```sh
docker compose down
```

After changing files, run `docker compose up --build -d` again to rebuild.

## Develop locally

The website uses plain HTML, CSS, and JavaScript, with no build tools or package dependencies. For a local preview without Docker:

```sh
python3 -m http.server 8080 --directory public
```

## Current interface

- `public/index.html` — intentionally blank landing page.
- `public/login.html` — reference-inspired login selection with one eParaksts mobile option and a required demo acknowledgment.
- `public/eparaksts-login.html` — separate user-number form with cancel and confirm controls.
- `public/styles.css` — responsive styles for both login screens and prototype icons.
- `public/app.js` — demo acknowledgment gating and local form handling. Confirm clears the input and shows a design-only message; it does not authenticate or create a user.
- `Dockerfile`, `nginx.conf`, and `compose.yaml` — Dockerized static hosting.

Both login pages display clear prototype notices. They do not use official logos, send phone notifications, connect to eParaksts, persist input, or access a database. Use invented user numbers only.

## Next steps

1. Design the newborn service page and shared application flow on the currently blank landing page.
2. Define the demo user model, database schema, and account/session behavior before connecting the login mockup. Keep demo identities separate from real authentication.
3. Add the demo profile and explicit simulated approval/result screens.
4. Integrate address selection and municipality lookup using the imported open data.
5. Verify official benefit amounts, deadlines, eligibility conditions, and municipal grant rules before implementing recommendations.
6. Verify the complete flow in Docker once the Docker daemon is running.

## Open data

Import licensed data snapshots with `python3 scripts/import_open_data.py`. See [data/README.md](data/README.md) for sources, licenses, attribution, generated files and limitations. Import before rebuilding Docker to include nationwide address JSON. The small address sample remains available without the bulk import.

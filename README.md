# Kopā — e-pakalpojumu prototype

A minimal Latvian website exploring how several public services could be combined around one life event. This is a hackathon demo, not an official government portal. All flows are illustrative; there is no real authentication, backend, or connection to government systems.

## Run with Docker

Install Docker with Docker Compose (Docker Desktop includes both), then run:

```sh
docker compose up --build -d
```

Open http://localhost:8080/login.html to preview the demo login. The root page shows the portal landing-page mockup.

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

- `public/index.html` — portal landing-page mockup.
- `public/login.html` — demo login; any non-empty sequence of digits opens the profile.
- `public/profile.html` — demo profile with a simulated inbox notice about services related to a child's birth.
- `public/pakalpojumi.html` — illustrative service list opened from the inbox notice.
- `public/styles.css` and `public/auth.css` — responsive portal and login styles.
- `public/app.js` — stores the invented demo number in `sessionStorage` for the current browser tab, guards the profile and services pages, and clears the demo session on logout.
- `Dockerfile`, `nginx.conf`, and `compose.yaml` — Dockerized static hosting.

This is not government authentication and does not connect to Latvija.gov.lv, eParaksts, email, or a database. The demo number is kept only for the current browser tab; use invented digits only. The profile notice and service descriptions are illustrative and do not confirm eligibility or submit applications.

## Further work

1. Add real service application flows only after verifying official eligibility, deadlines, and requirements.
2. Integrate address selection and municipality lookup using the imported open data.
3. Verify the complete flow in Docker once the Docker daemon is running.

## Open data

Import licensed data snapshots with `python3 scripts/import_open_data.py`. See [data/README.md](data/README.md) for sources, licenses, attribution, generated files and limitations. Import before rebuilding Docker to include nationwide address JSON. The small address sample remains available without the bulk import.

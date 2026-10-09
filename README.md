# Kopā — e-pakalpojumu prototype

A minimal Latvian website exploring how several public services could be combined around one life event. This is a hackathon demo, not an official government portal. All flows are illustrative; there is no authentication, backend, or connection to government systems.

## Run with Docker

Install Docker with Docker Compose (Docker Desktop includes both), then run:

```sh
docker compose up --build -d
```

Open http://localhost:8080.

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

## Files

- `public/index.html` — page content and service cards.
- `public/styles.css` — responsive styles.
- `public/app.js` — mock service bundles and their steps.
- `Dockerfile` — Nginx image serving the website.
- `nginx.conf` — web server configuration on port 8080.
- `compose.yaml` — local container setup.

To add a bundle, add a card in `index.html` with a `data-bundle` key and a matching entry in `app.js`.

## Open data

Import licensed data snapshots with `python3 scripts/import_open_data.py`. See [data/README.md](data/README.md) for sources, licenses, attribution, generated files and limitations. Import before rebuilding Docker to include nationwide address JSON. The small address sample remains available without the bulk import.

# snipbox — Lab 2 service

A small HTTP API written in **Python 3.14 / FastAPI** that stores short text
snippets in **PostgreSQL**. In Lab 1 it used an SQLite file on a volume; here
the data lives in a separate database container instead.

- Container port: **8080** (published on host **8400** by `../docker-compose.yaml`)
- Swagger UI: <http://localhost:8400/docs>
- Database: `SNIPBOX_DATABASE_URL`, default
  `postgresql://snipbox:snipbox@snipbox-db:5432/snipbox` (`snipbox-db` is the
  database's container name)

## API

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Service metadata |
| `GET` | `/health` | Liveness probe, also reports the snippet count |
| `POST` | `/snippets` | Create a snippet, returns `201` and an 8-char id |
| `GET` | `/snippets?limit=&offset=` | List snippets, newest first |
| `GET` | `/snippets/{id}` | Read one snippet, `404` if unknown |
| `DELETE` | `/snippets/{id}` | Delete one snippet, `204` / `404` |

`POST /snippets` takes `content` (required, 1..64000 chars), plus optional
`title` (default `untitled`) and `language` (default `text`). Validation errors
come back as `422`.

## Run it

The Compose file lives in the repository root, see the [root README](../README.md).

## Publish

The image is published to the GitHub Container Registry:

```bash
docker build -t snipbox:2.0.0 service/   # from the repository root
docker login ghcr.io -u dezsokee         # password = PAT with write:packages
docker tag snipbox:2.0.0 ghcr.io/dezsokee/snipbox:2.0.0
docker tag snipbox:2.0.0 ghcr.io/dezsokee/snipbox:latest
docker push ghcr.io/dezsokee/snipbox:2.0.0
docker push ghcr.io/dezsokee/snipbox:latest
```

A freshly pushed package is **private** by default. Make it public under
*GitHub -> Packages -> snipbox -> Package settings -> Change visibility*,
otherwise `docker pull` needs credentials.

## Develop locally

The tests need a real PostgreSQL; without `SNIPBOX_DATABASE_URL` they are skipped.

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
docker run --rm -d --name snipbox-test-db -p 55432:5432 \
  -e POSTGRES_USER=snipbox -e POSTGRES_PASSWORD=snipbox postgres:18-alpine
export SNIPBOX_DATABASE_URL=postgresql://snipbox:snipbox@localhost:55432/snipbox
pytest
uvicorn app.main:app --reload --port 8400
docker rm -f snipbox-test-db
```

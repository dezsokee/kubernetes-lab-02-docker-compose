# Microservices and Kubernetes: Lab 2 - Docker Compose and deployment

In Lab 2 you will deploy a Docker Compose service in a live environment. For the purposes of this lab, for the duration of the lab on Friday you will be given a Hetzner environment where you can experiment with this setup.

You have two choices:
- In case you've finished [Lab 1](https://github.com/darktohka/kubernetes-lab-02-docker), you can choose to extend your Docker container with a docker-compose.yaml environment:
  1. First, create the corresponding docker-compose.yaml environment that will start your Docker container, as if you were starting it with a simple Docker command.
  2. You can test with `docker compose up -d`, or shut down your environment with `docker compose down`.
  3. Add an external database to your code that persists data over the previous in-memory storage mechanism.
  4. Create two new networks: one for your backend and one for your database. Connect your backend to both networks, but connect the database only to the database network.
  5. Add the new database to the docker-compose, and have the application connect to it through its **container name**.
- You can also choose to install any self-hosted application that is packaged using a Dockerfile. For example, try [Immich](https://docs.immich.app/install/docker-compose), an awesome Google Photos alternative.

Try to deploy the application in the live environment!

If possible, set up Caddy as your web server.

Fork this repository and continue your work here.

---

## Solution: snipbox + PostgreSQL

The Lab 1 service lives in [`service/`](service/README.md). It moved from an
SQLite file to a PostgreSQL container, and [`docker-compose.yaml`](docker-compose.yaml)
starts both.

```
            host :8400
                |
   [backend] ---+--- snipbox ---+--- [database, internal]
                                |
                            snipbox-db (postgres:18-alpine, volume snipbox-db-data)
```

- **`backend` network**: the app's public side. The published port goes through it, and later a reverse proxy (Caddy) can join it.
- **`database` network**: `internal: true`, so it has no route to the internet. Only `snipbox` and `snipbox-db` are on it.
- `snipbox` is on both networks, `snipbox-db` only on `database`, with no published port.
- The app reaches the database by its **container name**: `postgresql://...@snipbox-db:5432/snipbox`.
- `snipbox` waits for `snipbox-db` to pass its `pg_isready` healthcheck (`depends_on: condition: service_healthy`).

### Run

```bash
cp .env.example .env              # optional, set a real password
docker compose up --build -d
curl -s localhost:8400/health     # {"status":"ok","snippets":0,"db":"snipbox-db:5432/snipbox"}

curl -s -X POST localhost:8400/snippets \
  -H 'Content-Type: application/json' \
  -d '{"title":"hello","content":"print(1)"}'

docker compose down               # containers and networks gone, volume kept
docker compose up -d              # the snippet is still there
docker compose down -v            # also drops the database volume
```

### Check the network isolation

```bash
docker inspect -f '{{.Name}}: {{range $k,$v := .NetworkSettings.Networks}}{{$k}} {{end}}' snipbox snipbox-db
docker exec snipbox python -c "import socket; print(socket.gethostbyname('snipbox-db'))"
docker port snipbox-db            # prints nothing: the database is not published
```

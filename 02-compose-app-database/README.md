# Compose: app, database, backup and restore

Run a Python notes app with PostgreSQL, replace both containers while keeping their data, diagnose two connection faults and restore a database backup into a fresh project.

Tested 17 November 2026 in a local Linux VM. No cloud account. Requires working Docker, Docker Compose plugin, Git, Neovim and a browser. Video in production.

## Start here

```bash
git clone https://github.com/varcodefather/docker101.git
cd docker101/02-compose-app-database/starter
docker compose version
cp .env.example .env
nvim .env
```

The example password is a disposable local-demo value. Keep `.env` untracked and use no real credentials in this exercise. `APP_PORT=8080` is the browser port.

The starter includes the app, its Dockerfile, initialization SQL and two fault overrides. It deliberately has no `compose.yaml`. The completed files one folder up are the reference if you get stuck. Keep commands in this same project directory and terminal.

## Write the configuration

Open `nvim compose.yaml` and enter:

```yaml
services:
  web:
    build: .
    image: compose-notes:v1
    ports:
      - "127.0.0.1:${APP_PORT:-8080}:8000"
    environment:
      PGHOST: db
      PGDATABASE: notes
      PGUSER: demo
      PGPASSWORD: ${DB_PASSWORD:?copy .env.example to .env first}
    depends_on:
      db:
        condition: service_healthy
    mem_limit: 256m
    cpus: 0.5
  db:
    image: postgres:17.12-alpine
    environment:
      POSTGRES_DB: notes
      POSTGRES_USER: demo
      POSTGRES_PASSWORD: ${DB_PASSWORD:?copy .env.example to .env first}
    volumes:
      - db-data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/01-notes.sql:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $$POSTGRES_USER -d $$POSTGRES_DB"]
      interval: 2s
      timeout: 3s
      retries: 30
      start_period: 5s
    mem_limit: 512m
    cpus: 1.0
volumes:
  db-data:
```

`web` connects to `db` by service name on the project network. Browser traffic enters through `127.0.0.1:8080`; no database port is published to the host. `service_healthy` waits for the database health check during startup, not for every application query forever. The web app still reports connection errors if its database becomes unavailable later.

`db-data` mounts the PostgreSQL 17 data directory. This path is specific to the selected image major version; review the official image documentation before changing majors. `init.sql` creates the table only when the database data directory is first initialized. Editing that file or changing `POSTGRES_PASSWORD` does not migrate or reset an existing database.

The doubled `$$` in the health check defers variable expansion to the container shell. CPU and memory limits keep the two-service lab small.

## Build, start and save notes

```bash
export COMPOSE_PROJECT_NAME=compose101
docker compose config --quiet
docker compose build
docker compose up -d --wait --wait-timeout 120
docker compose ps
```

Configuration validation succeeds silently. Expect `web` running and `db` healthy. Open [the notes app](http://127.0.0.1:8080) and save:

1. `First note from the browser`
2. `Containers replaced; notes stay`

Read the same two rows in PostgreSQL:

```bash
docker compose exec -T db psql -U demo -d notes -c "SELECT id, body FROM notes ORDER BY id;"
docker volume ls --filter label=com.docker.compose.project=compose101
```

The named volume is `compose101_db-data`. Replace both containers:

```bash
docker compose up -d --force-recreate --wait --wait-timeout 120
docker compose ps
```

Reload the browser. Both notes remain; the app container identity changes. Replacing a container leaves its named volume available. This is persistence, not a backup.

## Diagnose the wrong database hostname

```bash
nvim compose.bad-host.yaml
docker compose -f compose.yaml -f compose.bad-host.yaml up -d --force-recreate web
```

Reload the browser: `Database connection failed`. Inspect the actual error and restore the base configuration:

```bash
docker compose logs --tail 30 web
docker compose up -d --force-recreate web
```

The log refers to `dbb`, but the service is `db`. The later file overrides only the supplied fields. Reload and check both saved notes. Container startup success does not guarantee a successful database request.

## Diagnose rejected credentials

```bash
nvim compose.bad-password.yaml
docker compose -f compose.yaml -f compose.bad-password.yaml up -d --force-recreate web
```

Reload, then inspect:

```bash
docker compose logs --tail 30 web
docker compose up -d --force-recreate web
```

This fault reaches PostgreSQL but produces `password authentication failed`. Reload after restoring the base settings: both notes return. Fix the client's credentials; don't delete a working data volume to fix an app setting.

## Export a database-native backup

```bash
docker compose exec -T db pg_dump -U demo -d notes --clean --if-exists --no-owner --no-acl > notes-backup.sql
nvim notes-backup.sql
```

Search `/COPY public.notes` and find both note rows, then quit without changes. `pg_dump` produces a consistent logical export of this database. Shell redirection saves it outside the containers. `-T` disables terminal allocation for redirected data. This lesson does not back up PostgreSQL cluster-wide roles or implement a production backup schedule.

In the original browser app, add `Added after backup`. The live database now has three notes; the backup has two.

## Restore into a fresh project

```bash
APP_PORT=8081 docker compose --project-name compose101-restore up -d --wait --wait-timeout 120
docker volume ls --filter label=com.docker.compose.project=compose101-restore
```

Open [the fresh app](http://127.0.0.1:8081): no notes. Its separate volume is `compose101-restore_db-data`. Original app at port 8080 still has three.

Stop writes to the restore database, import the trusted lab backup, then start its app:

```bash
APP_PORT=8081 docker compose --project-name compose101-restore stop web
APP_PORT=8081 docker compose --project-name compose101-restore exec -T db psql -X -U demo -d notes -v ON_ERROR_STOP=1 < notes-backup.sql
APP_PORT=8081 docker compose --project-name compose101-restore start web
```

Expect successful SQL statements including `COPY 2`. `-X` ignores client startup files; `ON_ERROR_STOP=1` makes SQL errors fail the import. This import replaces objects in the restore database. It is a disposable destination, not a live database upgrade procedure.

Reload both pages: restored app has the original **two** notes; original app still has **three**. Read the app result, not only the import's exit status.

## Cleanup

These commands deliberately delete both demo databases and their named volumes. Keep `notes-backup.sql` if you want the export. Without `--volumes`, ordinary `down` leaves the named volume available.

```bash
APP_PORT=8081 docker compose --project-name compose101-restore down --volumes --remove-orphans
docker compose down --volumes --remove-orphans
docker image rm compose-notes:v1
docker volume ls --filter label=com.docker.compose.project=compose101
```

No global prune. Source files and local SQL export remain. The original terminal's `COMPOSE_PROJECT_NAME` must still be `compose101`; set it again if you opened another terminal.

## References

- [Compose startup order and health dependencies](https://docs.docker.com/compose/how-tos/startup-order/)
- [PostgreSQL official image: initialization variables and data directories](https://hub.docker.com/_/postgres)
- [PostgreSQL logical backup and restore](https://www.postgresql.org/docs/current/backup-dump.html)
- [Psycopg installation](https://www.psycopg.org/psycopg3/docs/basic/install.html)

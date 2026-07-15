# Setup

> **No setup required to try the app.** The hosted version is live at [linguaalayam.org](https://linguaalayam.org).
> Follow this guide only if you want to run the full stack locally (ingest, RAG pipeline, MCP server).

## Prerequisites

- Python 3.11+
- [Poetry](https://python-poetry.org/docs/#installation)
- Docker (for the local Postgres + pgvector container)
- Node.js 20+ (only for `make sync-jayasree` — vendors the handwriting-trace widget; the app runs fine without it, just without the trace button)

---

## Database

LinguAalayam runs against a **local Postgres + pgvector** instance. You create and own the database — there are no external credentials to obtain.

```bash
docker run -d --name linguaalayam \
  -e POSTGRES_PASSWORD=yourpassword \
  -p 5432:5432 \
  ankane/pgvector

docker exec -it linguaalayam psql -U postgres -c "CREATE DATABASE linguaalayam;"
```

---

## Install

```bash
poetry install
poetry run pre-commit install
make sync-jayasree   # optional — vendors the handwriting-trace widget from npm
```

---

## Environment variables

Copy `.env.example` to `.env`. The DB values must match what you used when starting the container above — you define them, there is nothing to look up.

```
DB_USER=postgres
DB_PASSWORD=yourpassword        # same as POSTGRES_PASSWORD in the docker run command
DB_HOST=localhost
DB_PORT=5432
DB_NAME=linguaalayam
ANTHROPIC_API_KEY=sk-ant-...   # required for llm=anthropic (get from console.anthropic.com)
OPENAI_API_KEY=sk-...          # required for llm=openai
# DB_SSLMODE=require           # uncomment for hosted Postgres
```

---

## Migrations

```bash
poetry run alembic upgrade head
```

---

## Data download

Download the corpora from [olam.in/p/open](https://olam.in/p/open) and place them at:

```
data/
├── enml/
│   ├── olam          # Olam EN→ML (TSV)
│   └── ekkurup.yml   # Ekkurup EN→ML thesaurus (YAML)
└── mlml/
    └── datuk         # Datuk ML→ML (TSV)
```

---

## Ingest

```bash
poetry run ingest                               # full corpus ingest (all three corpora)
poetry run ingest corpus=debug                  # 50-entry test ingest
poetry run ingest embedding=multilingual_e5_large
```

Ingestion is checkpoint-based — safe to restart after a failure without re-embedding already-vectorised entries.

---

## Data sources

| Corpus | Type | Status |
|---|---|---|
| Olam EN→ML | English → Malayalam | ✅ Active |
| Datuk | Malayalam → Malayalam | ✅ Active |
| Ekkurup | EN→ML thesaurus | ✅ Active |

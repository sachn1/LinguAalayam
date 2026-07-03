<p align="center">
  <img src="linguaalayam/static/logo.svg" alt="lingua·ആലയം" width="440" />
</p>

> Abode of words.
>
> *lingua (Latin: language) · ആലയം (Malayalam: abode)*

**[linguaalayam.org](https://linguaalayam.org)** · [API docs](https://linguaalayam.org/docs) · [MCP endpoint](https://linguaalayam.org/mcp)

---

## What this is

Malayalam has one of the richest literary and grammatical traditions in the world, yet for many Malayalis, especially those in the diaspora, the everyday digital experience offers little depth. Over years, a community of linguists, engineers, and volunteers has built open corpora, morphological analysers, transliteration libraries, wiktionary, and many more. **lingua·ആലയം** (read as linguaalayam) brings these resources together under one roof.

Think of it as a [Leo.org](https://leo.org) for Malayalam, a lexicology companion rather than just a lookup tool. The goal is insight: how a word inflects, what grammatical forms it takes, how it relates to its synonyms, how it reads in Roman script alongside its Malayalam script. Whether you are a native speaker exploring the depth of the language, a diaspora Malayali reconnecting with it, or a student learning it for the first time, the aim is understanding over raw coverage.

The retrieval layer is also exposed as a Model Context Protocol (MCP) server and REST API, making it accessible to AI assistants and developer tools. That is an add-on, a way to bring the lexical knowledge base into the current AI ecosystem, not the primary purpose.

### With the diaspora in mind

There's an old joke about Neil Armstrong stepping off the Apollo Lunar Module onto the moon and hearing a familiar Malayalam film song drifting through the silence. Following the melody, he found a makeshift tea stall hand-painted sign reading "മതം പറയരുത്" (Don't discuss religion). Behind the counter, a ചേട്ടൻ (a brother or a guy) in a lungi (traditional South Asian wrap-around cloth) looked up and asked: "എന്താ മോനെ? ചായ വേണോ?" (What's up son, do you want some tea?). [This video is more fun!](https://www.youtube.com/shorts/EGrQ05nRm14)

The joke lands because it is barely a joke. A large share of Malayalam speakers live outside Kerala <sup>[[1](https://timesofindia.indiatimes.com/city/kochi/keralites-working-182-countries-worldwide/articleshow/105460653.cms)]</sup> and their everyday language is a mix: code-switching between Malayalam, English, and Manglish. Linguaalayam is built with them in mind::

- **Romanisation toggle**: Malayalam definitions shown alongside Roman-script transliteration, so you can read while still learning the script.
- **Voice search**: tap the mic icon in the search bar to speak your query; speech language follows your browser locale.
- **Morphological context**: inflected forms like *കേരളത്തിൻറെ* are parsed to show the base word and grammatical role, powered by [mlmorph](https://morph.smc.org.in/).
- **Manglish search**: type *oduka*, *santhosham*, *veedu* in Roman script and get Malayalam results, powered by [Varnam](https://varnamproject.com) (Subin Siby).
- **Clickable definitions**: words in definitions that exist as their own dictionary entries are clickable links.
- **Four corpora**: Olam (EN→ML), Datuk (ML→ML), Shabdataaravali/Sayahna (classical ML→ML, 1917), Ekkurup (EN thesaurus).

We are bringing in more features for you here!

---

linguaalayam is open-source, self-hostable, and built entirely on openly-licensed corpora and tools. There could be errors but we are here to fix them all and learn together :)

> Built with the assistance of [Claude](https://claude.ai) (Anthropic).

---

## REST API

The hosted API is available at `https://linguaalayam.org`. No API key required for dictionary lookup.

```
GET /lookup/exact?query=run&source=olam_enml
GET /lookup/fuzzy?query=run&top_k=5
GET /lookup/semantic?query=ഓടുക&top_k=5
```

Full OpenAPI docs: [linguaalayam.org/docs](https://linguaalayam.org/docs)

---

## MCP setup (Claude Code, Claude Desktop, Cursor, Windsurf, Cline, and more)

The MCP server is hosted at `linguaalayam.org/mcp`. Three tools: `exact_lookup`, `fuzzy_lookup`, `semantic_lookup`. Works with any LLM backend. OAuth is automatic (RFC 7591 + PKCE, no login, no API key). The URL alone is enough.

See [linguaalayam/mcp/README.md](linguaalayam/mcp/README.md) for the JSON snippet, client-specific config file paths (Claude Desktop, Cursor, Windsurf, Cline, Continue), and self-hosted setup.

---

## RAG pipeline

```bash
poetry run rag 'rag.query=ephemeral'
RAG_QUERY='what does pastoral mean?' poetry run rag
poetry run rag 'rag.query=run' llm=nollm    # no API key needed
poetry run rag 'rag.query=run' llm=openai   # switch provider
```

See [linguaalayam/rag/README.md](linguaalayam/rag/README.md) for pipeline details and config options.

---

## Quick start

```bash
poetry install
cp .env.example .env        # see docs/setup.md
poetry run alembic upgrade head
poetry run ingest
```

See [docs/setup.md](docs/setup.md) for database setup, environment variables, and data download.


### Docker

Prefer containers? This spins up the full stack (app + Postgres):

```bash
docker compose up --build
```

Just need the database running (e.g. for `psql`/DBeaver access)?

```bash
docker compose up -d db
```

### Data storage

Corpus files (`data/`) and database snapshots (`linguaalayam.sql.gz`) are tracked with [DVC](https://dvc.org), backed by a private remote.

---

## Docs

- [User guide](docs/user-guide.md): search modes, corpora, AI synthesis explained
- [Architecture](docs/architecture.md): system flow, module reference, tech stack
- [Roadmap](docs/roadmap.md): versioned goals
- [Setup](docs/setup.md): database, environment, migrations, corpora
- [API docs](https://linguaalayam.org/docs): live OpenAPI / Swagger UI
- [MCP server](linguaalayam/mcp/README.md): tools, resources, testing
- [RAG pipeline](linguaalayam/rag/README.md): nodes, config, debug tool
- [Evaluation](linguaalayam/eval/README.md): metrics, query categories

---

## Testing

```bash
poetry run pytest
poetry run pytest tests/corpus      # corpus parsers
poetry run pytest tests/database    # DB layer (SQLite, no Postgres needed)
```

---

## Data sources

Four corpora, all openly licensed. See [DATA_SOURCES.md](DATA_SOURCES.md) for full attribution and licence terms.

| Corpus | Description | Source |
|---|---|---|
| Olam EN→ML | English–Malayalam dictionary | [olam.in/p/open](https://olam.in/p/open) |
| Datuk | Malayalam–Malayalam dictionary | [olam.in/p/open/datuk](https://olam.in/p/open/datuk) |
| Ekkurup | English–Malayalam thesaurus | [olam.in/p/open/ekkurup](https://olam.in/p/open/ekkurup) |
| Shabdataaravali | Malayalam–Malayalam dictionary (classical) | [dict.sayahna.org](https://dict.sayahna.org) |

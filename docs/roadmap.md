# Roadmap

### v0.2 — RAG ready
- [x] Query preprocessing — extract target word from natural language queries
- [x] Hybrid search — exact, fuzzy, and semantic retrieval
- [x] Response synthesis — LLM answer from top-k retrieved entries
- [x] Evaluation harness — retrieval metrics on a labeled query set

### v0.3 — MCP server
- [x] MCP server with three tools: `exact_lookup`, `fuzzy_lookup`, `semantic_lookup`
- [x] Claude Code integration via `.mcp.json` project config
- [x] Claude Desktop setup instructions

### v0.4 — LLM adapter + MCP resources
- [x] `LLMAdapter` ABC with `AnthropicAdapter`, `OpenAIAdapter`, `NoLLMAdapter`
- [x] Provider selected via Hydra `_target_` — adding a new provider requires only a subclass and a YAML file
- [x] `NoLLMAdapter` — no API key needed; synthesis returns formatted reranker output
- [x] Remove HuggingFace text-generation; LLM is always API-backed or absent
- [x] MCP resource `dictionary://{headword}` alongside the existing tools

### v0.5 — Additional corpora + code quality
- [x] **Datuk** — ML→ML corpus (Malayalam headwords with Malayalam definitions)
- [x] **Ekkurup** — EN→ML thesaurus (synset entries with grouped EN synonyms and ML translations)
- [x] Per-corpus filtering in retrieval via `source` parameter on all three tools
- [x] Hydra-driven corpus parsers — adding a corpus requires only a YAML config entry, no Python change
- [x] Code quality sweep — dead code removed, encapsulation fixed, silent failures logged

### v2.0 — REST API, hosted MCP, and stable release
- [x] Thin FastAPI layer over `DictionaryTools` — `/lookup/exact`, `/lookup/fuzzy`, `/lookup/semantic`
- [x] Web UI — HTMX + Jinja2 served from FastAPI; settings sidebar, structured POS-grouped results, live filter refresh
- [x] Hosted MCP server at `/mcp` — zero-config for AI clients (`{ "url": "https://linguaalayam.org/mcp" }`)
- [x] Bring-your-own-key LLM synthesis (Anthropic / OpenAI) — key stored in browser localStorage, injected as request header, never persisted server-side
- [x] Self-hosted deployment on Hetzner CX33 (Nuremberg, €7.72/month) — Docker Compose, nginx reverse proxy
- [x] Domain and HTTPS — [linguaalayam.org](https://linguaalayam.org) live with Let's Encrypt cert
- [x] CI/CD — GitHub Actions deploy to VPS on `bump:` commit via forced-command SSH key
- [x] User guide, MCP client setup guide (Claude Code, Claude Desktop, Cursor, Windsurf, Cline, Continue)
- [x] CPU-only PyTorch in Docker — explicit `pytorch-cpu` source, no CUDA packages on VPS

### v2.1 — Intent-based source filter
- [x] **Intent-based source filter** — corpus dropdown replaced with human-readable intents (EN → Malayalam, Thesaurus, Malayalam word); backend unchanged

### v2.2 — Diaspora, accessibility, i18n, and search quality
- [x] **UI language toggle** — English / Malayalam interface labels; JSON locale bundles, no page reload
- [x] **Romanised output toggle** — Malayalam definitions returned with ISO romanisation alongside for users who cannot read the script (toggle with **A ↔ അ** button)
- [x] **Smart multi-word search** — phrases and definition queries (multiple words in fuzzy mode) automatically route to semantic retrieval instead of trigram matching
- [x] **Manglish input (formal romanisation)** — Latin queries that miss exact/fuzzy are tried against multiple formal transliteration schemes; falls back to semantic if no match. Known limitation: informal romanisation ("oduka") is not reliably handled — resolved in v2.8 via Varnam.
- [x] **Evaluation harness** — corpus-derived query sets (10 intents, EN + ML inputs, generated from live DB); offline model comparison with per-intent metrics and MLflow tracking

### v2.3 — Logo, MCP setup page, and OAuth
- [x] **Elephant logo** — amber elephant mark; transparent PNG; used as favicon, navbar logo, and PWA install icon
- [x] **One-click MCP setup page** — `/mcp/setup` with prominent URL copy box, per-client step-by-step guide, and developer configs collapsed; connection test button
- [x] **OAuth 2.0 for Claude.ai browser connector** — passthrough `OAuthAuthorizationServerProvider` (RFC 7591 dynamic registration, PKCE/S256, token refresh, revocation); `MCP_ISSUER_URL` env var; FastMCP 2.x wires all endpoints automatically

### v2.5 — i18n foundation and Android
- [x] **i18n foundation** — EN/ML locale bundles complete; architecture is locale-file-based (drop a new JSON in `static/locales/` to add a language); additional UI languages tracked in backlog
- [x] **Android TWA** — PWA icons generated (48–512px PNG + maskable); `manifest.json` updated for Android; `/.well-known/assetlinks.json` endpoint live; `android/twa-manifest.json` (Bubblewrap config) checked in; `android/README.md` documents full build + Play Store publish flow
- [x] **MCP OAuth** — passthrough OAuth 2.0 (RFC 7591 dynamic registration, PKCE/S256); root-level proxy so origin-based clients (Claude Desktop, Inspector) and path-aware clients both work from the URL alone

### v2.6 — Play Store compliance and Android production
- [x] **Privacy policy** — `/privacy` page for Play Store listing compliance
- [x] **Android build artifacts** — gitignore for APK/AAB/keystore; Play Store closed testing active (12 testers, 14-day window)

### v2.7 — Search quality, voice input, and attribution
- [x] **ml2en romanisation** — swapped ISO 15919 for informal ml2en; correct chillu handling (ൺ→n, ൽ→l, ർ→r); romanisation now covers Datuk definitions and Ekkurup Malayalam synonym groups
- [x] **Morphological analysis** — `mlmorph` integration; human-readable labels per headword (e.g. *past verb of ഓടുക*); shown inline in results
- [x] **Voice search** — Web Speech API mic button with EN/ML language toggle; hidden on unsupported browsers; `ml-IN` recognition returns Malayalam Unicode script
- [x] **Mobile layout** — header stacks logo above tagline on ≤600px; fixes cramped Android TWA layout
- [x] **Open data attribution** — `DATA_SOURCES.md` with per-dataset authors and licences (ODbL for Olam/Datuk, CC BY-SA 4.0 for Ekkurup by E.K. Kurup); footer and settings sidebar updated
- [x] **Service worker v2** — static assets cached first, pages network-first with offline fallback

### v2.8 — Informal Manglish, ingest-time morphology, and UI cleanup
- [x] **Informal Manglish via Varnam** — Latin queries that miss exact/fuzzy now try the [Varnam](https://varnamproject.com) API for informal romanisation (e.g. *oduka* → *ഓടുക*) before falling back to the local formal transliteration schemes from v2.2; resolves the informal-romanisation gap noted in v2.2
- [x] **Search mode removed** — the exact/fuzzy/semantic selector is gone from both UI and `/search`; retrieval is always trigram-first (exact matches score 1.0) with automatic semantic fallback, simplifying the query surface
- [x] **`ml_ml` source filter** — Datuk + Sayahna merged under one "All Malayalam → Malayalam" UI option; the old `datuk`-expands-to-both behaviour is now explicit
- [x] **Morphology computed at ingest time** — `DatukEntry`/`SayahnaEntry` store mlmorph analysis at parse time instead of recomputing it per search request
- [x] **Clickable definitions** — ML→ML definition tokens that exist as their own headword become links, via a cached `DictionaryTools.ml_headword_set()`
- [x] **`transliteration/` package** — `morphology.py`, `varnam.py`, and the existing romanisation helpers (`core.py`) consolidated under one package
- [x] **Search UI simplification** — visible language dropdown removed (kept only as a hidden field driven by speech recognition / browser locale); mode selector and its help text removed
- [x] **Handwriting trace** — [jayasree](https://github.com/sachn1/jayasree) (published to npm, formerly the malayalam-stroker repo) animates stroke-by-stroke handwriting for Malayalam headwords; trace button on Datuk/Sayahna entries, lazy-loaded client-side so the ~11.6MB glyph/stroke data is never fetched unless clicked; vendored from npm at build time via `make sync-jayasree`, no runtime CDN dependency

### Unreleased — Traffic analytics, voice UX, and Manglish search quality
- [x] **Traffic/usage analytics** — `request_log` table + `RequestLoggingMiddleware` logs every request (route type, search term, IP/country, bot heuristic); `/admin/analytics` dashboard (HTMX-polling, HTTP Basic Auth) shows traffic by route, top search terms, top clients, and outbound-link clicks
- [x] **Click-beacon tracking** — `POST /track/click` (label allow-list) covers interactions with no server route of their own: handwriting trace (`jayasree`), the romanise toggle (`ml2en`), voice search (`web_speech`), and outbound links (GitHub, docs, mlmorph credit)
- [x] **Route classification fixes** — `/mcp/setup` (human page view) no longer conflated with `/mcp` (actual AI-assistant protocol traffic); `/docs` classified as `api_docs` instead of falling into a generic bucket
- [x] **Voice search language picker** — flag icon grouped directly against the mic button (not elsewhere on the page) so it reads unambiguously as "language to speak," not an interface/search-language setting; a first-time onboarding modal (opened by either the mic or the flag) replaces the previous silent browser-locale default
- [x] **Manglish/English ambiguity handling** — words valid in both (e.g. *kali* → the goddess Kali, or *കലി*, "anger") now show the confident English result plus a collapsed "Did you mean this in Malayalam?" suggestion (Varnam candidates capped at 5), instead of silently picking one interpretation
- [x] **Search-quality fixes** — Varnam candidates are validated via exact/lemma lookup instead of fuzzy match, eliminating false "did you mean" links to words that don't actually exist; fallback triggers (Varnam, semantic) now check for a *confident* result, not just a non-empty one, so weak spelling coincidences (e.g. "kundi" matching unrelated entries like "Kunti" at 30%) no longer silently block better matches or show a misleading empty "0 results" heading
- [x] **Search box sync** — clicking a definition word-link or a "did you mean" suggestion now updates the visible search box to match, instead of leaving it showing the original query

### v2.9 — Word of the Day
- [ ] **Phonetic Manglish index** — add `headword_roman` column storing ml2en output for each Malayalam headword; pg_trgm index enables reliable informal Manglish matching (e.g. "oduka" → "otuka" → "ഓടുക") without the ISO 15919 formalism gap; requires migration + re-ingest
- [ ] **Word of the Day** — daily featured word, filtered by frequency list to exclude common words (top 5k excluded); alternates EN/ML by default
- [ ] **User preference** — app settings: EN only / ML only / alternate; stored in `localStorage`
- [ ] **Push notifications** — service worker push for word-of-the-day on Android

### v3.0 — On-device AI synthesis (in-app purchase)
- [ ] Generate synthetic (query → answer) training pairs from existing corpus (headword + POS + definition + synonyms)
- [ ] Fine-tune a small multilingual model on Malayalam dictionary Q&A
- [ ] Quality eval harness before shipping — answer quality metrics (BLEU + human eval on Malayalam output); do not ship without passing eval
- [ ] Serverless inference (Modal or RunPod) — pay-per-request, no idle GPU cost
- [ ] AI synthesis as in-app purchase — core app stays free, premium tier unlocks prose answers at lower price point than user-managed API keys


### Backlog
- [ ] **Production embedding upgrade** — eval confirms the current model underperforms on Malayalam semantic and cross-lingual queries; upgrade and re-ingest (~2h CPU); no schema change
- [ ] **Cross-lingual result bridging** — EN query surfaces Malayalam equivalents; ML query surfaces English equivalents
- [ ] `ml_from_ml_semantic` retrieval quality — definition → headword currently at 20% hit@1; revisit after embedding upgrade
- [ ] Reranker for mixed-script result sets — deduplicate and rerank exact + fuzzy + semantic hits in a single pass
- [ ] Explore English gloss of ML→ML definitions (requires hosted model or translation API budget)
- [ ] `int8` quantisation for faster inference
- [ ] Query caching for repeated lookups
- [ ] Monitoring — retrieval latency and top-k quality metrics in production

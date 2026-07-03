# User Guide

LinguAalayam is a Malayalam dictionary that searches across four open corpora — in English, Malayalam, or Manglish.

**Live at [linguaalayam.org](https://linguaalayam.org)**

---

## How search works

Type a word in the search bar and results appear automatically. There is no mode to switch — the search engine finds the best matches using trigram similarity, which naturally ranks exact matches at the top followed by close variants.

- Type **English** to find Malayalam definitions: *run*, *happiness*, *ephemeral*
- Type **Malayalam** to find definitions in any direction: *ഓടുക*, *സന്തോഷം*
- Type **Manglish** (romanised Malayalam) to find Malayalam results: *oduka*, *santhosham*, *veedu*
- Type a **description or phrase** to find the word: *feeling of nostalgia*, *complete absence of sound*

---

## Voice search

On browsers that support speech recognition (Chrome, Edge, Safari), a microphone icon appears inside the search bar. Tap it, speak, and the transcribed text is searched automatically. The speech language is set from your browser locale.

---

## Corpora (source filter)

LinguAalayam searches four open Malayalam corpora. Leave the filter on **All** to search everything at once.

| Filter | Corpora | Direction | Best for |
|---|---|---|---|
| **All** | All four | — | General search |
| **English → Malayalam** | Olam | EN → ML | Translating an English word |
| **All Malayalam → Malayalam** | Datuk + Sayahna | ML → ML | Understanding a Malayalam word |
| **Datuk** | Datuk | ML → ML | Contemporary Malayalam definitions |
| **Sayahna** | Shabdataaravali (1917) | ML → ML | Classical/archaic Malayalam |
| **Thesaurus → Ekkurup** | Ekkurup | EN thesaurus | English synonyms with Malayalam equivalents |

Shabdataaravali uses 1917 Malayalam orthography. Headwords ending in `ு்` are archaic word-boundary markers, not errors.

---

## Clickable words

Malayalam words in definitions are clickable when they exist as their own dictionary entry. Clicking a word searches for it directly.

---

## AI synthesis (optional)

By default, results are raw dictionary entries. Add an API key in [Settings](/settings) to enable AI synthesis — the app reads the top results and writes a plain-English explanation alongside them.

### How to get a key

| Provider | Where | Key format |
|---|---|---|
| Anthropic (Claude) | [console.anthropic.com/settings/keys](https://console.anthropic.com/settings/keys) | `sk-ant-…` |
| OpenAI (GPT) | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) | `sk-…` |

**Privacy:** your key is stored only in your browser's `localStorage`. It is sent directly to the AI provider with each request and never stored on LinguAalayam's servers.

---

## Tips

- **No results?** Try removing the corpus filter.
- **Manglish search:** *oduka* → *ഓടുക* is powered by [Varnam](https://varnamproject.com) (Subin Siby).
- **Morphological context:** for Malayalam queries, the base form and grammatical role are shown above results, powered by [mlmorph](https://morph.smc.org.in/).
- **MCP for AI assistants:** LinguAalayam is available as an MCP server at `https://linguaalayam.org/mcp`. See the [MCP setup guide](../linguaalayam/mcp/README.md) to connect Claude, Cursor, Windsurf, or Cline.

---

## Data sources

All corpora are openly licensed. Full attribution: [DATA_SOURCES.md](../DATA_SOURCES.md).

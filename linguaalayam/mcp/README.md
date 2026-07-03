# MCP Server

LinguAalayam exposes its three retrieval tools as an [MCP](https://modelcontextprotocol.io) server directly from the hosted app — no local install, no Python, no database setup required.

The MCP endpoint is live at `https://linguaalayam.org/mcp`.

---

## Tools

| Tool | Description |
|---|---|
| `exact_lookup(word, source?)` | Case-insensitive exact headword match |
| `fuzzy_lookup(query, threshold?, top_k?, source?)` | Trigram similarity search via pg_trgm |
| `semantic_lookup(query, top_k?, source?)` | Embedding cosine search via HNSW |

All tools accept an optional `source` parameter to filter by corpus: `olam_enml`, `datuk`, `sayahna`, or `ekkurup`. Omit to search all corpora.

---

## Authentication

The endpoint is protected by OAuth 2.0, but there is **nothing to configure** — LinguAalayam is a public dictionary, so the authorization server auto-approves every client. Your MCP client handles the whole handshake transparently:

- **Dynamic client registration** (RFC 7591) — the client registers itself; no client ID to create.
- **PKCE / S256** public-client flow — no secret, no login screen.
- Discovery metadata is served at both the domain root and the path-aware
  well-known locations, and the OAuth endpoints (`/authorize`, `/token`,
  `/register`, `/revoke`) are reachable at both the root and under `/mcp` — so
  origin-based clients (Claude, the MCP Inspector) and spec-strict path-aware
  clients all connect from the URL alone.

So a plain `{"url": "https://linguaalayam.org/mcp"}` is all any client needs. Opening the URL in a browser returns `401 invalid_token` — that is expected; only an MCP client carrying an OAuth token gets through.

---

## Client setup

Add this block to your MCP client config. No command, no package, no local database.

```json
{
  "mcpServers": {
    "linguaalayam": {
      "url": "https://linguaalayam.org/mcp"
    }
  }
}
```

Where to put the file:

| Client | Config file | Notes |
|---|---|---|
| **Claude Code** | `.mcp.json` in your project root | Picked up automatically — no restart |
| **Claude Desktop** (macOS) | `~/Library/Application Support/Claude/claude_desktop_config.json` | Restart Claude Desktop after saving |
| **Claude Desktop** (Windows) | `%APPDATA%\Claude\claude_desktop_config.json` | Restart Claude Desktop after saving |
| **Claude Desktop** (Linux) | `~/.config/Claude/claude_desktop_config.json` | Restart Claude Desktop after saving |
| **Cursor** (global) | `~/.cursor/mcp.json` | Reload Window (Cmd/Ctrl+Shift+P) after saving |
| **Cursor** (project) | `.cursor/mcp.json` in project root | Reload Window after saving |
| **Windsurf** | `~/.codeium/windsurf/mcp_config.json` | Restart Windsurf; tools appear in Cascade panel |

---

### Cline (VS Code)

Cline uses a different settings key. Open VS Code settings (`Cmd/Ctrl+,`), search for `Cline MCP`, click **Edit in settings.json**:

```json
{
  "cline.mcpServers": {
    "linguaalayam": {
      "url": "https://linguaalayam.org/mcp"
    }
  }
}
```

Or use the Cline sidebar → MCP Servers tab → Add Server → paste the URL.

---

### Continue (VS Code / JetBrains)

Continue uses YAML. In `~/.continue/config.yaml`:

```yaml
mcpServers:
  - name: linguaalayam
    url: https://linguaalayam.org/mcp
```

---

## A note on LLM providers

The MCP server is LLM-agnostic — it returns plain text from the dictionary. Any LLM backend your client uses (Claude, GPT-4o, Gemini, Mistral, Llama, etc.) can call the tools and synthesise answers from the results. You do not need an Anthropic API key to use these tools.

---

## Client not listed?

If your IDE or MCP client is not covered above, [open an issue](https://github.com/sachn1/linguaalayam/issues/new) and mention which client you are using. Most clients that support MCP use the same JSON format — only the config file path differs.

---

## Self-hosted instance

Running the full stack locally (see [docs/setup.md](../../docs/setup.md))? The MCP server is already mounted at `/mcp` on the local app. Point your client at:

```json
{
  "mcpServers": {
    "linguaalayam": {
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

No separate MCP process needed — it runs inside the same FastAPI app.

---

## Testing

### MCP Inspector (interactive web UI)

The server speaks **Streamable HTTP** and is OAuth-protected, so test it the way a real client does — over the URL, not by opening it in a browser (an unauthenticated request correctly returns `401`).

1. Start the app — the MCP server is mounted at `/mcp` inside the same FastAPI process:

   ```bash
   poetry run uvicorn linguaalayam.api.app:app --port 8000
   ```

2. Launch the Inspector in a second terminal. It needs a **Linux** Node.js:

   ```bash
   npx @modelcontextprotocol/inspector
   ```

   It prints a `http://localhost:6274/?MCP_PROXY_AUTH_TOKEN=…` link and opens your browser.

   **WSL gotcha:** if `npx` resolves to the Windows install you'll get
   `zsh: .../nodejs/npx: bad interpreter: /bin/sh^M` (CRLF line endings). You need
   a Linux Node. With [fnm](https://github.com/Schniz/fnm), either load it into the
   shell (`eval "$(fnm env)"`) or call the Linux binary directly, e.g.:

   ```bash
   # one-off, no shell setup:
   ~/.local/share/fnm/node-versions/<version>/installation/bin/npx @modelcontextprotocol/inspector
   ```

   To make it permanent, add to `~/.zshrc`:

   ```bash
   export PATH="$HOME/.local/share/fnm:$PATH"
   eval "$(fnm env --use-on-cd)"
   ```

3. In the Inspector connection form:

   | Field | Value |
   |---|---|
   | **Transport Type** | `Streamable HTTP` |
   | **URL** | `http://localhost:8000/mcp` |

   Click **Connect**. OAuth runs automatically (no login screen), then the three tools appear under the **Tools** tab and the `dictionary://{headword}` resource under **Resources**.

> Point at `https://linguaalayam.org/mcp` to test the hosted server the same way.

> Do **not** use `mcp dev` / the stdio "command" override — this server runs over HTTP inside the app, not as a stdio subprocess.

### Python notebook

[`notebooks/mcp_testing.ipynb`](../../notebooks/mcp_testing.ipynb) calls tool functions directly without the MCP protocol layer — fastest way to iterate on output format or debug retrieval.

```python
from linguaalayam.mcp import server
server._ensure_docker_db()
server._tools = server._init_tools()

print(server.exact_lookup("run"))
print(server.fuzzy_lookup("runing", threshold=0.2))
print(server.semantic_lookup("to move quickly on foot", top_k=5))
```

#!/usr/bin/env bash
# Vendor jayasree's runtime files from node_modules into static/, so the
# server can serve them with no bundler and no runtime npm/CDN dependency.
# Regenerated from package.json on every build — never committed (see .gitignore).
set -euo pipefail

SRC="node_modules/jayasree/src"
DEST="linguaalayam/static/vendor/jayasree"

if [[ ! -d "$SRC" ]]; then
    echo "ERROR: ${SRC} not found. Run 'npm install' first." >&2
    exit 1
fi

mkdir -p "$DEST"
cp "$SRC/index.js" "$SRC/style.css" "$SRC/glyph-data.json" "$SRC/stroke-data.json" "$DEST/"

echo "Synced jayasree $(node -p "require('./node_modules/jayasree/package.json').version") into ${DEST}"

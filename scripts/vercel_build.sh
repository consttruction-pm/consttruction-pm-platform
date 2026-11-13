#!/usr/bin/env bash
# Assemble the static workspace shell for Vercel.
#
# The deployed origin serves the same HTML and bundles the preview server
# serves locally, but from a flat `public/` directory:
#   /                     -> index.html
#   /app                  -> rewritten to the session-gated function
#   /login                -> login.html
#   /styles.css           -> styles.css
#   /dist/*.bundle.js     -> dist/web/src/*.bundle.js
set -euo pipefail
cd "$(dirname "$0")/.."

npm --prefix apps/web run build

rm -rf public
mkdir -p public/dist public/client-sync/src
cp apps/web/index.html apps/web/app.html apps/web/login.html apps/web/styles.css public/
cp -R apps/web/public/. public/
cp -R apps/web/dist/web/src/. public/dist/
if [ -d apps/web/dist/client-sync/src ]; then
  cp -R apps/web/dist/client-sync/src/. public/client-sync/src/
fi

# Never ship a source map that exposes server-only paths in production.
find public/dist -name "*.map" -delete

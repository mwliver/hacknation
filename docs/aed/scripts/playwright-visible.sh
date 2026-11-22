
#!/usr/bin/env bash
set -euo pipefail

echo ""
echo "======================================"
echo "       MISJA AED - PLAYWRIGHT"
echo "       TRYB WIDOCZNY (CHROMIUM)"
echo "======================================"
echo ""

# Katalog główny repozytorium
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
FRONTEND="$REPO_ROOT/frontend_latest"

if [ ! -d "$FRONTEND" ]; then
    echo "Blad: nie znaleziono frontend_latest!"
    exit 1
fi

cd "$FRONTEND"

echo "[1/3] Sprawdzam zaleznosci..."

if [ ! -d "node_modules" ]; then
    npm install
fi

echo "[2/3] Sprawdzam Chromium..."
npx playwright install chromium 

echo "[3/3] Uruchamiam testy AED w widocznej przegladarce..."
echo ""

npm run e2e:aed -- --headed

echo ""
echo "Testy Playwright zakonczone!"

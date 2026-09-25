#!/usr/bin/env bash
# install.sh — commitguard Unix/macOS installer
#
# Run once from the commitguard directory.
# Adds the directory to your shell profile so 'git' resolves to the shim.
#
# Usage:
#   cd path/to/commitguard
#   chmod +x install.sh git
#   ./install.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "[commitguard] Starting installation..."

# ── 1. Verify Python 3.11+ is available ───────────────────────────────────
PYTHON_BIN=""
for py in python3.12 python3.11 python3 python; do
    if command -v "$py" &>/dev/null; then
        PY_VER=$("$py" -c "import sys; print(sys.version_info[:2])" 2>/dev/null || echo "(0, 0)")
        if "$py" -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" 2>/dev/null; then
            PYTHON_BIN="$py"
            break
        fi
    fi
done

if [ -z "$PYTHON_BIN" ]; then
    echo "[commitguard] ERROR: Python 3.11+ not found. Install it first." >&2
    exit 1
fi
echo "[commitguard] Found: $($PYTHON_BIN --version)"

# ── 2. Make shim executable ───────────────────────────────────────────────
chmod +x "$SCRIPT_DIR/git"
echo "[commitguard] Made git shim executable."

# ── 3. Detect shell profile ───────────────────────────────────────────────
PROFILE=""
if [ -n "${ZSH_VERSION:-}" ] || [ "$SHELL" = "/bin/zsh" ] || [ "$SHELL" = "/usr/bin/zsh" ]; then
    PROFILE="${HOME}/.zshrc"
elif [ -n "${BASH_VERSION:-}" ] || [ "$SHELL" = "/bin/bash" ]; then
    PROFILE="${HOME}/.bashrc"
    [ "$(uname)" = "Darwin" ] && PROFILE="${HOME}/.bash_profile"
else
    PROFILE="${HOME}/.profile"
fi

EXPORT_LINE="export PATH=\"${SCRIPT_DIR}:\$PATH\"  # commitguard"

# ── 4. Check if already installed ─────────────────────────────────────────
if grep -qF "# commitguard" "$PROFILE" 2>/dev/null; then
    echo "[commitguard] Already installed in $PROFILE."
    exit 0
fi

# ── 5. Append PATH export to profile ──────────────────────────────────────
echo "" >> "$PROFILE"
echo "$EXPORT_LINE" >> "$PROFILE"
echo "[commitguard] Added to $PROFILE: $EXPORT_LINE"

# ── 6. Optional: pyyaml hint ──────────────────────────────────────────────
if ! "$PYTHON_BIN" -c "import yaml" 2>/dev/null; then
    echo "[commitguard] Tip: pyyaml not installed. Run: pip install pyyaml"
    echo "              (Required only if you use config.yaml)"
fi

echo ""
echo "[commitguard] Installed successfully."
echo "  Run: source $PROFILE   (or restart your terminal)"
echo "  To uninstall: ./uninstall.sh"

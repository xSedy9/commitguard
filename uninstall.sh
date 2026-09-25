#!/usr/bin/env bash
# uninstall.sh — commitguard Unix/macOS uninstaller
#
# Removes the commitguard PATH export from your shell profile.
#
# Usage:
#   ./uninstall.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Detect profile (same logic as install.sh)
PROFILE=""
if [ -n "${ZSH_VERSION:-}" ] || [ "$SHELL" = "/bin/zsh" ] || [ "$SHELL" = "/usr/bin/zsh" ]; then
    PROFILE="${HOME}/.zshrc"
elif [ -n "${BASH_VERSION:-}" ] || [ "$SHELL" = "/bin/bash" ]; then
    PROFILE="${HOME}/.bashrc"
    [ "$(uname)" = "Darwin" ] && PROFILE="${HOME}/.bash_profile"
else
    PROFILE="${HOME}/.profile"
fi

echo "[commitguard] Uninstalling from $PROFILE..."

if ! grep -qF "# commitguard" "$PROFILE" 2>/dev/null; then
    echo "[commitguard] Not found in $PROFILE — nothing to remove."
    exit 0
fi

# Remove lines containing "# commitguard" and adjacent blank lines
if command -v gsed &>/dev/null; then
    gsed -i '/# commitguard/d' "$PROFILE"
else
    sed -i'' '/# commitguard/d' "$PROFILE"
fi

echo "[commitguard] Removed from $PROFILE."
echo "  Run: source $PROFILE   (or restart your terminal)"

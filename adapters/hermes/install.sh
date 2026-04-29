#!/usr/bin/env bash
# adapters/hermes/install.sh
# First-time setup: generate .hermes/skills/, symlink to ~/.hermes/skills/wally-trader/,
# install git pre-commit hook for auto-sync.

set -euo pipefail

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO"

# Verify Python 3 + pyyaml available
python3 -c "import yaml" 2>/dev/null || {
  echo "⚠️  PyYAML not installed. Installing..."
  pip3 install --user pyyaml
}

# First generation
echo "🔄 Generating .hermes/skills/ from system/..."
python3 "$REPO/adapters/hermes/transform.py"

# Symlink to ~/.hermes/skills/wally-trader/ if Hermes is installed
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
HERMES_SKILLS="$HERMES_HOME/skills"
LINK="$HERMES_SKILLS/wally-trader"
TARGET="$REPO/.hermes/skills"

if [ -d "$HERMES_HOME" ]; then
  mkdir -p "$HERMES_SKILLS"
  if [ -L "$LINK" ]; then
    if [ "$(readlink "$LINK")" != "$TARGET" ]; then
      rm "$LINK"
      ln -s "$TARGET" "$LINK"
      echo "✓ Updated symlink $LINK → $TARGET"
    else
      echo "✓ Symlink $LINK → $TARGET already correct"
    fi
  elif [ -e "$LINK" ]; then
    BACKUP="$LINK.backup-$(date +%s)"
    mv "$LINK" "$BACKUP"
    ln -s "$TARGET" "$LINK"
    echo "✓ Backed up existing $LINK → $BACKUP and created symlink"
  else
    ln -s "$TARGET" "$LINK"
    echo "✓ Created symlink $LINK → $TARGET"
  fi
else
  echo "ℹ️  Hermes not installed yet ($HERMES_HOME missing). Skipping symlink."
  echo "   Install Hermes: curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash"
  echo "   Then re-run this install.sh to create the symlink."
fi

# Install git pre-commit hook (use rev-parse for worktree compat)
HOOK_PATH="$(git rev-parse --git-path hooks/pre-commit)"
HOOK_DIR="$(dirname "$HOOK_PATH")"
mkdir -p "$HOOK_DIR"

MARKER='# hermes-adapter-v1'

if [ -f "$HOOK_PATH" ] && grep -q "$MARKER" "$HOOK_PATH"; then
  echo "✓ pre-commit hook already installed (hermes v1)"
else
  if [ -f "$HOOK_PATH" ]; then
    cp "$HOOK_PATH" "$HOOK_PATH.backup-$(date +%s)"
    echo "   Backed up existing pre-commit to $HOOK_PATH.backup-*"
  fi

  cat >> "$HOOK_PATH" <<'EOF'

# hermes-adapter-v1 — auto-regenerate .hermes/skills/ on system/ changes
__REPO="$(git rev-parse --show-toplevel)"
__CHANGED=$(git diff --cached --name-only | grep -E '^system/(commands|agents)/' || true)
if [ -n "$__CHANGED" ]; then
  echo "[hermes-adapter] system/ changed → re-generando .hermes/skills/"
  python3 "$__REPO/adapters/hermes/transform.py" || exit 1
  git add "$__REPO/.hermes"
fi
EOF
  chmod +x "$HOOK_PATH"
  echo "✓ pre-commit hook installed at $HOOK_PATH"
fi

echo ""
echo "✅ Hermes adapter ready."
echo "   .hermes/skills/ will auto-regenerate on git commit when system/ changes."
echo ""
echo "📋 Next steps:"
echo "   1. Install Hermes (if not yet): curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash"
echo "   2. hermes setup    # configure model + provider"
echo "   3. hermes          # start interactive CLI (auto-loads AGENTS.md + skills)"
echo ""
echo "💡 Configure TradingView MCP (optional):"
echo "   hermes config set mcp.tradingview.command node"
echo "   hermes config set mcp.tradingview.args '[\"$REPO/tradingview-mcp/src/server.js\"]'"

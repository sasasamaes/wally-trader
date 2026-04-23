#!/usr/bin/env bash
# adapters/codex/install.sh
# ⚠️ UNTESTED — Codex CLI not installed locally. Report issues to regenerate.

set -euo pipefail

REPO="$(cd "$(dirname "$0")/../.." && pwd)"

echo "⚠️  Codex adapter is UNTESTED."
echo "   Prerequisite: OpenAI API key + codex CLI installed."
echo "   If something breaks: report and regenerate."
echo ""

python3 "$REPO/adapters/codex/transform.py"

echo ""
echo "✅ Codex prompts written to ~/.codex/prompts/"
echo "   Invocation (in Codex session): /cmd_morning  /agent_morning-analyst-ftmo  etc."

#!/usr/bin/env bash
# scripts/hermes_smoke_new.sh
# Verify the new commands (added 2026-05-09 and 2026-05-10) are accessible
# from Hermes context.
#
# Tests: pine-gen, liq-heatmap, strategy-import, session_quality gate,
#        backtest_punk_filters, F1+F2 vetoes in punk-hunt-analyst.
#
# Usage: bash scripts/hermes_smoke_new.sh
# Exit code: 0 if all pass, 1 if any fail.

set -uo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"

PASS=0
FAIL=0

pass() { echo "[PASS] $1"; ((PASS++)); }
fail() { echo "[FAIL] $1 — $2"; ((FAIL++)); }

echo "=== Hermes New-Features Smoke Test ==="
echo "    Repo: $REPO"
echo ""

# ── 1. Skills synced to Hermes ────────────────────────────────────────────────
for skill in pine-gen liq-heatmap strategy-import; do
  SKILL_FILE="$REPO/.hermes/skills/wally-commands/$skill/SKILL.md"
  if [ -f "$SKILL_FILE" ]; then
    pass "Hermes skill: $skill"
  else
    fail "Hermes skill: $skill" "missing $SKILL_FILE — run: make sync-all"
  fi
done

# ── 2. Underlying scripts exist + executable ─────────────────────────────────
for script in liq_heatmap.py strategy_distill.py session_quality.py backtest_punk_filters.py; do
  SCRIPT="$REPO/.claude/scripts/$script"
  if [ -x "$SCRIPT" ]; then
    pass "Script executable: $script"
  elif [ -f "$SCRIPT" ]; then
    fail "Script executable: $script" "exists but not chmod +x"
  else
    fail "Script executable: $script" "missing"
  fi
done

# ── 3. Functional smoke: liq-heatmap can fetch + compute ─────────────────────
LIQ_OUT=$(python3 .claude/scripts/liq_heatmap.py --symbol BTCUSDT --top 3 2>&1 | head -50)
if echo "$LIQ_OUT" | grep -q '"longs_liq"'; then
  pass "liq-heatmap functional (fetched live data)"
else
  fail "liq-heatmap functional" "no longs_liq key in output (likely network or API issue)"
fi

# ── 4. Functional smoke: strategy_distill with raw text ─────────────────────
DISTILL_OUT=$(python3 .claude/scripts/strategy_distill.py --text "Long when RSI < 30" --name "smoketest_$$" --quiet 2>&1)
if echo "$DISTILL_OUT" | grep -q '"slug"'; then
  pass "strategy-import functional (raw text mode)"
  # Cleanup test artifact
  rm -f .claude/strategy_imports/raw/smoketest_*.txt 2>/dev/null
else
  fail "strategy-import functional" "no slug in output: ${DISTILL_OUT:0:100}"
fi

# ── 5. Functional smoke: session_quality gate ────────────────────────────────
SQ_OUT=$(python3 .claude/scripts/session_quality.py --symbol BTCUSDT 2>&1 | head -20)
if echo "$SQ_OUT" | grep -q '"verdict"'; then
  pass "session_quality gate functional"
else
  fail "session_quality gate functional" "no verdict key (network or API issue)"
fi

# ── 6. punk-hunt agent has FASE 4.5 vetoes ──────────────────────────────────
if grep -q "FASE 4.5" .hermes/skills/wally-agents/punk-hunt-analyst/SKILL.md; then
  pass "punk-hunt agent has FASE 4.5 (F1+F2 vetoes)"
else
  fail "punk-hunt FASE 4.5" "vetoes not synced — run: make sync-all"
fi

# ── 7. signal-validator + trade-validator have FASE 0.5 ─────────────────────
for agent in signal-validator trade-validator; do
  if grep -q "FASE 0.5\|session_quality" ".hermes/skills/wally-agents/$agent/SKILL.md"; then
    pass "$agent has FASE 0.5 (session-quality gate)"
  else
    fail "$agent FASE 0.5" "session-quality not wired"
  fi
done

# ── 8. Hermes daemon CWD is repo root (if launchd loaded) ──────────────────
if command -v launchctl >/dev/null 2>&1 && launchctl list | grep -q hermes-daemon; then
  PLIST_CWD=$(awk '/<key>WorkingDirectory<\/key>/{getline; print}' .claude/launchd/com.wally.hermes-daemon.plist | sed 's/.*<string>\(.*\)<\/string>.*/\1/' | head -1)
  if [ "$PLIST_CWD" = "$REPO" ]; then
    pass "Hermes daemon CWD = repo root"
  else
    fail "Hermes daemon CWD" "expected $REPO, got $PLIST_CWD"
  fi
else
  echo "[INFO] Hermes daemon not loaded — skipping CWD check"
fi

# ── 9. Backtest report exists ───────────────────────────────────────────────
if [ -f docs/backtest_findings_2026-05-10_punk_hunt_filters.md ]; then
  pass "Backtest report saved"
else
  fail "Backtest report" "docs/backtest_findings_2026-05-10_punk_hunt_filters.md missing"
fi

echo ""
echo "=== Summary ==="
echo "  PASSED: $PASS"
echo "  FAILED: $FAIL"

if [ $FAIL -eq 0 ]; then
  echo ""
  echo "✅ All new features ready for Hermes."
  echo "From Telegram: /liq-heatmap BTCUSDT  |  /pine-gen <desc>  |  /strategy-import youtube <URL>"
  exit 0
else
  echo ""
  echo "❌ Some checks failed. Fix above before relying on Hermes for these commands."
  exit 1
fi

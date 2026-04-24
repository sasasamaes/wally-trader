#!/bin/bash
# uninstall_agent.sh — Remove WallyWatcher launchd agent + .app bundle.
#
# Idempotent. Leaves .claude/watcher/status.json + dashboard.md + notifications.log
# intact (history). Your repo + pending_orders.json unaffected.

set -eu

PLIST="$HOME/Library/LaunchAgents/com.wallytrader.watcher.plist"
APP="$HOME/.local/Applications/WallyWatcher.app"
CONFIG="$HOME/.config/wallytrader.conf"

if [ -f "$PLIST" ]; then
    launchctl unload "$PLIST" 2>/dev/null || true
    rm "$PLIST"
    echo "Removed plist: $PLIST"
else
    echo "Plist not present (skipping): $PLIST"
fi

if [ -d "$APP" ]; then
    rm -rf "$APP"
    echo "Removed bundle: $APP"
else
    echo "Bundle not present (skipping): $APP"
fi

if [ -f "$CONFIG" ]; then
    rm "$CONFIG"
    echo "Removed config: $CONFIG"
fi

echo ""
echo "WallyWatcher uninstalled."
echo "To re-install: bash <repo>/.claude/watcher/install_agent.sh"

# Hermes Operational Layer — Setup Guide

## What this enables

Send `/punk-hunt` from your phone's Telegram → Hermes (running on your Mac) receives it → invokes MCP tools → draws levels on TradingView Desktop — all from anywhere in the world.

```
You (Telegram mobile)
        │  /punk-hunt
        ▼
┌──────────────────────┐
│  Telegram Bot API    │
└──────────┬───────────┘
           │  webhook / polling
           ▼
┌──────────────────────────────────────────────────────┐
│  Hermes daemon  (your Mac, always-on)                │
│  ~/.hermes/skills/wally-trader/  ← symlinked         │
│    wally-commands/  wally-agents/  wally-skills/     │
└────────┬─────────────────────────┬───────────────────┘
         │                         │
         ▼                         ▼
┌────────────────┐       ┌──────────────────────┐
│  wally MCP     │       │  tradingview MCP      │
│  (Python venv) │       │  (Node.js, TV Desktop)│
│  12 tools      │       │  78 tools             │
└────────────────┘       └──────────┬────────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │  TradingView Desktop  │
                         │  chart redraws live   │
                         └──────────────────────┘
```

---

## Prerequisites

- Mac with TradingView Desktop installed and logged in to your account
- Telegram account + ability to create a bot via @BotFather
- Python 3.11+ (`python3 --version`)
- Node.js 18+ (`node --version`) — for tradingview-mcp
- `uv` package manager (`pip install uv` or `brew install uv`)
- Repo cloned at `/Users/josecampos/Documents/wally-trader`

---

## Step 1 — Install Hermes

```bash
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
```

Verify:
```bash
hermes --version
```

If `hermes` is not found after install, add it to your PATH:
```bash
export PATH="$HOME/.hermes/bin:$PATH"   # add to ~/.zshrc
```

Configure model and provider (first-time setup):
```bash
hermes setup
```

---

## Step 2 — One-time project setup

Install Python MCP deps (wally + wally-trader-mcp into venv):
```bash
make wally-mcp-install
```

Install/refresh the Hermes adapter (generates skills, symlinks, registers MCPs):
```bash
make hermes-install
```

This single command does three things:
1. Generates `.hermes/skills/wally-{agents,commands,skills}/` from `system/`
2. Symlinks `~/.hermes/skills/wally-trader/` → `.hermes/skills/`
3. Registers all three MCP servers (`tradingview`, `wally`, `notion`) in Hermes config

Verify everything is wired up:
```bash
make hermes-smoke
```

Expected output: `6/6 checks passing`.

---

## Step 3 — Telegram bot setup

### Create a bot

1. Open Telegram → search for **@BotFather** → `/newbot`
2. Follow prompts → copy the **bot token** (looks like `7123456789:AAF...`)
3. Register it with Hermes:

```bash
hermes config set telegram.bot_token 7123456789:AAFyourTokenHere
```

### Find your chat_id

1. Send any message to your new bot in Telegram
2. Fetch updates:

```bash
curl -s "https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates" | python3 -m json.tool | grep '"id"'
```

3. The number next to `"id"` under `"chat"` is your chat_id (e.g. `123456789`)
4. Allowlist it:

```bash
hermes config set telegram.allowed_chat_ids '[123456789]'
```

### Test connection (before daemon)

```bash
hermes serve   # or: hermes bot  — adjust if your version differs
```

Send `/status` from Telegram → you should get a response within a few seconds.
Press Ctrl+C to stop (we'll daemonize it in the next step).

---

## Step 4 — Daemon setup (Mac always-on)

Load the launchd plist so Hermes starts automatically on login and restarts on crash:

```bash
make hermes-daemon-install
```

> **Important — confirm daemon command first.**  
> The plist defaults to `hermes serve`. If your Hermes version uses a different
> subcommand, edit `.claude/launchd/com.wally.hermes-daemon.plist` first:
>
> ```bash
> # Check what subcommand your Hermes uses:
> hermes --help | grep -E 'serve|bot|daemon|run'
> ```
>
> Then update the `<string>serve</string>` line accordingly.

**Prevent Mac sleep** (so the daemon keeps running):
- System Settings → Energy → Power Adapter → enable "Prevent automatic sleeping when display is off"

Verify daemon is running:
```bash
launchctl list | grep hermes
# Should show: com.wally.hermes-daemon   0   (exit code 0 = running OK)
```

Check the log:
```bash
tail -f logs/hermes-daemon.log
```

---

## Step 5 — Test Telegram → TradingView

With the daemon running and TradingView Desktop open on your chart:

**Basic test** (no TV needed):
```
Telegram: /status
```
Should respond with your current profile + market snapshot within ~30 seconds.

**TradingView drawing test**:
```
Telegram: /regime
```
Should respond with BTC regime analysis (calls wally MCP internally).

```
Telegram: /chart
```
Should clear TradingView and redraw current setup (calls tradingview MCP).

```
Telegram: /punk-hunt
```
Full autonomous scan → scores all bitunix assets → picks best setup → draws on TV.

---

## Daily operations

| Command | What it does |
|---|---|
| `/punk-morning` | Pre-session scan + Neptune TV setup |
| `/punk-hunt` | Autonomous setup scan, score≥70 |
| `/signal BTCUSDT SHORT entry=104000 sl=105500 tp=101000 leverage=10` | Validate Discord signal |
| `/regime` | Market regime detection (ADX + Donchian) |
| `/status` | Current profile dashboard |
| `/journal` | End-of-day log + equity update |

---

## Makefile reference

```bash
make hermes-install           # install/refresh adapter + register MCPs
make hermes-smoke             # 6-check smoke test
make hermes-daemon-install    # load launchd plist (start on login)
make hermes-daemon-uninstall  # unload + remove plist
make hermes-status            # show daemon status + MCP config
```

---

## Troubleshooting

### Hermes not responding to Telegram messages

```bash
# Is the daemon running?
launchctl list | grep hermes

# Is it crashing?
tail -50 logs/hermes-daemon.log

# Restart it manually:
launchctl unload ~/Library/LaunchAgents/com.wally.hermes-daemon.plist
launchctl load   ~/Library/LaunchAgents/com.wally.hermes-daemon.plist
```

### Wrong daemon subcommand (`exec: "hermes": not found` in log)

The plist uses the absolute path `/usr/local/bin/hermes`. If Hermes is installed
elsewhere (e.g. via Homebrew at `/opt/homebrew/bin/hermes`), update the plist:

```bash
which hermes   # → /opt/homebrew/bin/hermes
# Edit .claude/launchd/com.wally.hermes-daemon.plist:
#   change /usr/local/bin/hermes → /opt/homebrew/bin/hermes
make hermes-daemon-uninstall && make hermes-daemon-install
```

### MCP server timeout (tools not responding)

```bash
# Check what command Hermes will use for the wally MCP:
hermes config get mcp.wally.command
# Should return: /Users/josecampos/Documents/wally-trader/shared/wally_core/.venv/bin/python

# If missing, re-register:
bash adapters/hermes/configure_mcp.sh

# Verify venv is installed:
make hermes-smoke  # check 6
```

### TradingView drawing fails

1. TradingView Desktop must be **open and logged in** on the same Mac
2. The chart must be on the correct symbol (e.g. `BINANCE:BTCUSDT.P` for bitunix)
3. Check tradingview-mcp is running:

```bash
hermes config get mcp.tradingview.command
hermes config get mcp.tradingview.args
```

4. Test tradingview-mcp directly:

```bash
node tradingview-mcp/src/server.js
# Should start and wait — press Ctrl+C
```

### Telegram bot token expired or invalid

BotFather tokens don't expire, but if you revoked and re-issued:
```bash
hermes config set telegram.bot_token <new_token>
launchctl kickstart -k gui/$(id -u)/com.wally.hermes-daemon
```

### Chat_id not allowlisted (bot ignores messages)

```bash
hermes config get telegram.allowed_chat_ids
# Should show your chat_id — if empty:
hermes config set telegram.allowed_chat_ids '[YOUR_CHAT_ID]'
```

---

## Cross-device caveat

This setup ties all MCP tool execution to **your Mac being awake and running**.

If your Mac:
- **Sleeps** → Telegram bot stops responding (configure "prevent sleep" above)
- **Reboots** → daemon restarts automatically via launchd, but takes ~30s
- **Loses internet** → Telegram polling disconnects; daemon reconnects automatically

For 100% uptime: dedicate a Mac mini as an always-on Hermes host. Same setup,
just point TradingView MCP at a Mac mini running TV Desktop in screen share mode.

---

## Files reference

| File | Purpose |
|---|---|
| `adapters/hermes/install.sh` | One-command setup (skills + symlink + MCPs) |
| `adapters/hermes/configure_mcp.sh` | MCP registration only (idempotent) |
| `adapters/hermes/transform.py` | Converts `system/` → `.hermes/skills/` |
| `scripts/hermes_smoke.sh` | 6-check smoke test |
| `.claude/launchd/com.wally.hermes-daemon.plist` | launchd plist for daemon |
| `system/mcp/servers.json` | Canonical MCP server definitions |
| `logs/hermes-daemon.log` | Daemon stdout+stderr (created at runtime) |

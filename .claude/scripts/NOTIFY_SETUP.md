# Notification & Watcher Setup

Guía manual para activar los canales opcionales. macOS notif funciona sin setup.

## 1. Watcher launchd (obligatorio para auto-hourly)

```bash
cp .claude/watcher/launchd/com.wallytrader.watcher.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.wallytrader.watcher.plist
launchctl list | grep wallytrader
```

Verifica logs:
```bash
tail -f /tmp/wally_watcher.out
tail -f /tmp/wally_watcher.err
```

Manual trigger:
```bash
launchctl start com.wallytrader.watcher
```

Unload:
```bash
launchctl unload ~/Library/LaunchAgents/com.wallytrader.watcher.plist
```

## 2. TwelveData (precio forex/índices para ftmo/fotmarkets)

Free tier: 800 req/día.

1. Signup: https://twelvedata.com/
2. Copia tu API key.
3. Añade a `.claude/.env`:
   ```
   TWELVEDATA_API_KEY=tu_key
   ```
4. Smoke: `python3 -c "from price_feeds import twelvedata_price; print(twelvedata_price('EUR/USD'))"`

Si no configuras → los assets forex/índices no se vigilarán (price_feeds.PriceFeedError).
Retail BTCUSDT.P funciona sin esto (Binance público).

## 3. Telegram bot (stub en v1 — no-op si sin token)

No requerido para v1. Para v2:

1. En Telegram, busca `@BotFather` → `/newbot` → obtén token.
2. Inicia chat con tu bot → `/start`.
3. Obtén chat_id:
   ```bash
   curl "https://api.telegram.org/bot<TOKEN>/getUpdates" | jq .result[-1].message.chat.id
   ```
4. Añade a `.claude/.env`:
   ```
   TELEGRAM_BOT_TOKEN=xxx
   TELEGRAM_CHAT_ID=yyy
   ```

## 4. Email (Resend) — stub en v1

No requerido para v1. Para v3:

1. Signup: https://resend.com/ → API key.
2. Añade a `.claude/.env`:
   ```
   RESEND_API_KEY=xxx
   NOTIFY_EMAIL_TO=hamlik@redfi.io
   ```

## 5. Binance API — stub en v1 (--real flag)

NO REQUERIDO v1. El flag `--real` imprime "stub" en /order.

Para v4 (cuando implementes):

1. Binance cuenta → API Management → Create API.
2. Permisos: **Futures trade ON**, **Withdraw OFF**, **IP whitelist** tu IP local.
3. Añade a `.claude/.env`:
   ```
   BINANCE_API_KEY=...
   BINANCE_API_SECRET=...
   ```

Spec de seguridad: nunca commitees estas keys. `.env` está en `.gitignore`.

## Troubleshooting

**"No price feed mapping"**: el (profile, asset) no está en `price_feeds.ASSET_MAP`.
Edita el map.

**Watcher no corre**: `launchctl list | grep wallytrader`. Si ausente, `load` del plist.
Verifica permisos del script: `chmod +x .claude/scripts/watcher_tick.py`.

**Notif macOS silenciadas**: System Settings → Notifications → Script Editor
allow alerts.

**Claude -p headless falla**: ejecuta `which claude` — debe estar en PATH. Si
auth expiró, `claude /login`.

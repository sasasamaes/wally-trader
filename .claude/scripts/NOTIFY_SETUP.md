# Notification & Watcher Setup

Guía manual para activar los canales opcionales. macOS notif funciona sin setup.

## 1. Watcher launchd (obligatorio para auto-hourly)

Usa el instalador portable — resuelve `$HOME`, ruta del repo y binario Python
al momento de instalar. Funciona en cualquier Mac / usuario sin editar archivos.

### Instalar
```bash
bash .claude/watcher/install_agent.sh
```

El script:
1. Detecta el repo desde su propia ubicación (cualquier path, no solo `~/Documents/wally-trader`)
2. Busca Python 3.12+ (prefiere `brew install python@3.13`)
3. Instala deps si faltan (`requests pyyaml python-dateutil pytest`)
4. Copia `.claude/watcher/WallyWatcher.app` → `~/.local/Applications/`
5. Escribe `~/.config/wallytrader.conf` con `REPO_ROOT` + `PYTHON`
6. Renderiza `~/Library/LaunchAgents/com.wallytrader.watcher.plist` (sustituye path del bundle)
7. Registra el `.app` con LaunchServices (icono + display name en Background Items)
8. `launchctl load`

### Verificar
```bash
launchctl list | grep wallytrader              # debe aparecer
launchctl start com.wallytrader.watcher        # trigger manual
tail -f /tmp/wally_watcher.out                 # logs stdout
tail -f /tmp/wally_watcher.err                 # logs stderr
cat .claude/watcher/dashboard.md               # estado actual
```

### macOS Full Disk Access (obligatorio 1ª vez)
`~/Documents` está protegido por TCC. Concede FDA a:
- **System Settings → Privacy & Security → Full Disk Access → `+`**
- Agrega `/opt/homebrew/bin/python3.13` (u otra versión que detectó el installer)

Si instalaste con otro Python, verifica en `~/.config/wallytrader.conf`.

### Background Items display
El `.app` se muestra como **"Wally Trader Watcher"** con icono dachshund 🌭
(en vez de "bash") en *System Settings → General → Ítems de inicio y extensiones*.
Si sigue mostrando "bash" tras instalar, cierra/reabre System Settings para
refrescar el cache de LaunchServices.

### Desinstalar
```bash
bash .claude/watcher/uninstall_agent.sh
```
Remueve plist + bundle + config. Historial (`status.json`, `dashboard.md`,
`notifications.log`) queda intacto.

### Portabilidad — usar en otra máquina/usuario
Clona el repo en cualquier path (ej: `~/code/wally-trader`, `/opt/wally-trader`)
y corre `bash .claude/watcher/install_agent.sh`. El installer resuelve paths
absolutos automáticamente. No hay paths hard-coded en el repo.

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

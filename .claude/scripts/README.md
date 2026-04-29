# Claude Scripts — Sistema de Trading

Scripts de soporte para el sistema de trading. Cada uno tiene una función específica.

## 📋 Scripts

### `statusline.sh`
Muestra status line persistente: capital actual, PnL delta, trades hoy, ventana activa, hora CR, símbolo.

**Invocación automática:** configurado en `.claude/settings.json` → `statusLine.command`.

### `session_start.sh` (hook SessionStart)
Se ejecuta al iniciar sesión Claude en este proyecto. Inyecta contexto al modelo: hora, capital, estrategia activa, comandos disponibles, reglas sagradas.

**Output:** JSON con `hookSpecificOutput.additionalContext`.

### `stop_hook.sh` (hook Stop)
Se ejecuta cuando Claude termina. Auto-commit del journal si hubo cambios.

**Side effect:** `git add` + `git commit` silencioso en `DAILY_TRADING_JOURNAL.md`.

### `preprompt_check.sh` (hook UserPromptSubmit)
Se ejecuta cada vez que envías un prompt. Detecta palabras de auto-sabotaje ("arriesgar todo", "saltar filtro", "mover SL", etc.) y alerta.

**Output:** mensaje a stderr si detecta riesgo. No bloquea la acción.

### `notify.sh`
Helper para notificaciones macOS. Uso:
```bash
./notify.sh "Título" "Mensaje" [sonido]
```

Sonidos disponibles: Glass, Hero, Pop, Ping, Blow, Bottle, Frog, Funk, Morse, Submarine, Tink.

### `alert_setup.sh`
Monitor en background que vigila setup 4/4 filtros y notifica cuando aparece.

**Uso:**
```bash
./alert_setup.sh 6   # monitorea por 6 horas
./alert_setup.sh 3   # monitorea por 3 horas
```

### `daily_cron.sh`
Cron matutino para ser ejecutado a las 5:30 AM L-V. Envía notificación para recordar iniciar sesión.

**Instalación:**
```bash
crontab -e
# Añadir:
30 5 * * 1-5 ~/Documents/wally-trader/.claude/scripts/daily_cron.sh
```

### `notifications.log`
Log histórico de todas las notificaciones enviadas. Útil para debug.

### `cron.log`
Log de ejecuciones del cron matutino.

## 🔧 Instalación del cron

```bash
# Editar crontab
crontab -e

# Añadir estas líneas:
30 5 * * 1-5 ~/Documents/wally-trader/.claude/scripts/daily_cron.sh     # Lunes-Viernes 5:30 AM CR
0 17 * * 1-5 osascript -e 'display notification "Cierra posiciones ya!" with title "🕐 Fin de sesión"'  # 5:00 PM CR
0 10 * * 0 osascript -e 'display notification "Domingo: review semanal en Claude" with title "📊 Weekly Review"'  # Dom 10 AM
```

Verifica con: `crontab -l`

## 🔔 Alternativa: launchd (macOS nativo)

Si prefieres launchd sobre cron:

```xml
<!-- ~/Library/LaunchAgents/com.trading.morning.plist -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.trading.morning</string>
    <key>ProgramArguments</key>
    <array>
        <string>~/Documents/wally-trader/.claude/scripts/daily_cron.sh</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>5</integer>
        <key>Minute</key>
        <integer>30</integer>
        <key>Weekday</key>
        <integer>1</integer>
    </dict>
</dict>
</plist>
```

Cargar con: `launchctl load ~/Library/LaunchAgents/com.trading.morning.plist`

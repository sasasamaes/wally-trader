---
name: neptune-alert-placeholders
description: Use cuando necesites configurar alertas con webhooks/JSON desde los indicadores Neptune Oscillator™ o Neptune Signals™ — incluye TODOS los placeholders disponibles (TradingView nativo + custom Neptune) y ejemplos de JSON listos para 3Commas/Cornix/webhooks personalizados. Útil para automatizar pipelines con bots externos o para integrar con el watcher del proyecto.
---

# Neptune Alert Placeholders — guía completa de webhooks

## Placeholders nativos TradingView (todos los indicadores)

```
{{ticker}}     → BTCUSDT.P, EURUSD, etc.
{{exchange}}   → BINANCE, OANDA, BITUNIX, etc.
{{interval}}   → 15, 1H, 1D
{{close}}      → precio cierre vela
{{open}}       → precio apertura vela
{{high}}       → máximo vela
{{low}}        → mínimo vela
{{volume}}     → volumen vela
{{time}}       → tiempo vela
{{timenow}}    → fecha/hora alerta disparada
```

## Placeholders custom Neptune Oscillator™

### Señales

```
{{oscillator_signal}}       → "bullish" | "bearish" | "none"
{{confirmation_signal}}     → "bullish" | "bearish" (señal AI/ML confirmada)
{{signal_1_bounce}}         → señal Bounce
{{signal_2_confluence}}     → señal Confluencias
{{signal_3_cross}}          → señal Cross
```

### Valores numéricos (líneas)

```
{{neptune_line}}            → línea principal (Trigger)
{{neptune_signal_line}}     → línea señal (Q1)
{{neptune_tp1}}             → take profit 1 sugerido
{{neptune_sl}}              → stop loss sugerido
{{wt2_value}}               → WaveTrend 2 actual
{{rvol_value}}              → volumen relativo
```

### Contexto de mercado

```
{{is_momentum}}             → "true" | "false"
{{divergence}}              → "bullish" | "bearish" | "none"
{{trend_direction}}         → "up" | "down" (basado en EMA50)
{{session_active}}          → "true" | "false" (sesión alto volumen)
```

## Placeholders custom Neptune Signals™

### Niveles de precio (más completos que Oscillator)

```
{{neptune_tp1}}             → TP1 sugerido
{{neptune_tp2}}             → TP2 sugerido
{{neptune_sl1}}             → SL1 (principal)
{{neptune_sl2}}             → SL2 (más holgado)
{{rev_band_upper}}          → banda reversión superior
{{rev_band_lower}}          → banda reversión inferior
{{neptune_line}}            → media móvil base
{{neptune_trail}}           → línea principal del Trail
{{neptune_trail_zone}}      → zona secundaria del Trail
{{mtf_neptune_trail}}       → Trail en TF superior
{{wavetrend_1}}             → WT1 actual
{{wavetrend_2}}             → WT2 actual
```

### Métricas de mercado

```
{{trend_direction}}         → "Uptrend" | "Downtrend" | "Neutral"
{{market_regime}}           → "Trending" | "Ranging" | "Neutral"
{{session_active}}          → "New York" | "London" | "Tokyo" | "Sydney" | "None"
{{volume_sentiment}}        → "85.5%" | "N/A"
{{squeeze_metric}}          → "40.2%" | "N/A"
{{optimal_sensitivity}}     → "5 (Auto)" cuando Neptune Pilot activo
```

### Flags booleanos (filtros para webhooks)

```
{{is_momentum}}             → "true" | "false"
{{oscillator_signal}}       → "true" | "false" (adapta a Bull/Bear)
{{confirmation_signal}}     → "true" | "false" (confirmada por ML)
{{ml_exit_bull}}            → "true" | "false" (ML sugiere cerrar Bull)
{{ml_exit_bear}}            → "true" | "false"
{{neptune_touch_bull}}      → "true" | "false" (precio toca Trail desde arriba)
{{neptune_touch_bear}}      → "true" | "false"
{{neptune_flip_bull}}       → "true" | "false" (Trail flip bear→bull)
{{neptune_flip_bear}}       → "true" | "false"
```

## Templates JSON listos para webhooks

### Template universal Bull/Bear (recomendado)

```json
{
  "action": "BUY",
  "symbol": "{{ticker}}",
  "exchange": "{{exchange}}",
  "timeframe": "{{interval}}",
  "entry_price": "{{close}}",
  "take_profit_1": "{{neptune_tp1}}",
  "take_profit_2": "{{neptune_tp2}}",
  "stop_loss": "{{neptune_sl1}}",
  "market_context": {
    "trend": "{{trend_direction}}",
    "regime": "{{market_regime}}",
    "session": "{{session_active}}",
    "vol_sentiment": "{{volume_sentiment}}"
  },
  "signal_flags": {
    "is_momentum": {{is_momentum}},
    "ai_confirmed": {{confirmation_signal}}
  },
  "sensitivity": "{{optimal_sensitivity}}"
}
```

Para Bearish: cambiar `"action": "SELL"`.

### Template minimal Oscillator (compacto)

```json
{
  "action": "long",
  "ticker": "{{ticker}}",
  "price": {{close}},
  "oscillator_signal": "{{oscillator_signal}}",
  "confirmation_signal": "{{confirmation_signal}}",
  "momentum": "{{is_momentum}}",
  "trail_tp1": {{neptune_tp1}},
  "neptune_line": {{neptune_line}},
  "session": "{{session_active}}"
}
```

### Template para 3Commas (formato específico)

```json
{
  "message_type": "bot",
  "bot_id": YOUR_BOT_ID,
  "email_token": "YOUR_EMAIL_TOKEN",
  "delay_seconds": 0,
  "pair": "{{ticker}}"
}
```

(Para 3Commas, los placeholders TP/SL no aplican — el bot 3Commas tiene sus propios settings.)

## Cómo activar las alertas con placeholders

### Neptune Oscillator (modo BOT):

```
1. Settings → tab "Inputs" → scroll a "ALERTS SCRIPTING"
2. Habilitar "Enable Dynamic Bot Alerts (alert() function)" ✅
3. Pegar template JSON en:
   - "Bullish Alert Message"
   - "Bearish Alert Message"
4. Cancel → Ok para guardar
5. Crear alerta en TradingView:
   - Right-click chart → Add alert
   - Condition: "Neptune Oscillator" → "Any alert() function call"
   - Notifications: Webhook URL + tu endpoint
   - El JSON se enviará automáticamente con los placeholders reemplazados
```

### Neptune Signals (similar):

```
1. Settings → buscar sección de alertas
2. Pegar templates Bull/Bear JSON
3. Crear alerta TV con condición "alert() function call"
4. Webhook URL → tu endpoint
```

## Integración con el watcher del proyecto

El sistema Wally Trader tiene un watcher (`.claude/scripts/watcher_tick.py`) que monitorea pending orders. Para recibir señales Neptune como pending orders:

**Pipeline propuesto** (no implementado todavía):
```
TradingView Neptune alert
   ↓ webhook
Servidor HTTP (FastAPI/Cloudflare Worker)
   ↓ valida JSON
Ejecuta /signal con los datos parseados
   ↓ approve/reject según validation score
Si APPROVE → /order encola pending
   ↓ watcher monitoreará
Notificación macOS cuando llegue al entry price
   ↓
Tú ejecutas manual en exchange
```

Esto requiere implementar un endpoint webhook + parser. Por ahora el flujo es manual: ves la alerta → ejecutas `/signal` con los datos manualmente.

## Reglas de uso

1. **Para profile bitunix** (copy trading punkchainer's): el sistema valida cada señal manualmente con `/signal`. NO usar webhooks automáticos para que el sistema decida — siempre filtrar primero.
2. **Para profile retail**: webhooks pueden ser útiles si automatizas notificaciones, NO ejecución.
3. **Sensitivity Manual** en Signals afecta los placeholders `{{optimal_sensitivity}}` — siempre verifica que la sensitivity reportada sea la esperada.
4. **JSON válido:** asegúrate de envolver placeholders de tipo string entre comillas `"{{ticker}}"`. Numéricos (close, neptune_tp1) sin comillas.

## Referencias

- `Neptune_Oscillator_Scripting_Guide.pdf` — guía oficial Oscillator
- `Manual_Placeholders.pdf` — guía oficial Signals
- `system/skills/neptune-community-config/SKILL.md` — configs validadas comunidad
- `system/skills/neptune-indicators/SKILL.md` — uso conceptual de los indicadores

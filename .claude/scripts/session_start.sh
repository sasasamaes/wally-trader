#!/bin/bash
# Hook SessionStart: carga contexto de trading al iniciar Claude en este proyecto
# Output format: JSON con hookSpecificOutput.additionalContext para inyectar al modelo

HORA_MX=$(TZ='America/Mexico_City' date +%H)
HORA_MX=${HORA_MX#0}
HORA_STR=$(TZ='America/Mexico_City' date +%H:%M)

# Determinar saludo según hora
if [ "$HORA_MX" -ge 5 ] 2>/dev/null && [ "$HORA_MX" -le 9 ] 2>/dev/null; then
    SALUDO="Buenos días — ventana de trading activa"
elif [ "$HORA_MX" -ge 10 ] 2>/dev/null && [ "$HORA_MX" -le 16 ] 2>/dev/null; then
    SALUDO="Sesión en curso"
elif [ "$HORA_MX" -ge 17 ] 2>/dev/null && [ "$HORA_MX" -le 20 ] 2>/dev/null; then
    SALUDO="Cierre de sesión — hora de journal"
else
    SALUDO="Fuera de ventana — planeando o revisando"
fi

# Leer capital actual de memoria
MEMORY_DIR="$HOME/.claude/projects/<project-path-encoded>/memory"
TRADING_LOG="$MEMORY_DIR/trading_log.md"
CAP="13.63"
if [ -f "$TRADING_LOG" ]; then
    FOUND=$(grep -oE 'Capital (actual|running|final)[: ]+\$[0-9]+\.[0-9]+' "$TRADING_LOG" 2>/dev/null | tail -1 | grep -oE '[0-9]+\.[0-9]+')
    [ -n "$FOUND" ] && CAP="$FOUND"
fi

# Construir contexto como JSON
CONTEXT=$(cat <<EOF
# CONTEXTO TRADING SESSION

**Hora MX:** $HORA_STR — $SALUDO
**Capital actual:** \$$CAP
**Símbolo:** BTCUSDT.P (BingX)
**Estrategia activa:** Mean Reversion 15m (según régimen)

## Comandos rápidos disponibles
- /morning — análisis matutino completo (17 fases)
- /validate — validar entry actual (4 filtros)
- /regime — detectar régimen mercado
- /risk — calcular position sizing 2%
- /status — estado completo sistema
- /chart — redibujar niveles en TV
- /journal — cerrar día / log trade
- /review — review semanal
- /levels — niveles técnicos ahora
- /alert — configurar alerta custom
- /backtest — probar estrategia

## Reglas sagradas
1. Max 2% riesgo por trade
2. Max 3 trades/día
3. 2 SLs → STOP día
4. Nunca mover SL en contra
5. Nunca leverage >10x
6. 4/4 filtros obligatorios

## Agentes disponibles (auto-invocación)
morning-analyst, trade-validator, regime-detector, chart-drafter, risk-manager, journal-keeper, backtest-runner
EOF
)

# Output JSON con additionalContext para inyectar en el modelo
jq -n \
    --arg ctx "$CONTEXT" \
    '{
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": $ctx
        }
    }'

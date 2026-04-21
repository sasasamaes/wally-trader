# 📈 BTC Trading System — Scalping Intraday con Claude

Sistema completo de trading algorítmico-asistido para BTCUSDT.P en BingX, construido sobre TradingView + Claude Code + Pine Script.

**Status actual:** Sistema validado con primer trade ganador (+11.4% / $10 → $11.14).
**Objetivo:** Escalar cuenta de $10 → $100 → FTMO $10k fundeado en ~4-6 meses.

---

## 🎯 Qué es este proyecto

Un **sistema operativo de trading** que combina:

- **Estrategia validada por backtest** (Mean Reversion + Donchian Breakout según régimen)
- **Indicador Pine Script** con los 4 filtros de entrada automatizados
- **Protocolo matutino** de 17 fases (análisis + psicología + disciplina)
- **Memoria persistente en Claude** que recuerda tu perfil, reglas y progreso
- **Journal obligatorio** de cada trade + review semanal
- **Integración con TradingView** via MCP (Claude dibuja niveles, detecta señales)

No es un bot automatizado. Es una **disciplina acompañada** — Claude hace el análisis pesado, tú ejecutas con reglas.

---

## 📁 Estructura del proyecto

```
trading/
├── CLAUDE.md                      # Guía del proyecto (la que Claude lee al iniciar)
├── MORNING_PROMPT.md              # Protocolo matutino de 17 fases
├── MEAN_REVERSION_INDICATOR.pine  # Indicador Pine Script (4 filtros + alertas)
├── DAILY_TRADING_JOURNAL.md       # Template journal diario
├── BREAKOUT_DASHBOARD_TRACKER.md  # Dashboard de niveles Donchian
├── NEPTUNE_TRADING_SYSTEM.md      # Docs sistema Neptune (legacy, referencia)
├── DOCUMENTATION.md               # Documentación general del sistema
├── QUICK_START_GUIDE.md           # Guía rápida de arranque
├── RISK_CALCULATOR.md             # Fórmulas de position sizing
├── .gitignore                     # Excluye /tmp, screenshots, node_modules
└── README.md                      # Este archivo

# Repos externos (no incluidos en este repo):
├── tradingview-mcp/               # MCP server de TradingView (submódulo externo)
└── claude-tradingview-mcp-trading/  # Bot adicional (submódulo externo)

# Memoria persistente (fuera del repo, en ~/.claude/):
~/.claude/projects/<project-path-encoded>/memory/
├── MEMORY.md                      # Índice de memorias
├── user_profile.md                # Perfil del trader
├── trading_strategy.md            # Config de estrategia activa
├── market_regime.md               # Cómo detectar régimen de mercado
├── trading_log.md                 # Historial de trades
├── morning_protocol.md            # Protocolo de 17 fases (versión memoria)
├── entry_rules.md                 # Filtros de entrada + lecciones
├── backtest_findings.md           # Resultados de backtests
├── tradingview_setup.md           # Setup de TV + workarounds
├── market_context_refs.md         # APIs públicas útiles
├── communication_prefs.md         # Preferencias de comunicación
└── user_goals_reality.md          # Expectativas vs realidad
```

---

## 🏆 Estrategia actual: Mean Reversion en Range

**Validada con 100% WR en primer trade** (2026-04-20, +$1.14 sobre $10 cap).

### Parámetros

| Parámetro | Valor |
|---|---|
| Timeframe | 15m |
| Donchian length | 15 velas |
| Bollinger Bands | (20, 2) |
| RSI | 14 (OB 65 / OS 35) |
| ATR | 14 |
| Stop Loss | 1.5 × ATR |
| TP1 (40%) | 2.5 × SL |
| TP2 (40%) | 4.0 × SL |
| TP3 (20%) | 6.0 × SL |
| Leverage | 10x |
| Position sizing | 2% risk del capital |
| Ventana entradas | MX 06:00 – 12:00 |
| Cierre forzado | MX 17:00 |
| Max trades/día | 3 |
| Stop sesión | 2 SLs → para |

### 4 filtros obligatorios (todos deben cumplirse)

**LONG:**
1. Precio toca o cruza Donchian Low (dentro 0.1%)
2. RSI(14) < 35
3. Low de vela toca Bollinger Band inferior
4. Vela cierra verde (close > open)

**SHORT:** mirror (Donchian High, RSI > 65, BB superior, vela roja)

### Estrategia secundaria (si regime cambia)

**Donchian Breakout** cuando close 4H rompe el rango macro (ahora 73,500-78,300) con volumen >2x promedio. Config documentada en `CLAUDE.md`.

---

## 🌅 Uso diario

### 1. Preparación nocturna (el día anterior)
- Review del día
- Actualizar `DAILY_TRADING_JOURNAL.md`
- Dormir 7+ horas

### 2. Mañana 5:30 AM MX
Abre Claude Code en este directorio:
```bash
cd ~/Documents/trading
claude
```

### 3. Pega el prompt matutino
Copia el bloque `PROMPT PRINCIPAL` de `MORNING_PROMPT.md`, pégalo en Claude.

Claude ejecuta 17 fases en ~5-8 minutos:
- Auto-check personal
- Sentiment global (F&G, funding, on-chain)
- Correlaciones (ETH, SPX, DXY)
- Noticias/eventos próximas 6h
- Detección de régimen (range/trend/volatile)
- Selección de estrategia
- Niveles técnicos multi-TF
- Money flow + patrones
- Position sizing con tu capital
- Dibujo en TradingView
- Plan de entrada exacto
- Checklist pre-entry
- Reglas duras
- **VEREDICTO:** ENTRAR LONG / ENTRAR SHORT / ESPERAR / NO OPERAR

### 4. Ejecución disciplinada
- Imprime el checklist pre-entry (sección en `MORNING_PROMPT.md`)
- Tacha cada ítem antes de apretar COMPRAR/VENDER
- Si no puedes tachar los 15 → **no entres**

### 5. Cierre de sesión MX 17:00
```
"Cierre sesión. Resumen PnL + actualiza trading_log.md"
```

### 6. Review semanal (domingos)
```
"Review semana: métricas, patrones, 1 cambio para la próxima"
```

---

## 🔧 Setup inicial

### Requisitos

- **TradingView Desktop** (plan Basic mínimo)
- **BingX Futures** con BTCUSDT.P activado
- **Claude Code** (Anthropic CLI)
- **TradingView MCP** instalado y conectado (ver `tradingview-mcp/`)
- **Python 3.11+** (para backtests locales)

### Instalación

```bash
# 1. Clonar este repo
git clone git@github.com:sasasamaes/trading.git
cd trading

# 2. Abrir TradingView Desktop con CDP en puerto 9222
#    (ver tradingview-mcp/README.md)

# 3. Abrir Claude Code en este directorio
claude

# 4. Instalar indicador Pine en TV (manual):
#    - Abrir Pine Editor en TV
#    - Copiar contenido de MEAN_REVERSION_INDICATOR.pine
#    - Pegar, guardar como "MR Signals"
#    - Añadir al chart
```

### Memoria persistente

Claude mantendrá memoria de tu perfil en `~/.claude/projects/.../memory/`.
**Importante:** esa carpeta NO está en este repo (excluida por `.gitignore`).
Si cambias de máquina, deberás regenerar la memoria o copiarla manualmente.

---

## 📊 Progreso y objetivos

### Ruta planificada

| Meta | Capital | Días estimados | Estado |
|---|---|---|---|
| Primer trade ganador | $10 → $11.14 | 1 | ✅ **Completado** |
| Acumular 25 trades estadísticos | → $15-20 | ~15-20 | 🔄 En progreso |
| WR validado ≥ 60% sobre 25+ trades | — | ~20 | ⏳ Pendiente |
| $20 por trade | $161 cap | ~26 | ⏳ Pendiente |
| $50/día promedio | $325 cap | ~70 | ⏳ Pendiente |
| **$100/día promedio** | **$650 cap** | **~85** | ⏳ Pendiente |
| FTMO $10k fundeado | — | ~60 post-validación | ⏳ Pendiente |

### Métricas objetivo mínimo (después de 25 trades)

- Win Rate ≥ 60%
- Profit Factor ≥ 1.8
- Max Drawdown ≤ 15%
- Days operated ≥ 15

---

## 🧠 Principios del sistema

### 1. Régimen dicta estrategia
Una estrategia no es universal. **Mean Reversion** funciona en RANGE. **Donchian Breakout** funciona en TRENDING. Cada día detectar el régimen antes de elegir.

### 2. 4 filtros obligatorios
Nunca entrar con 3/4 filtros. La disciplina es el edge.

### 3. Position sizing 2% fijo
Nunca arriesgar más del 2% del capital por trade. Matemáticamente imposible quebrar con 60%+ WR.

### 4. Stop de sesión duro
2 SLs consecutivos → para el día. No hay "recuperación".

### 5. Journal obligatorio
Cada trade se documenta. Sin journal no hay mejora.

### 6. Disciplina > Estrategia
El 90% de retail pierde por emocional, no por análisis. Tu mayor enemigo eres tú.

---

## 📚 Archivos clave y para qué sirven

### `CLAUDE.md`
Guía principal que Claude lee al iniciar sesión. Contiene perfil del trader, estrategia activa, reglas, niveles técnicos vigentes, APIs útiles.

### `MORNING_PROMPT.md` ⭐
**El archivo más importante.** Contiene:
- Prompt completo de 17 fases para copy-paste cada mañana
- Checklist físico imprimible
- Templates de journal diario y review semanal
- Quick commands
- Mantras del día

### `MEAN_REVERSION_INDICATOR.pine`
Código Pine Script del indicador con los 4 filtros automatizados. Se pega en TradingView → Pine Editor.

Incluye:
- Donchian(15) channel
- Bollinger Bands(20, 2)
- RSI(14) OB/OS
- ATR(14) para SL/TP dinámicos
- Flechas LONG/SHORT cuando 4/4 filtros alinean
- Tabla top-right con status de filtros en tiempo real
- Alertas configurables

### `DAILY_TRADING_JOURNAL.md`
Template para registrar cada trade con todos sus datos. Obligatorio.

### `RISK_CALCULATOR.md`
Fórmulas de position sizing, cálculo de SL/TP basado en capital.

---

## 🔄 Workflow con Git

### Commit diario del journal
```bash
git add DAILY_TRADING_JOURNAL.md
git commit -m "journal: 2026-04-21 +$1.20 (+12.4%)"
git push
```

### Commit de cambios de estrategia
```bash
git add CLAUDE.md MORNING_PROMPT.md
git commit -m "strategy: ajustar filtro RSI tras review semanal"
git push
```

### Commit de nuevos backtest findings
```bash
# Los backtests corren en /tmp/ y NO se commitean.
# Solo los hallazgos se documentan en memoria de Claude
# o en markdowns específicos si son relevantes.
```

---

## ⚠️ Disclaimers importantes

1. **Esto NO es consejo financiero.** Todo lo aquí descrito es para fines educativos y de investigación personal.

2. **Futuros con leverage pueden liquidar capital en minutos.** Usa solo capital que puedas perder sin afectar tu vida.

3. **Win Rate histórico ≠ Win Rate futuro.** Los backtests tienen data limitada (3-50 días según TF). Validación real requiere 25+ trades live.

4. **El sistema depende de disciplina.** Saltarte filtros o mover SLs convierte un sistema ganador en perdedor.

5. **El mercado cambia.** Si regime shift no detectado → recalibrar estrategia. Revisa régimen semanalmente.

---

## 🛠️ Troubleshooting

### Claude no recuerda mi capital/progreso
- Verifica que exista `~/.claude/projects/<project-path-encoded>/memory/`
- Lee `MEMORY.md` — debe listar todas las memorias activas
- Si falta, pide a Claude: "lee mi memoria y cárgala"

### El indicador Pine no aparece en TradingView
- TV Basic limita a 2 indicadores por chart
- Quita uno (Neptune Signals o Oscillator) primero
- Luego añade MR Signals

### draw_clear falla con "getChartApi is not defined"
- Workaround: click derecho en trash icon del left sidebar
- Menú contextual → "Eliminar dibujos"
- Documentado en `~/.claude/.../tradingview_setup.md`

### Pine Editor hang/loading infinito
- Cierra el panel y reabre
- Si persiste, guarda el código localmente (ya está en `MEAN_REVERSION_INDICATOR.pine`) y pega manual

---

## 🤝 Colaboración

Este repo es **personal** pero si quieres proponer mejoras:

1. Fork el repo
2. Crea una branch (`git checkout -b feature/mi-mejora`)
3. Commit (`git commit -m 'Propuesta: ...'`)
4. Push (`git push origin feature/mi-mejora`)
5. Abre un Pull Request

Idealmente acompaña con:
- Backtest evidencia (>20 trades mínimo)
- Justificación del cambio
- Comparación vs estrategia actual

---

## 📜 Licencia

Proyecto personal sin licencia pública. Si quieres usar partes del código, cita la fuente.

---

## 🙏 Créditos

- **Estrategia Mean Reversion / Donchian Breakout:** construida iterativamente vía backtests
- **Indicadores Pine Script:** escritos en Pine v6
- **TradingView MCP:** [tradingview-mcp](https://github.com/anthropics/claude-code/tree/main/examples/tradingview) (o equivalente)
- **Claude Code:** [Anthropic](https://claude.com/claude-code)

---

## 💎 Mantra del sistema

> **"El mejor trade del año es el que NO hiciste por falta de setup."**
>
> **"Un SL pequeño respetado es una victoria. Un SL movido es el principio del fin."**
>
> **"Tu cuenta crece por lo que NO haces, tanto como por lo que haces."**

---

**Última actualización:** 2026-04-21
**Capital actual:** $11.14
**Próximo objetivo:** $20 (≈ +80%) en las próximas 2 semanas

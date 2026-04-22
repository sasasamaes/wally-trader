# DAILY TRADING JOURNAL — BTCUSDT.P (BingX)

Capital inicial histórico: $10.00
Estrategia activa: Mean Reversion 15m / 10x (régimen RANGE)
Ventana operativa oficial: MX 06:00 – 23:59 (force exit 23:59 — "no dormir con trade abierto")

> Nota 2026-04-21 (cierre de día): ventana extendida de 18:00 → 23:59 MX por decisión del trader (cripto es 24/7, la única restricción real es no ir a dormir con posición abierta). La evaluación de disciplina del Trade #2 del 2026-04-21 abajo refleja la regla vigente ese día (force exit 18:00).

---

## SESIÓN 2026-04-21 (martes)

### Estado capital
- Capital pre-sesión: $11.14
- Capital post-sesión: ~$12.23
- Delta día: +$1.09 (+9.8% sobre capital pre-sesión)
- Delta acumulado desde inicio: +$2.23 (+22.3% sobre $10 inicial en 2 trades)

### Trades ejecutados
**Trade único del día — LONG BTCUSDT.P**
- Orden: #992142455942 (Taker, reduce-only cierre)
- Entry: NO REGISTRADO en tiempo real (falta de logging)
- Exit: $76,312.7 @ MX 18:43:33
- Notional: 76.4 USDT
- Leverage asumido: 10x (margen ~$7.6)
- Comisión: 0.03815635 USDT
- PnL neto: **+1.0946 USDT (+1.43% notional)**
- Movimiento favorable estimado en precio: ~0.14%
- Resultado: **WIN**

### Métricas del día
- Trades: 1
- Win Rate día: 1/1 (100%)
- Mejor trade: +$1.09
- Peor trade: N/A
- Comisiones pagadas: $0.038

### Disciplina / Cumplimiento de reglas

| Regla | Cumplida |
|---|---|
| Operar en régimen correcto (RANGE) | SI (asumido) |
| 4 filtros Mean Reversion documentados | NO (no registrados en tiempo real) |
| Entry dentro ventana 06:00-18:00 MX | DESCONOCIDO |
| **Exit ≤ 18:00 MX (force exit)** | **NO — cerrado 18:43:33 (+43 min fuera de regla)** |
| Max 5 trades/día | SI (1 trade) |
| Stop tras 2 SLs | N/A (sin SLs) |
| No mover SL en contra | N/A |

**Puntaje disciplina día: 2/4 reglas auditables → 50%**

### Patrones detectados (acumulado 2 trades)
Positivos:
- **Racha 2-0 (WR 100% temprana)** — muestra aún pequeña pero consistente
- **No over-trading** — 1 trade por día ambos días, sin "forzar" setups
- **Disciplina en el outcome (deja correr hasta objetivo)** — ni panic-close, ni FOMO

Negativos / a vigilar:
- **Falta de logging en tiempo real**: trade #2 no tiene entry ni hora de apertura registrados. Sin esto, no se pueden validar filtros ni construir base estadística real.
- **Violación del force exit de 18:00 MX** en trade #2 → primer incumplimiento de regla. El hecho de que ganó es lo que lo hace peligroso (refuerzo positivo de mala conducta).

### Evaluación honest-first

El +22.3% en 2 trades se ve espectacular pero son datos de ejemplo, NO evidencia estadística. WR 100% con n=2 no significa nada. Lo que SÍ importa de estos 2 días:

1. Ejecutó la estrategia (no se quedó en parálisis análisis)
2. No perdió capital — primer objetivo de cualquier trader
3. YA empezó a aparecer indisciplina menor (violación force exit). Si no se corrige ahora que el trade ganó, se convertirá en hábito cuando pierda.

### Lección del día
"Ganar violando una regla es más caro que perder respetándola. El refuerzo positivo del outcome crea el hábito que un día costará más de lo que hoy ganaste."

### Estado mental
No reportado explícitamente por el usuario — pedir en próxima sesión.

### Progreso hacia target $100
- Capital actual: $12.23
- Target: $100
- Falta: $87.77 (+717% adicional)
- A ritmo de +5% compuesto diario necesitaría ~43 días hábiles consecutivos
- A ritmo observado (2 trades en 2 días, +22%) NO es extrapolable — muestra insuficiente

### Mañana (2026-04-22)
**1 cosa específica a hacer diferente:**

> **LOGGEAR EL TRADE EN EL MOMENTO DE ABRIR LA POSICIÓN.** Antes de pulsar "Abrir" en BingX, escribir en el journal: hora MX, precio entry, los 4 filtros cumplidos uno por uno (Donchian tocado, RSI<35/>65, BB tocada, vela cerrada), SL en $X, TPs planeados en $X/$X/$X. Sin este registro NO se puede mejorar. El journal post-hoc es ficción — el real es el que se escribe antes del fill.

**Regla reforzada (actualizada al cierre 2026-04-21):**
- Nueva ventana operativa: MX 06:00 – 23:59. Si a las 23:30 MX el trade sigue abierto: alarma audible. A 23:59 MX cerrar mercado SIN EXCEPCIÓN (no dormir con posición abierta — con leverage 10x un wick de madrugada puede liquidar mientras el trader no puede reaccionar).

---

## HISTORIAL DE SESIONES

### 2026-04-20 (lunes) — PRIMER WIN
- Trades: 1 | WR: 1/1 | PnL: +$1.14 (+11.4%) | Capital: $10.00 → $11.14
- Setup: Mean Reversion LONG, Donchian Low(15), TP2 hit a 75,729
- Disciplina: entró antes de cerrar vela verde (filtro #4 incumplido), pero cerró disciplinado

### 2026-04-21 (martes) — SEGUNDO WIN CON VIOLACIÓN
- Trades: 1 | WR: 1/1 | PnL: +$1.09 (+9.8% sobre capital) | Capital: $11.14 → $12.23
- Setup: LONG cerrado en 76,312.7
- Disciplina: **force exit 18:00 MX violado (cerrado 18:43:33)**

---

## MÉTRICAS ACUMULADAS (n=2 trades)

```
Total trades:          2
Winners / Losers:      2 / 0
Win Rate:              100% (muestra insuficiente)
PnL neto acumulado:    +$2.23
Retorno sobre inicial: +22.3%
Max DD:                0%
Días operando:         2 consecutivos
Violaciones de regla:  1 (filtro #4 día 1, force exit día 2 = 2 en 2 días)
```

**NOTA:** 2 violaciones en 2 trades = 100% tasa de violación. La WR 100% enmascara este dato. Si el patrón continúa, la estrategia no está siendo testeada en su forma pura — se está testeando una versión degradada.

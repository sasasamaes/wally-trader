# DAILY TRADING JOURNAL — BTCUSDT.P (BingX)

Capital inicial histórico: $10.00
Estrategia activa: Mean Reversion 15m / 10x (régimen RANGE)
Ventana operativa oficial: CR 06:00 – 23:59 (force exit 23:59 — "no dormir con trade abierto")

> Nota 2026-04-21 (cierre de día): ventana extendida de 18:00 → 23:59 CR por decisión del trader (cripto es 24/7, la única restricción real es no ir a dormir con posición abierta). La evaluación de disciplina del Trade #2 del 2026-04-21 abajo refleja la regla vigente ese día (force exit 18:00).

---

## SESIÓN 2026-04-22 (miércoles) — TERCER WIN

### Estado capital (confirmado por screenshot exchange)
- Capital pre-sesión: $11.82 (implícito por +15.32% del día)
- Capital post-sesión: **$13.63**
- PnL realizado del día: **+$1.81 (+15.32%)**
- Delta acumulado desde inicio: +$3.63 (+36.3% sobre $10 inicial en 3 trades)
- ⚠ Gap de -$0.41 entre cierre 2026-04-21 ($12.23) y baseline de hoy ($11.82) — posible funding fee / withdraw / ajuste no documentado. Confirmar con usuario.

### Trades ejecutados
- **Trade único del día (3º WIN consecutivo)** — detalles de entry/exit/setup NO registrados en tiempo real. PnL +$1.81 confirmado vía exchange.
- **PATRÓN REPETIDO**: 2º día seguido sin logging completo en el momento de ejecución.

### Disciplina
- WIN sí, pero **auditabilidad = 0**. No se puede verificar si fue setup válido 4/4 filtros o suerte.
- Próxima sesión: exigir logging PRE-FILL antes de cualquier otra cosa.

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
- Exit: $76,312.7 @ CR 18:43:33
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
| Entry dentro ventana 06:00-18:00 CR | DESCONOCIDO |
| **Exit ≤ 18:00 CR (force exit)** | **NO — cerrado 18:43:33 (+43 min fuera de regla)** |
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
- **Violación del force exit de 18:00 CR** en trade #2 → primer incumplimiento de regla. El hecho de que ganó es lo que lo hace peligroso (refuerzo positivo de mala conducta).

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
- Capital actual: $13.63
- Target: $100
- Falta: $86.37 (+634% adicional)
- A ritmo de +5% compuesto diario necesitaría ~41 días hábiles consecutivos
- A ritmo observado (3 trades en 3 días, +36.3%) NO es extrapolable — muestra insuficiente

### Mañana (2026-04-22)
**1 cosa específica a hacer diferente:**

> **LOGGEAR EL TRADE EN EL MOMENTO DE ABRIR LA POSICIÓN.** Antes de pulsar "Abrir" en BingX, escribir en el journal: hora CR, precio entry, los 4 filtros cumplidos uno por uno (Donchian tocado, RSI<35/>65, BB tocada, vela cerrada), SL en $X, TPs planeados en $X/$X/$X. Sin este registro NO se puede mejorar. El journal post-hoc es ficción — el real es el que se escribe antes del fill.

**Regla reforzada (actualizada al cierre 2026-04-21):**
- Nueva ventana operativa: CR 06:00 – 23:59. Si a las 23:30 CR el trade sigue abierto: alarma audible. A 23:59 CR cerrar mercado SIN EXCEPCIÓN (no dormir con posición abierta — con leverage 10x un wick de madrugada puede liquidar mientras el trader no puede reaccionar).

---

## HISTORIAL DE SESIONES

### 2026-04-20 (lunes) — PRIMER WIN
- Trades: 1 | WR: 1/1 | PnL: +$1.14 (+11.4%) | Capital: $10.00 → $11.14
- Setup: Mean Reversion LONG, Donchian Low(15), TP2 hit a 75,729
- Disciplina: entró antes de cerrar vela verde (filtro #4 incumplido), pero cerró disciplinado

### 2026-04-21 (martes) — SEGUNDO WIN CON VIOLACIÓN
- Trades: 1 | WR: 1/1 | PnL: +$1.09 (+9.8% sobre capital) | Capital: $11.14 → $12.23
- Setup: LONG cerrado en 76,312.7
- Disciplina: **force exit 18:00 CR violado (cerrado 18:43:33)**

### 2026-04-22 (miércoles) — TERCER WIN (mejor día % hasta la fecha)
- Trades: 1 | WR: 1/1 | PnL: +$1.81 (+15.32%) | Capital: $11.82 → $13.63
- Setup: DESCONOCIDO (sin registro en tiempo real) — PATRÓN REPETIDO del día anterior
- Gap sin documentar: $12.23 → $11.82 (-$0.41) pre-sesión

---

## MÉTRICAS ACUMULADAS (n=3 trades)

```
Total trades:          3
Winners / Losers:      3 / 0
Win Rate:              100% (muestra insuficiente)
PnL neto acumulado:    +$3.63
Retorno sobre inicial: +36.3%
Max DD:                0% (excluyendo gap -$0.41 no documentado)
Días operando:         3 consecutivos
Violaciones de regla:  filtro #4 día 1, force exit día 2, zero-logging días 2 y 3
```

**NOTA:** 3 WINs en 3 días con 2 días seguidos sin logging completo. El outcome sigue disfrazando el problema estructural: **si no se registra, no existe evidencia estadística** — solo anécdotas.

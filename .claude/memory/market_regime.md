---
name: Market regime detection — clave para escoger estrategia
description: Cómo identificar si BTC está en range o trending, y qué estrategia usar en cada caso
type: project
originSessionId: 870cfb36-0066-4b6c-a1b7-eeaebc9a6ca8
---
**Insight crítico descubierto:**

Una estrategia NO es universal. La misma config que gana en trending PIERDE todo en range, y viceversa. Hay que detectar el régimen ANTES de escoger estrategia.

**Evidencia empírica (2026-04):**
- Donchian Breakout 10x en 4H trending (50 días): +87%
- Donchian Breakout 10x en 15m range (3 días): **-26% a 0% WR** (todas trampas)
- Mean Reversion en 15m range: **100% WR, +15%**

**Cómo detectar régimen (al abrir sesión, MX 05:30):**

**RANGE (usar Mean Reversion):**
- BTC se mantiene dentro de una caja de <5% de amplitud por **3+ días**
- Precio rebota entre soporte y resistencia sin romper
- ATR estable (no explota)
- Ejemplo 2026-04: BTC en 73,500-78,300

**TRENDING (usar Donchian Breakout):**
- BTC hace **higher highs + higher lows** diarios (uptrend) o mirror (downtrend)
- Cierra por encima/debajo de range previo con volumen alto
- Ejemplo ideal: BTC rompe 78,300 con vol >2x y cierra 4H arriba

**VOLATILE (NO operar):**
- ATR 2x+ su promedio histórico
- Mechas grandes en ambas direcciones
- News/FOMC/CPI pendiente

**Señal de TRANSICIÓN de régimen:**

De RANGE → TRENDING:
- Cierre 4H fuera del range con vol >2x promedio
- En ese momento **cambiar de Mean Reversion a Breakout** (o no operar ese día)

De TRENDING → RANGE:
- Precio empieza a rebotar cerca del mismo nivel 3+ veces
- ATR contrayéndose
- Se forma consolidación

**Why:** Tradear con la estrategia equivocada para el régimen actual garantiza pérdidas. Donchian breakout en range fue documentado con 0% WR en este mercado.

**How to apply:**
- Antes de operar, hacer check-in de régimen (5 min)
- Ver si close 4H sigue dentro de la caja de referencia
- Si dentro → Mean Reversion
- Si afuera + vol alto → Breakout (pero verificar que no sea fakeout re-entrando al range)
- Si volatile (ATR explota) → sentarse afuera ese día

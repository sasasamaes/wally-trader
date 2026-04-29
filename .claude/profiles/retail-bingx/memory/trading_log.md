---
name: Trading log — histórico de operaciones
description: Registro de trades ejecutados con aprendizajes
type: project
originSessionId: 870cfb36-0066-4b6c-a1b7-eeaebc9a6ca8
---
**Trade #1 — 2026-04-20 (PRIMER WIN)**
- Setup: Mean Reversion LONG en Donchian Low(15)
- Entry: 74,801 (CR ~08:45 aprox)
- Exit: 75,729 (CR ~09:15 aprox)
- Cierre: TOTAL al tocar TP2
- Move: +1.24% / 10x leverage
- **PnL neto: +$1.14 (+11.4%)**
- **Capital: $10 → $11.14**

**Qué funcionó:**
- Identificó correctamente el setup de mean reversion en range
- Exit disciplinado en TP2 cuando sistema lo indicó
- Respetó el SL (no lo movió a evitarlo)

**Qué fue sub-óptimo:**
- Entró ANTES del cierre de vela verde (filtro #4 incumplido)
- Si esperaba a que la vela cerrara verde, entry habría sido mejor (~74,750)
- Cerró en TP2 en vez de dejar runner a TP3 (76,029 = +$0.33 más)

**Potencial máximo del trade:** full TP3 con 40/40/20 scaling = +$1.08 (+10.8%)
**Resultado real:** cierre completo en TP2 = +$1.14 (+11.4%)
**Conclusión:** el "error" de cerrar todo en TP2 funcionó mejor que el plan original. A veces el instinto vale. Pero la disciplina de scaling es robusta a largo plazo.

**Por qué importa:**
Este fue el primer trade ganador con la estrategia Mean Reversion. Valida que:
1. El análisis de régimen (range detection) fue correcto
2. La estrategia mean reversion FUNCIONA en este contexto
3. Los filtros del indicador son efectivos
4. El usuario es capaz de ejecutar con disciplina

**How to apply (para futuras sesiones):**
- Cuando el usuario registre un trade, actualizar este archivo con entry/exit/PnL y lecciones
- Recordarle el historial antes de entrar a trade nuevo (contexto de su progreso)
- Señalar patrones: ¿siempre cierra en TP2? ¿Se salta el filtro #4?
- Calcular capital running: empezó en $10, cada trade modifica el baseline

---

**Trade #2 — 2026-04-21 (SEGUNDO WIN — CON VIOLACIÓN DE REGLA)**
- Exit: 76,312.7 CR 18:43:33 (43 min DESPUÉS del force exit 18:00 vigente ese día)
- PnL: +$1.09 (+9.8%)
- Capital: $11.14 → $12.23
- Sin entry/hora/4 filtros registrados → no auditable

---

**Trade #3 — 2026-04-22 (TERCER WIN — sin documentación)**
- PnL confirmado por screenshot exchange: **+$1.81 (+15.32%)**
- Capital: **$11.82 → $13.63** (gap no documentado de -$0.41 desde cierre 04-21)
- Setup/entry/exit DESCONOCIDOS → 2º día seguido sin logging en tiempo real
- Patrón preocupante: outcome positivo disfraza el problema estructural de journaling cero

**Lección crítica acumulada:**
"3/3 WINs con 2 días sin logging = no hay evidencia estadística, solo anécdotas. La próxima sesión, NO GO hasta que el setup esté escrito pre-fill."

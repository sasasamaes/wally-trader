---
description: Valida una señal externa de comunidad contra tu sistema — GO/NO-GO
allowed-tools: Agent
---

Invoca el agente `signal-validator` para validar una señal externa antes de ejecutarla.

## Formatos aceptados

Ejemplos:
- `/signal Short XLM @ 0.1822`
- `/signal LONG ETH 2850 SL 2800 TP 2950`
- `/signal Sabueso: compra BTC 75000 stop 74800 target 76500`
- `/signal SHORT SOL 180.50` (sin SL/TP, los calcula)

## Qué hace el agente

1. **Parsea** la señal (símbolo, dirección, entry, SL, TP)
2. **Cambia chart** al símbolo de la señal
3. **Aplica tu sistema completo** — régimen, Mean Reversion, ICT, chartismo, Fibonacci, Elliott, indicadores
4. **Score de confluencia** — cuenta factores a favor y en contra (scale -10 a +10)
5. **Decisión clara:**
   - +7 a +10 → GO fuerte (size 1.5×)
   - +4 a +6 → GO moderado (size 1×)
   - +2 a +3 → GO tentativo (size 0.5×)
   - -1 a +1 → ESPERA
   - -2 a -10 → NO-GO
6. **Position sizing** con regla 2% de tu capital actual
7. **Niveles exactos** si decides ejecutar
8. **Dibuja la señal** en TV

## Protección

- Nunca aprueba trades con R:R < 1:1.5
- Nunca recomienda leverage > 10x
- Si el precio ya pasó el entry → marca como "perdiste trade"
- En altcoins pequeñas → advertencia de riesgo extra

## Señal a validar

$ARGUMENTS

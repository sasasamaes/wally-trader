---
name: trade-psychology
description: Use cuando el usuario muestre signos de fatiga mental, revenge trading, FOMO, ansiedad, o después de SLs. Aplica framework de disciplina psicológica basado en trading behavior research. Incluye intervenciones de deescalación y reset mental.
---

# Trade Psychology — Framework de Disciplina Mental

## Cuándo activar este skill

Signos de alerta que requieren intervención:

### 🔴 Alta urgencia (intervención inmediata)
- Usuario menciona "recuperar", "arriesgar más", "todo o nada"
- Pide operar con size mayor tras un SL
- Quiere saltarse los 4 filtros "solo esta vez"
- Expresa frustración sobre un trade cerrado
- Menciona aumentar leverage

### 🟡 Media urgencia (coaching)
- 2+ trades el mismo día (overtrading)
- Mirando chart cada 2 minutos
- Hace preguntas rápidas sucesivas sin actuar
- Dice "creo que va a subir/bajar" sin basis técnico

### 🟢 Baja urgencia (reminder preventivo)
- Inicio de sesión con gap de varios días
- Después de ganancia grande (euforia)
- Al acercarse a un hito (próximo a $50, $100, etc.)

## Framework de intervención

### Paso 1: Validar estado emocional

Antes de dar consejo técnico, reconoce lo que siente:
- "Entiendo que quieres recuperar ese SL rápido..."
- "Es normal sentir ansiedad tras un trade perdedor..."
- "Ganar 2 trades seguidos genera confianza que puede cegar..."

### Paso 2: Mostrar evidencia

Saca data concreta del trading_log.md:
- "Los últimos 5 trades que hiciste post-SL: 4 también fueron SL"
- "Tu WR cuando operas fuera de ventana: 20% (vs 75% dentro)"
- "La última vez que subiste leverage: -45% en 2 días"

### Paso 3: Reglas sagradas reminder

Nunca negociar estas:
1. **Max 2% risk por trade** (fórmula mathematical)
2. **Max 3 trades/día**
3. **2 SLs consecutivos → STOP día**
4. **Nunca mover SL en contra**
5. **Nunca leverage > 10x**
6. **4/4 filtros obligatorios**

### Paso 4: Ofrecer alternativa

En vez de operar ansiosamente, sugerir:
- Caminar 30 minutos
- Leer el journal de trades ganadores para recordar disciplina
- Hacer backtest de una idea en `/backtest`
- Documentar el estado emocional en journal

### Paso 5: Si insiste en saltarse reglas

Respuesta honesta pero firme:
- "Puedes hacerlo, pero voy a documentar esta decisión"
- "Pregunta: ¿este trade es razonable o emocional?"
- "Si estuvieras asesorando a otra persona en tu situación, ¿qué le dirías?"

## Patrones de auto-sabotaje comunes

### Revenge Trading
**Síntoma:** Después de SL, abre otra posición rápido en dirección opuesta.
**Stats:** +85% de los casos termina en 2do SL.
**Intervención:** Regla dura 30 min de pausa post-SL. Durante ese tiempo, escribir en journal.

### FOMO (Fear of Missing Out)
**Síntoma:** "Ya subió mucho pero voy a entrar antes de que suba más."
**Stats:** Compras tops = -70% WR.
**Intervención:** Si precio ya no está en zona de entrada, se perdió el trade. Otro vendrá.

### Overconfidence post-win
**Síntoma:** Después de 3 wins seguidos, aumenta size 2x.
**Stats:** El trade #4 tiene 70% probabilidad de ser el más grande loss del mes.
**Intervención:** Mantener size constante o subir solo 20% tras 5 wins.

### Stop-loss moving
**Síntoma:** "El SL está muy cerca, lo muevo un poquito más."
**Stats:** 95% de SLs movidos en contra terminan peor que el original.
**Intervención:** Cierra plataforma. NO negocies contigo mismo.

### Analysis paralysis
**Síntoma:** Revisa 10 indicadores más, pide 3 opiniones antes de cada entrada.
**Stats:** Las mejores setups son las obvias. Si dudas, skip.
**Intervención:** Si los 4 filtros no están cumplidos, no hay trade. Punto.

## Rituales de reset mental

### Post-SL Ritual (5 min obligatorio)
1. Cerrar plataforma inmediatamente
2. Caminar 2 minutos físicamente alejado del monitor
3. Escribir en journal: "¿Qué filtro fallé? ¿Qué patrón veo?"
4. Beber agua
5. Si todavía estoy alterado, parar el día

### Post-Win Ritual (3 min)
1. Anotar en journal qué hice BIEN
2. Review si seguí el plan o fue suerte
3. NO incrementar size inmediatamente
4. Si es el segundo win del día, considerar parar

### Weekend Reset
1. Revisar journal semanal completo
2. Identificar 1 patrón a mejorar
3. Día sin chart totalmente
4. Volver lunes fresco

## Mantras para momentos difíciles

> "El mejor trade del año es el que NO hice por falta de setup."

> "Un SL pequeño respetado es una victoria."

> "El mercado estará abierto mañana. Mi cuenta no sobrevive el pánico."

> "Yo no pierdo contra el mercado. Pierdo contra mí mismo."

> "Disciplina > Análisis > Suerte."

## Reglas de stop-out emocional

| Estado | Acción |
|---|---|
| 2 SLs seguidos | Stop día |
| 3+ trades hoy | Stop día (overtrading) |
| Dormí < 5h | NO operar |
| Pelea/estrés personal | NO operar |
| Noticia macro próxima | NO operar hasta pasar |
| Cap < 70% inicial | Volver a demo 1 semana |

## Cuando el usuario acepta la intervención

Felicitar explícitamente:
- "Excelente decisión. Los pros dicen 'no' 100x antes de decir 'sí'."
- "Respetar una regla cuando quieres operar es el hábito más valioso."
- "Este 'no operar' vale más que el próximo trade ganador."

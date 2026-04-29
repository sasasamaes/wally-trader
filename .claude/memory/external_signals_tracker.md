---
name: External signals tracker
description: Registro de señales externas validadas (Discord, Telegram, Twitter) con su outcome para análisis de edge de los traders seguidos
type: project
originSessionId: 870cfb36-0066-4b6c-a1b7-eeaebc9a6ca8
---
**Propósito:** llevar registro de señales externas validadas y su resultado final para saber qué traders/fuentes tienen edge real.

## Formato de registro

Cada señal validada se registra así:

```
### Señal #N — YYYY-MM-DD HH:MM
**Fuente:** [nombre del trader/grupo — ej: "El Sabueso de Wall Street"]
**Comunidad:** [punkchainer's Discord, etc.]
**Señal:** [LONG/SHORT] [SÍMBOLO] @ [entry] SL [sl] TP [tp]

**Validación del sistema:**
- Score: [X/+10 a -10]
- Veredicto: [GO FUERTE / GO MODERADO / GO TENTATIVO / ESPERA / NO-GO]
- Razón clave: [frase corta]

**Decisión del usuario:**
- [ ] No ejecuté (seguí el NO-GO del sistema)
- [ ] Ejecuté con size normal
- [ ] Ejecuté con size reducido
- [ ] Ejecuté ignorando NO-GO del sistema

**Si ejecuté:**
- Entry real: [precio]
- Exit: [precio]
- Resultado: [+/-$]
- ¿Se movió como esperaba la fuente? [sí/no]
- ¿Mi sistema tenía razón? [sí/no]

**Lección:**
- [Qué aprendí sobre este trader/este tipo de señal]
```

## Análisis periódico

**Cada 30 señales registradas, calcular:**

### Por fuente
- WR de señales que el sistema aprobó
- WR de señales que el sistema rechazó (si las seguiste igual)
- Profit Factor de la fuente
- ¿Vale la pena seguir a esta persona?

### Por tipo de señal
- Mean reversion vs breakout
- Por símbolo (BTC vs ETH vs alts)
- Por horario

**Decisión:**
- Si una fuente tiene WR < 50% → silenciar o ignorar
- Si una fuente tiene WR > 70% Y el sistema suele aprobarla → trust + seguir
- Si el sistema rechaza señales de una fuente pero terminan ganando → revisar si el sistema es demasiado strict para ese trader

## Estado actual

### Señal #1 — 2026-04-21 04:15 CR
**Fuente:** El Sabueso de Wall Street
**Comunidad:** punkchainer's Discord
**Señal:** SHORT XLMUSDT.P @ 0.1822 (sin SL/TP especificados)

**Validación del sistema:**
- Score: -1 / +10
- Veredicto: **ESPERAR / NO ENTRAR AHORA**
- Razón clave: Régimen TRENDING UP +7.54% en 30h — trade contra-trend en top. Precio ya pasó entry y rebotó 70% del drop máximo.

**Contexto adicional:**
- Entry del Sabueso fue en TOP del rally (high 0.18259)
- Mínimo tocado post-señal: 0.17992 (+1.25% profit máximo)
- Al momento de validación: 0.18124 (+0.54% profit si sigue abierto)
- Sin Neptune cargado en chart XLM (validación parcial)

**Decisión del usuario:**
- [ ] No ejecuté (seguí el ESPERAR del sistema)
- [ ] Ejecuté con size normal
- [ ] Ejecuté con size reducido
- [ ] Ejecuté ignorando sistema

**Setup alternativo sugerido (si quieres entrar):**
- Esperar retest 0.18220-0.18270 con rechazo confirmado
- SL: 0.18330 (+0.3%)
- TP1: 0.18060 | TP2: 0.17900 | TP3: 0.17750

**Resultado (pending — actualizar cuando se sepa):**
- Entry real: ___
- Exit: ___
- PnL: ___

**Lección:**
Traders como Sabueso shortean contra-trend en tops — win rate bajo pero cuando funciona da 1-2% move. Para cuenta chica (cap $11), R:R no compensa el riesgo de liquidación si el rally continúa.

## Why

Este tracker te permite **construir tu propia inteligencia** sobre qué fuentes vale la pena escuchar. No te quedas en "ese trader es bueno" — tienes DATA.

## How to apply

Cuando el usuario valide una señal con `/signal`:
1. Agente signal-validator ejecuta validación
2. Al final, ofrece al usuario: "¿La ejecutaste? ¿Cuál fue el resultado?"
3. Si responde, registra en este archivo con el formato arriba
4. Cada 10-20 señales registradas, sugerir review para detectar patrones

# Bitunix — Setup Neptune indicators (community config)

> Las señales que copias vienen de PunkAlgo bot que usa los indicadores Neptune con la config exacta de la comunidad. Para validar TÚ las señales, replica el setup en tu TV.

## Indicadores requeridos (TradingView, requieren invitación)

1. **Neptune® - Oscillator™** — meta-oscilador con WaveTrend, momentum, divergencias
2. **Neptune® - Signals™** — señales LONG/SHORT con Neptune Pilot + ML classifier
3. **Neptune® - SMC™** — Smart Money Concepts (order blocks, FVG, liquidity)
4. **Neptune® - ICT™** — ⚠️ NO existe como indicador separado. ICT está INTEGRADO en `Neptune® - Smart Money Concepts™` (mismo script). Usar siempre el nombre técnico exacto: `Neptune® - Smart Money Concepts™` para `chart_manage_indicator`.

⚠️ **Plan TradingView Basic** = max 2 indicadores por chart. Combo recomendado para validar señales bitunix:

```
Chart 1: Neptune Signals + Neptune Oscillator
Chart 2 (otro tab): Neptune SMC + Neptune Oscillator
```

## Configuraciones EXACTAS

Ver skills:
- **`@neptune-community-config`** — todas las configs (ICT, Signals, Oscillator, SMC) verificadas por la comunidad
- **`@neptune-alert-placeholders`** — JSON templates para webhooks si automatizas

## Reglas críticas reseñadas por la comunidad

1. **Neptune Signals: Sensitivity = MANUAL.** NO usar Automatic — la comunidad confirma "no es la misma efectividad".
2. **Neptune Oscillator: si tienes Neptune Signals activo** → desactivar el toggle "Neptune Signals" en el oscilador (evita duplicación).
3. **Money Flow: "Smart Money"** (no "Neptune") en oscilador para lectura institucional.
4. **Confluences Lines + Square ON** en oscilador es obligatorio para detectar confluencias visuales.
5. **Volume Analysis ON** detecta señales de momentum extremo en alta volatilidad.
6. **Neptune SMC: Modern UI ON** (diseño 2026).
7. **HH/LL toggle** se desactiva cuando activas ZigZag (mutuamente excluyentes en setup canónico).

## Workflow específico bitunix

Cuando llega una señal de PunkAlgo (ej: "MSTRUSDT Short 20x entry 166.57"):

```
1. Abre TradingView con el asset (BITUNIX:MSTRUSDT.P)
2. Aplica config Neptune según skill `neptune-community-config`
3. Verifica el setup VISUALMENTE en tu chart:
   - ¿Neptune Signals dibujó la flecha de entry?
   - ¿Neptune Oscillator confirma con confluencias?
   - ¿Neptune SMC marca un OB/FVG/breaker compatible?
   - ¿Hay divergencias visibles?
4. Ejecuta /signal en Claude para validación cuantitativa:
   /signal MSTRUSDT short 166.57 sl=170 tp=160 leverage=20
5. Si /signal aprueba CON multifactor>50 + ML>55 → ejecutar
6. NO ejecutar si tu chart con setup Neptune NO confirma (aunque /signal apruebe)
```

## Filosofía de validación con Neptune

> "Si la comunidad genera señales con estos indicadores, debo poder LEER los mismos indicadores. Si veo el chart y no entiendo el setup → SKIP. La señal puede ser correcta pero si yo no la entiendo, no la opero."

Esto es lo que distingue **copy-validated** de **copy-blind**. Las señales son input, no oracle.

## Limitaciones honestas

- Los indicadores Neptune son **invitación-only** de Bangchan10. Si NO estás en la comunidad punkchainer's (con acceso por subscription o invitación) → NO podrás usar este profile efectivamente.
- Plan TradingView Basic limita a 2 indicadores. Tener layout pre-guardado para switch rápido entre combos.
- La interpretación es subjetiva — el sistema (`/signal`) provee score numérico, pero la confianza final viene de tu lectura del chart con Neptune.

# Profile: BITUNIX (copy trading punkchainer's community)

**Capital:** $50.00 USD inicial (default — ajustable)
**Plataforma:** [Bitunix](https://bitunix.com) — exchange crypto perpetual futures
**Referral code:** `punkchainer` (descuento en fees, igual que la comunidad)
**Modelo:** **NO ES ANÁLISIS PROPIO.** Es validación + copia de señales de la comunidad punkchainer's.

## Filosofía operativa

> El edge aquí NO es generar señales. Es **filtrar las malas**.

La comunidad punkchainer's en Discord publica señales de trading (BTC, ETH, MSTRUSDT, otros perpetual). El bot `PunkAlgo` postea dirección/leverage/entry. Tu sistema valida CADA señal con tus filtros propios antes de copiar:

- ¿4 filtros técnicos alineados? (`/signal` agent)
- ¿Multi-Factor score >+50 (long) o <-50 (short)?
- ¿ML XGBoost score >55?
- ¿Chainlink price valida (no wick fake)?
- ¿Régimen del asset compatible con dirección?

**Si pasa todo → COPIAR.**
**Si falla cualquiera → SKIP** (la comunidad puede usar lógica distinta a la tuya).

Este profile es perfecto para:
1. **Validar el edge de la comunidad** (¿cuántas de sus señales pasan tus filtros?)
2. **Aprender por contraste** (¿qué señales tomaron ellos que tú rechazaste y resultaron WIN?)
3. **Diversificar capital** sin replicar setups de retail/FTMO

## Universo de assets

**Dinámico** — depende de lo que la comunidad señale en cualquier momento.

Histórico observado en señales punkchainer's:
- BTCUSDT.P, ETHUSDT.P (mayoría)
- Altcoins memecaps (MSTRUSDT, FARTCOIN, PEPE, WIF, etc.)
- Ocasionalmente: SOL, AVAX, INJ, otros L1/L2 perpetuals

## Reglas duras (ver `rules.md`)

| Regla | Valor | Tipo |
|---|---|---|
| Risk per copied signal | 2% capital | hard cap |
| Max copied signals / día | **3** | BLOCK |
| Min validation score | 60% (4/4 filtros + multifactor>50) | gate |
| Max leverage | **10x** (NO usar 20x aunque la señal lo diga) | safety override |
| Daily loss BLOCK | -6% (3 SLs consecutivos) | STOP día |
| Max DD del capital | -30% | STOP profile + review |
| Auto-blacklist asset | Después de 2 SLs consecutivos en mismo asset | filter |
| Ventana | 24/7 (cripto) — pero mejor London/NY overlap | INFO |

## Cómo funciona el flow

```
[Discord punkchainer's]
   ↓ señal nueva: "MSTRUSDT Short 20x entry 166.57"
   
[Tú lees y ejecutas]
/signal MSTRUSDT short 166.57 sl=170 tp=160 leverage=20
   ↓
[Sistema valida con 4 capas]
   - 4 filtros técnicos
   - Multi-Factor score
   - ML XGBoost score
   - Chainlink cross-check
   ↓
[Veredicto]
   GO confidence>=60 → recomienda EJECUTAR (override leverage 20→10)
   NO-GO confidence<60 → SKIP, anota razón en memory/signals_received.md
   
[Tú ejecutas manual en Bitunix]
   - Login Bitunix
   - Open MSTRUSDT-PERP, side SHORT
   - Size: 2% del capital con leverage 10x (no 20x)
   - SL en 170, TPs escalonados
   
[Tracking automático]
   /equity bitunix <new>  → actualiza equity_curve
   /journal              → log + outperformance metrics
```

## Reglas cross-profile

1. **NO copiar señal Bitunix de BTC si tienes posición BTC en retail/ftmo/quantfury.** Doble exposición = riesgo correlacionado.
2. **Nunca exceder leverage 10x en Bitunix** aunque la señal pida 20x. (Las pérdidas escalan no-linealmente con leverage; el edge de la señal se mantiene mejor con leverage menor.)
3. **Documentar SKIPS** — cada señal que rechaces va a `memory/signals_received.md`. Después puedes verificar si esa señal HUBIERA ganado (FOMO check).

## Setup inicial

```bash
# 1. Registro en Bitunix con código de referido
#    https://bitunix.com — usa código `punkchainer`

# 2. Depósito inicial $50 (vía USDT en BSC/Polygon, low fee)

# 3. Llenar credenciales en .env (NO necesarias para read-only):
#    BITUNIX_API_KEY=<...>           # solo si quieres tracking automático
#    BITUNIX_API_SECRET=<...>
#    BITUNIX_REFERRAL_CODE=punkchainer

# 4. Switch profile
/profile bitunix

# 5. Test con primera señal
# Cuando aparezca señal en Discord:
/signal <SYMBOL> <SIDE> <entry> sl=<sl> tp=<tp> leverage=<lev>
```

## Métricas a trackear

- **Hit rate de señales validadas** — de las que tu sistema aprueba, ¿cuántas son WIN?
- **Hit rate de señales rechazadas** — de las que SKIP, ¿cuántas hubieran sido WIN? (si >50%, tus filtros son demasiado restrictivos)
- **Comparativa vs replicar todo blindly** — si copias 100% sin filtrar vs filtrar con tu sistema, ¿cuál hubiera dado mejor PnL?
- **Outperformance vs solo retail** — ¿bitunix tiene mejor edge que tu sistema solo en BTC?

## Disclaimer

Las señales de la comunidad NO son consejo financiero. Tú decides ejecutar después de validar. El sistema NO ejecuta automáticamente.

> "El edge no es seguir gurús — es entender por qué su señal funciona (o no) y tener tu propia lógica para validar."

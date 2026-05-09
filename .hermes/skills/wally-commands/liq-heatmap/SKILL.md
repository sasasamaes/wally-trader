---
name: liq-heatmap
description: Mapa de clusters de liquidación (longs/shorts) — detecta zonas magnéticas
  donde MMs cazan stops
version: 1.0.0
metadata:
  hermes:
    tags:
    - wally-trader
    - command
    - slash
    category: trading-command
    requires_toolsets:
    - terminal
    - subagents
---
<!-- generated from system/commands/liq-heatmap.md by adapters/hermes/transform.py -->
<!-- Hermes invokes via /liq-heatmap -->


Estima los clusters de liquidación más probables para un perpetual usando data pública (Open Interest, L/S ratios, leverage tiers comunes 5x-100x). Dibuja líneas horizontales en TradingView marcando los niveles "imán" donde los market makers tienden a cazar stops.

Inspirado en el video YouTube de Cloud Code + TradingView donde el host muestra un heatmap de liquidaciones (típicamente Coinglass-style). Esta versión funciona **sin APIs pagadas** combinando OI + L/S + leverage distribution.

## Uso

```
/liq-heatmap <SYMBOL>
/liq-heatmap BTCUSDT
/liq-heatmap TONUSDT --top 10
/liq-heatmap ETHUSDT --no-draw    # solo análisis, sin dibujar TV
```

## Pasos

1. **Estimar clusters:**
   ```bash
   python3 .claude/scripts/liq_heatmap.py --symbol <SYMBOL> --quick
   ```
   El script:
   - Pull precio + 24h high/low + OI + L/S ratios (Binance Futures public)
   - Para cada leverage tier (5x/10x/20x/50x/100x), calcula precio de liquidación desde anchor points (24h low, 24h high, retrace 30%/60%, current)
   - Pondera por (a) popularidad del leverage, (b) bias L/S
   - Agrupa precios cercanos (~0.1% bucket) y normaliza heat score 0-100

2. **Identificar magnet** (cluster más cercano con heat≥50):
   - Si LONG-side: precio probablemente baja a cazar esos stops
   - Si SHORT-side: precio probablemente sube a cazar esos stops
   - Si ambos lados balanceados: no hay magnet claro, usar otros factores

3. **Dibujar en TradingView** (a menos que `--no-draw`):
   - `chart_set_symbol(<SYMBOL>)` si distinto al activo
   - Limpiar dibujos previos (opcional, preguntar primero si hay otros)
   - Para cada cluster con heat ≥ 70:
     - LONG-side (price down) → línea ROJA punteada con texto `LIQ-LONG <heat>`
     - SHORT-side (price up) → línea VERDE punteada con texto `LIQ-SHORT <heat>`
   - Para el magnet específicamente → línea sólida más gruesa con texto `🧲 MAGNET`

4. **Reportar al usuario:**

```markdown
🔥 LIQ HEATMAP — TONUSDT

## Estado actual
- Precio: $2.471
- OI: $96.6M
- Smart Money L/S: 1.60 (longs cargados)
- Retail L/S: 1.11

## 🧲 Magnet: $2.360 (-4.50%) side=LONG_LIQ heat=100
**Interpretación:** longs heavy en $2.40-2.47 con leverage 20x → stops clusterizan en $2.36. Market makers tienen incentivo de empujar el precio a ese nivel.

## 🔴 SHORT-side clusters (price UP to trigger)
| Precio | Distancia | Heat |
|---|---|---|
| $2.582 | +4.5% | 100 ████████ |
| $2.656 | +7.5% | 100 ████████ |
| $2.712 | +9.8% | 100 ████████ |
| $2.768 | +12.0% | 100 ████████ |

## 🟢 LONG-side clusters (price DOWN to trigger)
| Precio | Distancia | Heat |
|---|---|---|
| $2.360 | -4.5% | 100 ████████ ⭐ MAGNET |
| $2.325 | -5.9% | 100 ████████ |
| $2.298 | -7.0% | 100 ████████ |
| $2.272 | -8.1% | 100 ████████ |

## 🎯 Implicaciones operativas

**Si estás SHORT (como ahora con TON):**
- ✅ Magnet $2.36 favorece tu TP1 $2.355 — alta probabilidad de fill
- ✅ Cluster cascade $2.27 - $2.36 = movimiento limpio si rompe $2.379
- ⚠️ Resistance squeeze en $2.58+ pero está MUY lejos para preocuparse

**Si estás LONG:**
- ⚠️ Si TP1 está en $2.55+, magnet en LONG-side te jala en contra
- ⚠️ SL debe estar arriba de $2.36 para no caer en honeypot

## ✅ Dibujado en TradingView
- 8 clusters dibujados como horizontal lines
- Magnet $2.360 marcado con línea sólida + texto
- 4 SHORT-side (verde) + 4 LONG-side (rojo)
```

## Reglas

- **Heat score normalizado 0-100 por side** — no comparar heat entre LONG y SHORT directamente
- **Magnet** = cluster MÁS CERCANO con heat ≥ 50, no el de mayor heat absoluto
- **NO dibujar más de 8 líneas** total (4 cada lado max) para no saturar el chart
- **Symbol must be Binance Futures pair** (acaba en USDT). Si user pasa otro exchange, advertir que los OI/LS son de Binance, no necesariamente representativos
- **Si error fetching data** → reportar exit code 1 con razón, NO dibujar
- **Refresh cadencia:** liq levels cambian con OI hourly; recomendable re-correr cada 1-2h durante trade activo

## Casos de uso operativos

1. **Pre-entry:** verificar si tu TP/SL está en zona de honeypot (cluster heat alto) — si tu SL coincide con cluster MMs lo pueden cazar
2. **Mid-trade adaptativo:** ajustar TPs hacia magnet más cercano para fill probable
3. **Liquidation cascade detection:** si precio rompe nivel con heat alto, cascade a próximos clusters es típica
4. **Squeeze setup:** Si SHORT clusters densos arriba + price near support → asymmetric long setup (squeeze potential)

## Limitaciones honest-first

- **NO es Coinglass real** — aproximación con leverage distribution asumida (no datos reales de open positions por exchange)
- **Solo Binance Futures data** — Bitunix/OKX/etc. tienen distribuciones distintas, esta es proxy razonable pero no exacta
- **Subestima clusters >100x** — algunos perp exchanges permiten 125x+, ese tail no se captura
- **Falla en small-cap altcoins** sin OI significativo en Binance — usar solo si OI > $5M

## Disclaimer

Liquidation heatmaps sirven para **gestión adaptativa**, NO para timing absoluto. El magnet típicamente se cumple en ventanas 1-12h pero puede no resolverse en absoluto si hay catalysts macro, news, o flujos institucionales no reflejados en OI público.

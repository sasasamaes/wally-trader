# Estrategia: Mean Reversion 15m (RETAIL)

Validada con **100% WR** y **+15.1%** en backtest 3 días frente a 144 configs.

## Parámetros

| Parámetro | Valor |
|---|---|
| Timeframe | 15m |
| Donchian | 15 velas |
| Edge de entrada | ±0.1% del extremo Donchian |
| RSI(14) | OB 65, OS 35 |
| Bollinger Bands | (20, 2) confirmación obligatoria |
| ATR length | 14 |
| SL | 1.5 × ATR (adaptativo) |
| TP1 (40%) | 2.5 × SL → SL a BE |
| TP2 (40%) | 4.0 × SL |
| TP3 (20%) | 6.0 × SL |
| Leverage | 10x |
| Ventana | CR 06:00 – 23:59 |

## Entradas — 4 filtros obligatorios

**LONG:**
1. Precio toca o cruza Donchian Low(15) (dentro 0.1%)
2. RSI < 35
3. Low de vela toca BB inferior
4. Vela cierra verde

**SHORT:**
1. Precio toca o cruza Donchian High(15) (dentro 0.1%)
2. RSI > 65
3. High de vela toca BB superior
4. Vela cierra roja

## Invalidación

- 2 SLs consecutivos → parar ese día
- Días con noticias macro (CPI, Fed) → no operar
- ATR 2x promedio → no operar (régimen volatile)

## Estrategia secundaria

Donchian Breakout si BTC rompe el range (cierre 4H fuera de 73.5k–78.3k con volumen >2x promedio). Config: Donchian(20), buffer 30 pts, vol >300 BTC, SL 0.5%, TP 0.75/1.25/2.0%.

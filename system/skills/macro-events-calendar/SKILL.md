---
name: macro-events-calendar
description: Use cuando user pregunte por "noticias macro", "eventos macro", "FOMC", "CPI", "NFP", "events de la semana", o cuando esté planeando trades para los próximos días y necesite saber si hay catalysts macro que pueden romper sus setups. Crítico antes de morning sessions y backtest validation.
---

# Macro Events Calendar — eventos que mueven mercados

> En 5 minutos un evento macro puede romper cualquier setup técnico. **Conocer el calendario es proteger capital**.

## Eventos críticos (riesgo alto — NO operar 30min antes/después)

### USA — moves $-200 a +500 BPS típicos

| Evento | Frecuencia | Hora CR (EST-1) | Impacto típico |
|---|---|---|---|
| **FOMC Meeting + Powell speech** | 8/año (~6 sem) | 13:00-14:30 | ±2-5% en BTC, ±100bps en DXY |
| **CPI (Inflation)** | Mensual, día 10-15 | 06:30 | ±2-4% en BTC, ±60bps DXY |
| **PCE (Fed's preferred)** | Mensual, fin de mes | 06:30 | ±1-3% BTC |
| **NFP (Non-Farm Payrolls)** | 1er viernes mes | 06:30 | ±1-3% BTC, fuerte en DXY |
| **GDP (preliminary)** | Trimestral | 06:30 | ±1-2% BTC |
| **PPI (Producer Prices)** | Mensual | 06:30 | ±1-2% BTC |
| **Jobless Claims** | Semanal jueves | 06:30 | <0.5% BTC, mayor DXY |
| **Consumer Confidence** | Mensual | 09:00 | <0.5% BTC |

### Europa / UK / Japón

| Evento | Frecuencia | Impacto |
|---|---|---|
| **ECB Rate Decision** | 8/año | ±150bps EUR, mediano BTC |
| **BoE Rate Decision** | 8/año | ±100bps GBP, bajo BTC |
| **BoJ Meeting** | 8/año | ±100bps JPY, bajo BTC |
| **Eurozone CPI** | Mensual | ±60bps EUR |

### Crypto-específicos (sin schedule fijo)

| Evento | Naturaleza | Impacto |
|---|---|---|
| **BTC Halving** | Cada 4 años (~Apr) | Histórico +200% en 12-18 meses post |
| **ETF approval/rejection** | Esporádico | ±10-20% BTC en horas |
| **Hard fork** | Anuncios | ±5-10% pre/post |
| **Major hacks/exploits** | Random | ±3-15% en horas (FTX, Terra, etc.) |
| **Regulatory news** (SEC, MiCA) | Random | ±5-15% BTC |

## Reglas operativas

### Antes de FOMC / CPI / NFP

- **30 min antes**: NO abrir nuevas posiciones
- **15 min antes**: cerrar SLs muy cerca del precio (mover SL alejado o cerrar)
- **Durante el evento (5-15 min)**: stand-aside total
- **30 min después**: dejar que el primer swing termine, luego evaluar entry

### Configuración watchlist semanal

Cada **domingo en `/review`** revisar el calendario macro próximo y marcar:
- 🔴 **NO TRADE** días con FOMC / CPI / NFP
- 🟡 **HALF SIZE** días con Fed speeches o data secundaria
- 🟢 **NORMAL** días sin eventos relevantes

## Fuentes para consultar el calendario

### APIs / Endpoints (free, sin key)

```bash
# Forex Factory (HTML scraping pero estructurado)
curl 'https://www.forexfactory.com/calendar'

# Investing.com (RSS feed)
curl 'https://www.investing.com/rss/news_25.rss'

# TradingEconomics calendar (free tier)
curl 'https://api.tradingeconomics.com/calendar?c=guest:guest&country=united%20states'

# FRED (St. Louis Fed) — series histórica
curl 'https://api.stlouisfed.org/fred/releases?api_key=YOUR_KEY&file_type=json'
```

### Web (manual check)

- **Forex Factory**: https://www.forexfactory.com/calendar (más usado por traders)
- **Investing.com calendar**: https://www.investing.com/economic-calendar/
- **TradingView events**: integrado en el chart (right sidebar)

## Cómo integrarlo en el sistema

### Opción A: pre-flight check manual

```bash
# Antes del /morning, lee Forex Factory:
# Si día tiene 🔴 events → /morning hace BLOCK con mensaje
# "No trading hoy: FOMC scheduled at 13:30 CR"
```

### Opción B: hook automático (futuro)

```python
# .claude/scripts/macro_calendar.py
# Lee Forex Factory el lunes, cachea events de la semana
# /validate y /risk leen el cache, BLOCK 30min around events
```

## Backtest insight

Backtest del 2026-04-30 NO incluyó filtro macro. Los días con FOMC/CPI mostraron
**WR -10pp** vs días normales (la volatilidad rompe setups). Implementar este filtro
en una versión futura del engine podría mejorar WR sustancialmente.

## Referencias

- Federal Reserve calendar: https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm
- ECB schedule: https://www.ecb.europa.eu/press/calendars/governingcouncil/html/index.en.html
- BLS (CPI/NFP) release schedule: https://www.bls.gov/schedule/news_release/

## Disclaimer

Calendarios cambian — confirma siempre las fechas exactas con fuentes oficiales
antes de operar. La Fed a veces convoca emergency meetings (e.g. March 2020).

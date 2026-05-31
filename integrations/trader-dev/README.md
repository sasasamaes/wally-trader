# Trader Dev MCP — integración (ready-to-connect)

MCP server de [DaviddTech](https://daviddtech.com) / [StrategyFactory.ai](https://strategyfactory.ai),
del video **"I Let Claude AI Opus 4.8 Trade For Me"** (`youtube.com/watch?v=tkAq6g2Gjz4`).

> ⚠️ **No hay endpoint público documentado.** A diferencia de Jesse (Docker Hub + docs
> abiertos), el install de Trader Dev MCP está **gated**: se obtiene registrándose en
> StrategyFactory.ai o comentando "Claude code" en el video para recibir la línea de instalación.
> **No inventamos una URL.** Este scaffold queda listo para conectar en cuanto tengas el endpoint.

## Qué hace (según el video + StrategyFactory)

Gestiona el workflow de un "AI hedge-fund desk": generar hipótesis de trading, escribir Pine
Script, backtest multi-par y multi-timeframe en TradingView, optimizar parámetros, comparar
estrategias y generar reportes.

## ⚠️ Solapamiento con el stack nativo de Wally

Casi todo lo que hace Trader Dev MCP ya está cubierto por el proyecto **sin depender de un
servicio externo**:

| Trader Dev MCP | Equivalente nativo Wally |
|---|---|
| Pine Script generation | `/pine-gen` (indicadores) + `/optimize --export-pine` (`strategy()`) |
| Backtest multi-par/TF | `backtest-runner` (`/backtest`), `per_asset_backtest.py` |
| Optimizar parámetros | **`/optimize`** (loop con gates anti-overfit RST+OOS+Monte Carlo) |
| Reportes | output markdown de cada comando + `docs/` |
| Validación de robustez | `/rst`, `/montecarlo` (Bundle 5) — más estricto que el del video |

Por eso es **opcional**: úsalo si quieres su biblioteca de estrategias copy-trade o su
plataforma de forward-testing; para el ciclo build→backtest→optimize→validate, el stack
nativo ya lo hace (y con gates anti-overfit que el video no aplica).

## Cómo conectarlo (cuando tengas el endpoint)

1. **Consigue el install line / URL del MCP:**
   - Regístrate en https://strategyfactory.ai/ (recursos gratis en
     https://app.strategyfactory.ai/resources/), o
   - Comenta "Claude code" en el video para que te envíen el workbook + la línea de instalación.

2. **Regístralo en Claude Code** (rellena `<URL-REAL>` con lo que te den):
   ```bash
   # Si es HTTP/SSE remoto:
   claude mcp add --transport http trader-dev <URL-REAL>

   # Si es un binario/STDIO local (npx, node, python):
   claude mcp add trader-dev -- <comando-de-arranque>
   ```
   Añade `--scope user` para tenerlo en todos los proyectos.

3. **Verifica:**
   ```
   /mcp        # debe aparecer "trader-dev" como Connected
   ```

## Honestidad

- El proyecto Wally **proposes, you approve** y NO auto-ejecuta en exchanges (el video sí, en
  Bybit). Si conectas Trader Dev MCP, mantén esa frontera: úsalo para research/backtest, no
  para auto-trading sin tu visto bueno (regla de riesgo del proyecto).
- Si nunca consigues el endpoint, no pasa nada: `/optimize` + `/rst` + `/montecarlo` cubren el
  flujo del video con más rigor.

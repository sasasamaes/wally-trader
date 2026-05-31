# Jesse — laboratorio de investigación paralelo

Integración del framework [Jesse](https://jesse.trade) como **laboratorio de R&D y
validación profunda**, destilado del video *"Opus 4.8 + Claude Code + MCP = Algo Trading
on Autopilot"* (Algo-trading with Saleh).

> ⚠️ **Jesse NO reemplaza el motor de backtest de Wally Trader.** El motor propio
> (`.claude/scripts/`, profiles, `regime_mapping.json`, TV MCP) sigue siendo la fuente de
> verdad para decisiones live. Jesse corre **en paralelo** como herramienta opcional para:
> - Backtests de año completo con su motor maduro (Jesse pagina candles a DB, sin el cap
>   de 300 barras del MCP de TradingView).
> - **Monte Carlo nativo** (trades + candles) y **walk-forward** desde su dashboard/MCP.
> - Hyperparameter tuning.
>
> La destilación **durable y portable** del video ya vive en el motor Wally:
> `.claude/scripts/rule_significance.py` (RST) + `.claude/scripts/monte_carlo.py`
> (ver `/rst` y `/montecarlo`). Jesse es power-tooling, no dependencia.

## Qué es Jesse

Framework Python de algo-trading que requiere **PostgreSQL** (el stack oficial corre sobre
`postgres:14-alpine`), expone REST API + dashboard + un **servidor MCP** (~32 tools:
backtest, tuning con walk-forward, Monte Carlo, VaR/stress). Las estrategias se escriben como
clases `Strategy`
(`should_long`/`go_long`/`update_position`). En el video el agente escribe la estrategia,
corre un *rule significance test* sobre el motor de Jesse, backtestea, y usa el Monte Carlo
nativo del dashboard.

## Setup (lo ejecuta/autoriza el usuario)

> Estos pasos tocan Docker / servicios de sistema y descargas externas. Claude prepara los
> archivos pero **el usuario los corre** en su máquina.

### Opción A — Docker (recomendada)

1. Copia el entorno y ajusta credenciales/puerto:
   ```bash
   cd integrations/jesse
   cp .env.example .env
   # edita .env si quieres otro puerto / password
   ```
2. Levanta el stack (Postgres + Jesse + visor de trades):
   ```bash
   docker compose up -d
   docker compose logs -f jesse   # primera vez baja imágenes (varios min)
   ```
   > El `docker-compose.yml` está alineado con el stack oficial
   > https://github.com/jesse-ai/jesse-stack-docker (imagen `salehmir/jesse:latest`,
   > `postgres:14-alpine`). Reconcilia con https://docs.jesse.trade/docs/getting-started/docker
   > si la versión cambió (los docs bloquean fetch automatizado, revísalos a mano).
3. Abre el dashboard en `http://localhost:8888` y crea/loguea tu cuenta Jesse local.
   (El visor `jesse-trades-info` queda en `http://localhost:3000`.)

### Opción B — pip en venv (requiere Postgres local)

```bash
python3.13 -m venv ~/jesse-venv && source ~/jesse-venv/bin/activate
pip install jesse
# Postgres debe estar corriendo y configurado en el .env del proyecto Jesse
cd <tu-proyecto-jesse> && jesse run
```

## Importar candles

Jesse necesita su propia DB de velas. Usa el helper:

```bash
cd integrations/jesse
./import_candles.sh BTC-USDT Binance 2024-01-01   # exchange, símbolo formato BASE-QUOTE
```

El script llama al endpoint `/candles/import` del REST de Jesse (ver el archivo para auth).

## Conectar el MCP a Claude Code

Ver [`connect_mcp.md`](./connect_mcp.md). Resumen: `jesse run` imprime una URL terminada en
`/mcp`; conéctala con `claude mcp add --transport http jesse <esa-url>`.

## Estrategia de ejemplo

[`strategies/DonchianEMATrend.py`](./strategies/DonchianEMATrend.py) — port fiel de la
estrategia del video (Donchian breakout + filtro EMA, long-only, SL por ATR, salida
estructural en banda Donchian baja). Cópiala a tu carpeta `strategies/` del proyecto Jesse.
[`strategies/_TEMPLATE.py`](./strategies/_TEMPLATE.py) — esqueleto en blanco.

## Caveat honesto del video

El presentador concluye que la estrategia ganadora (Sharpe 2.11 en 2024) **se cae fuera de
un uptrend limpio** (2025 negativo) → *no production-ready*. Jesse no lo salva: un Monte
Carlo o walk-forward sobre data de un solo régimen hereda los sesgos de ese régimen. La
herramienta acelera la iteración honesta; no fabrica edge.

# Conectar el MCP de Jesse a Claude Code

El framework Jesse expone su propio servidor MCP. En el video se conecta con un solo comando
copiado de los docs de Jesse (sección *MCP → connect in Claude Code*).

## Pasos

1. **Levanta Jesse** (ver [README](./README.md)). Con los contenedores arriba, corre el
   servidor desde el proyecto Jesse:
   ```bash
   jesse run
   ```
   La terminal imprime **dos** URLs: la del dashboard y la del **MCP** (termina en `/mcp`),
   típicamente algo como `http://localhost:9002/mcp` (el puerto depende de tu `MCP_PORT`).

2. **Registra el MCP en Claude Code** (transporte HTTP):
   ```bash
   claude mcp add --transport http jesse http://localhost:9002/mcp
   ```
   - Usa exactamente la URL que imprimió `jesse run` (puerto correcto + `/mcp`).
   - Añade `--scope user` para tenerlo disponible en todos los proyectos:
     ```bash
     claude mcp add --transport http --scope user jesse http://localhost:9002/mcp
     ```

3. **Verifica** dentro de Claude Code:
   ```
   /mcp            # lista servidores MCP conectados → debe aparecer "jesse"
   ```
   Las tools de Jesse (backtest, monte_carlo, walk-forward, VaR, etc.) quedan disponibles
   vía ToolSearch como cualquier otro MCP de la sesión.

## Notas

- Jesse es un **segundo servidor MCP**; coexiste sin conflicto con el MCP de TradingView que
  ya usa el proyecto.
- Si cambiaste el puerto en `.env` (como el presentador del video, que usó 9000), la URL del
  MCP cambia en consecuencia — **siempre copia la que imprime `jesse run`**, no la asumas.
- Fuente oficial (revisar a mano, bloquea fetch automatizado):
  `https://docs.jesse.trade/docs/mcp/connect-claude-code`.

## Flujo de validación con Jesse (replica el video)

1. Pídele al agente que escriba una estrategia trend-following (o copia
   [`strategies/DonchianEMATrend.py`](./strategies/DonchianEMATrend.py)).
2. Corre un **rule significance test** sobre la entrada (en Wally: `/rst`; en Jesse: vía sus
   tools de robustez).
3. Backtest del año completo.
4. **Monte Carlo trades + candles** (dashboard de Jesse, o en Wally `/montecarlo`).
5. **Out-of-sample** en otros años (2023 / 2025) — el momento de la verdad del video.
6. Veredicto honesto: si se cae fuera de un uptrend limpio, **no está listo para live**.

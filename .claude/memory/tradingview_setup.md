---
name: TradingView setup y limitaciones del MCP
description: Cómo está configurado el TV del usuario y qué limitaciones del MCP conocer
type: reference
originSessionId: 870cfb36-0066-4b6c-a1b7-eeaebc9a6ca8
---
**Chart del usuario:**
- URL: https://es.tradingview.com/chart/CvbQeQGs/
- Symbol default: BINGX:BTCUSDT.P
- Idioma interfaz: Español

**Plan TradingView: Basic**
- Máximo 2 indicadores por chart
- Los 2 slots están ocupados por: `Neptune® - Signals™` + `Neptune® - Oscillator™`
- **Consecuencia:** agregar Supertrend/EMA/RSI/MACD vía MCP no es posible sin primero remover un Neptune
- Pine strategy se puede compilar pero no correr en Strategy Tester (mismo límite)

**Bugs conocidos del MCP (2026-04):**

1. **`draw_clear` falla con "getChartApi is not defined"**
   - Workaround: click derecho en trash icon del left sidebar → aparece menú contextual → `ui_click` con `data-name="remove-drawing-tools"` (o `remove-all` para todo)
   - Este workaround sí funciona consistentemente

2. **`draw_remove_one` también falla con mismo error**
   - Mismo workaround que draw_clear

3. **`pine_new` puede fallar con "Could not open Pine Editor"**
   - Workaround: abrir panel primero con `ui_open_panel panel=pine-editor action=open`, luego `pine_new`

4. **`pine_compile` no siempre activa el botón "Añadir al gráfico"**
   - Workaround: click manual vía `ui_mouse_click` en coord (1019, 79) después de guardar

5. **`data_get_strategy_results` retorna vacío aún con strategy añadida** (cuando hay un toast/ad cubriendo el bottom panel)
   - Workaround: cerrar toast con `ui_click aria-label=toast-group-close-button-*`, luego abrir strategy tester panel

**Limitaciones de data:**
- `data_get_ohlcv` retorna MAX 300 barras por llamada (el param `count: 500` se ignora, cap duro)
- Para más data histórica → no disponible con el plan Basic actual

**Workflow recomendado para dibujos:**
```
1. Click derecho trash icon (x=12, y=619)
2. ui_click data-name="remove-drawing-tools" (o remove-all)
3. Dibujar nuevos niveles con draw_shape (una llamada por nivel)
4. Usar colores: #2962FF (azul trigger), #E53935 (rojo SL), #43A047/66BB6A (verde TPs), #FF6F00 (naranja time stop)
```

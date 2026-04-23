# ClaudeBridge EA — Guía de Usuario

Expert Advisor MQL5 que conecta Claude Code con MetaTrader 5 mediante archivos JSON.
Claude escribe comandos → el EA los ejecuta → escribe estado → Claude lo lee.

---

## Qué es un Expert Advisor (EA)

Un EA es un programa que corre dentro de MetaTrader 5 y puede ejecutar órdenes automáticamente.
ClaudeBridge NO toma decisiones de trading: solo ejecuta lo que Claude le indica via archivos JSON.
Claude sigue siendo quien analiza, valida reglas FTMO, y decide si abrir o cerrar posición.

---

## Arquitectura del bridge

```
Claude Code                   MQL5/Files/ (compartido)       MetaTrader 5
─────────────────            ──────────────────────────      ──────────────────
/order → mt5_bridge.py  →→→  claude_mt5_commands.json  →→→  ClaudeBridge EA
                         ←←←  claude_mt5_state.json     ←←←  (OnTimer cada 5s)
/trades ← mt5_bridge.py ←←←
```

Los archivos JSON actúan como cola de mensajes. Claude escribe comandos con `processed: false`.
El EA los ejecuta y marca `processed: true` con el resultado. El EA escribe estado completo cada 5s.

---

## Pre-requisitos

1. **MetaTrader 5** instalado en macOS (via CrossOver/Wine/Bottles).
   Descarga oficial: https://www.metatrader5.com/en/download
2. **Cuenta FTMO Demo** lista (login, password, server configurados en `.claude/.env`).
3. **Python 3.8+** instalado (para `mt5_bridge.py`).
4. Haber corrido `install.sh` al menos una vez.

---

## Paso 1: Correr install.sh

```bash
# Desde la raíz del repositorio:
bash .claude/profiles/ftmo/mt5_ea/install.sh
```

El script:
- Detecta automáticamente el bottle de MT5 en macOS.
- Copia `ClaudeBridge.mq5` a `MQL5/Experts/`.
- Crea `claude_mt5_state.json` y `claude_mt5_commands.json` en `MQL5/Files/`.
- Crea symlinks en `.claude/profiles/ftmo/memory/` apuntando a esos archivos.
- Guarda `MT5_FILES_PATH` en `.claude/.env`.

Si el auto-detect falla, define `MT5_FILES_PATH` manualmente en `.claude/.env` antes de correr.

---

## Paso 2: Habilitar Expert Advisors en MT5

1. Abrir MetaTrader 5.
2. **Tools → Options → Expert Advisors**:
   - Marcar **"Allow algorithmic trading"**
   - Marcar **"Allow DLL imports"** (por si acaso)
   - Click **OK**.

---

## Paso 3: Compilar el EA (si no compiló automático)

1. **Tools → MetaEditor** (o `F4`).
2. **File → Open** → navegar a `MQL5/Experts/ClaudeBridge.mq5`.
3. Presionar **F7** para compilar.
4. En la pestaña **Errors**: debe decir "0 errors, 0 warnings" (o solo warnings menores).
5. Cerrar MetaEditor.

---

## Paso 4: Activar en un chart

1. Abrir **Navigator** con `Ctrl+N`.
2. Expandir **Expert Advisors** → presionar **F5** para refrescar.
3. Debe aparecer **"ClaudeBridge"** en la lista.
4. Arrastrar **ClaudeBridge** a cualquier chart (recomendado: BTCUSD o EURUSD).
5. En el diálogo de configuración:
   - Pestaña **Common**: marcar **"Allow Automated Trading"**.
   - Pestaña **Inputs**: revisar valores (HeartbeatSec=5, Magic=77777, AllowExecution=true).
   - Click **OK**.

---

## Paso 5: Verificar inicio correcto

1. Ir a **View → Terminal** → pestaña **Experts** (`Ctrl+T`).
2. Debe aparecer:
   ```
   ClaudeBridge EA v1.00 starting magic=77777 heartbeat=5s AllowExecution=true
   ```
3. Si aparece, el EA está activo y escribe estado cada 5 segundos.

---

## Paso 6: Verificar que escribe estado

Esperar ~10 segundos, luego en terminal:

```bash
cat .claude/profiles/ftmo/memory/mt5_state.json | python3 -m json.tool | head -30
```

Debe mostrar JSON con:
- `"last_update"`: timestamp reciente (hace menos de 10s).
- `"account"`: balance, equity, servidor.
- `"positions"`: `[]` si no hay posiciones abiertas.
- `"pending_orders"`: `[]` si no hay órdenes pendientes.
- `"closed_today"`: `[]` si no hubo trades hoy.

---

## Inputs configurables del EA

| Input | Default | Descripción |
|---|---|---|
| `HeartbeatSec` | 5 | Segundos entre cada ciclo de OnTimer |
| `Magic` | 77777 | Magic number; filtra solo nuestras posiciones |
| `CommandsFile` | `claude_mt5_commands.json` | Nombre del archivo de comandos en MQL5/Files/ |
| `StateFile` | `claude_mt5_state.json` | Nombre del archivo de estado que escribe el EA |
| `AllowExecution` | true | **Kill-switch**: false = solo monitoreo, no ejecuta órdenes |

Para cambiar un input: click derecho en el EA en el chart → **Properties** → pestaña **Inputs**.

---

## Cómo Claude envía comandos al EA

Claude usa `/order` para encolar un comando. Ejemplo de estructura en `claude_mt5_commands.json`:

```json
{
  "commands": [
    {
      "id": "cmd_20260423_084512_01",
      "type": "place_order",
      "symbol": "BTCUSD",
      "side": "BUY_LIMIT",
      "lots": 0.01,
      "entry": 93500.0,
      "sl": 92800.0,
      "tp": 95000.0,
      "comment": "ClaudeBridge FTMO",
      "expiry_minutes": 240,
      "processed": false
    }
  ]
}
```

El EA lo detecta en el siguiente tick (máx 5s), ejecuta, y marca `processed: true` con resultado.

---

## Troubleshooting

### EA no aparece en Navigator después de compilar
- Abrir MetaEditor → compilar de nuevo (F7).
- En la pestaña **Errors**: si hay errores, no compiló.
- Presionar F5 en Navigator para refrescar.

### AutoTrading icon rojo en toolbar de MT5
- Presionar `Ctrl+E` en MT5 para activar AutoTrading.
- O click en el botón **"AutoTrading"** en la toolbar principal.
- El EA necesita que AutoTrading esté verde (ON) para ejecutar órdenes.

### mt5_state.json no se actualiza (sigue vacío o con `{}`)
1. Verificar pestaña Experts en MT5 — buscar mensajes de error del EA.
2. Verificar que `MT5_FILES_PATH` en `.env` apunta al directorio correcto.
3. En MT5: Tools → Options → Expert Advisors → verificar que "Allow algorithmic trading" está marcado.
4. Verificar que el EA está en un chart activo (icono carita feliz arriba a la derecha del chart).

### "ClaudeBridge: cannot open state tmp file"
El EA no tiene permiso de escritura en MQL5/Files/.
Solución: verificar que `MT5_FILES_PATH` existe y tiene permisos de escritura:
```bash
ls -la "$MT5_FILES_PATH"
touch "$MT5_FILES_PATH/test_write" && rm "$MT5_FILES_PATH/test_write" && echo "OK"
```

### Magic number conflict con otro EA
Si tienes otro EA con magic 77777, cambiar el input `Magic` en ClaudeBridge.
Actualizar también en `.claude/profiles/ftmo/config.md` para que Claude use el mismo magic.

### AllowExecution=false — EA no ejecuta órdenes
El kill-switch está activo. El EA solo monitorea y escribe estado, no ejecuta comandos.
Para habilitarlo: click derecho en EA en el chart → Properties → Inputs → `AllowExecution=true` → OK.

---

## Kill-switch de seguridad

Si necesitas que el EA deje de ejecutar órdenes inmediatamente:
1. Click derecho en el EA en el chart → **Properties** → **Inputs**.
2. Cambiar `AllowExecution` a `false` → **OK**.

El EA seguirá corriendo y escribiendo estado, pero ignorará todos los comandos pendientes.

---

## Desinstalar

```bash
# Eliminar EA del chart: click derecho en chart → Expert Advisors → Remove
# Eliminar symlinks:
rm .claude/profiles/ftmo/memory/mt5_state.json
rm .claude/profiles/ftmo/memory/mt5_commands.json
# Los archivos originales en MQL5/Files/ se pueden borrar manualmente desde MT5 o el Finder.
```

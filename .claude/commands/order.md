Encola una orden para FTMO. Escribe a la cola de commands del EA si está vivo, o a manual_pending si no.

Uso:
- `/order` — deriva params del último análisis del día (memoria de sesión o último setup en /morning)
- `/order BTCUSD LONG 77538 sl=77238 tp=78288 lots=0.07` — override explícito

Pasos que ejecuta Claude:

1. Lee profile activo. Si ≠ "ftmo" → ERROR "Solo FTMO. Usa /profile ftmo"

2. Carga params:
   - Sin args: busca en contexto conversacional el último setup (/morning output, /validate veredicto)
   - Con args: parsea la línea. Valida símbolo, side (LONG/SHORT → BUY_LIMIT/SELL_LIMIT si no es inmediato), entry, sl, tp, lots

3. Guardian check:
   `python3 .claude/scripts/guardian.py --profile ftmo --action check-entry --asset <SYMBOL> --entry <E> --sl <SL> --loss-if-sl <calc>`
   - Si BLOCK_HARD → abort: "Guardian BLOCK: <reason>. Override: escribir OVERRIDE GUARDIAN"
   - Si BLOCK_SIZE → aplica size_adjustment automático
   - Si OK / OK_WITH_WARN → continúa

4. **Confirmación obligatoria:**
   Muestra preview con ASCII box (params + guardian verdict + risk USD). Pide al usuario responder literal `YES` para proceder. Cualquier otra respuesta aborta sin escribir.

5. Si YES:
   a. Genera id con `python3 scripts/mt5_bridge.py next-cmd-id` (o calcula en Python inline)
   b. Append a `.claude/profiles/ftmo/memory/pending_orders.json`:
      ```json
      { "id": "...", "symbol": "...", "setup": "...", "proposed_at": "<iso>",
        "entry": ..., "sl": ..., "tp1": ..., "lots": ..., "status": "queued",
        "guardian_verdict": "OK", "filters_passed": <n> }
      ```
   c. Detect EA: `python3 .claude/scripts/mt5_bridge.py ea-status`. Si output contiene "✓" → EA vivo.
   d. Si EA vivo:
      - Append command a mt5_commands.json: `python3 scripts/mt5_bridge.py append-command <json>`
      - Update pending status → "sent_to_ea"
      - Espera 10s (sleep), re-lee mt5_commands.json, verifica `processed: true` y `result.ok`
      - Si ok → status = sent_to_ea (stays hasta que matchee posición en próximo /sync)
      - Si error → status = ea_error, mostrar result.error
   e. Si EA offline:
      - status = "manual_pending"
      - Display ASCII box con params para copiar a MT5 manual

6. Output formal:
```
╔══════════════════════════════════════╗
║  ORDEN ENCOLADA [<status>]           ║
║  ID: <id>                            ║
║  Símbolo:  <SYMBOL>                  ║
║  Tipo:     <SIDE>                    ║
║  Entry:    <E>                       ║
║  SL:       <SL>  (<pct>)             ║
║  TP:       <TP>  (<pct>)             ║
║  Lots:     <L>                       ║
║  Risk:     $<calc>  (<pct> equity)   ║
║  Magic:    77777                     ║
║  Guardian: <verdict>                 ║
╚══════════════════════════════════════╝
```

Si manual_pending, agregar: `⚠️ EA OFFLINE — copia a MT5 manualmente`

7. Al final, actualiza pending_orders.json a disco (update status final).

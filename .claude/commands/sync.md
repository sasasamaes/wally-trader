Sincroniza pending_orders.json con mt5_state.json. Marca fills y expirations.

Pasos:
1. Verifica profile==ftmo
2. Lee state y pending
3. match_pending_to_positions(pending, state.positions):
   - Por cada match → pending[i].status = "filled", agregar ticket MT5
4. Por cada pending con proposed_at + expiry_minutes < now:
   - status = "expired"
5. Save pending_orders.json
6. Output summary:
   - "X órdenes filled hoy (tickets: ...)"
   - "Y órdenes expired"
   - "Z órdenes still queued"
7. Si EA offline > 1h: Pide al usuario "Pega output de MT5 Terminal → Trade + History → lo parseo con regex y actualizo mt5_state.json manualmente con source=manual_paste"

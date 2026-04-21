---
name: Entry rules — ajustes tras fakeout real
description: Reglas de filtrado para evitar bull/bear traps en breakouts Donchian
type: feedback
originSessionId: 870cfb36-0066-4b6c-a1b7-eeaebc9a6ca8
---
**Reglas obligatorias antes de entrar a un breakout Donchian:**

1. **CIERRE de vela 15m** fuera de la zona Donchian — wicks/mechas NO cuentan como señal
2. **Buffer de confirmación: close debe estar ≥30 pts fuera del nivel** (ej: nivel 75,530 → entrada válida solo si close > 75,560). Roce de 0.1-5 pts NO es ruptura
3. **Filtro de volumen: vela breakout debe tener volumen > 300 BTC** (≈2x promedio en 15m). Volumen bajo = trampa probable
4. Entrada: apertura de la vela 15m siguiente al cierre que rompió
5. Colocar SL y 3 TPs inmediatamente en la plataforma al abrir posición

**Why:** El 2026-04-20 MX 08:30 una vela 15m cerró en 75,530.7 — apenas 0.7 puntos arriba del nivel Donchian 75,530. Técnicamente cumplió "close > 75,530" pero en la práctica fue un fakeout clásico: la vela siguiente cayó 300 pts inmediatamente y tocó el SL. Sin buffer, la regla genera entradas en noise.

**How to apply:** Cuando el usuario pregunte "¿entró ya?" o "¿dio entrada?", verificar no solo que el close esté fuera del nivel sino también que:
- Esté al menos 30 pts (≈0.04%) fuera
- El volumen de esa vela sea >300 BTC
Si ambos se cumplen → señal válida. Si uno falla → señal rechazada, seguir esperando.

**Example:**
- close 75,530.7 con vol 580 BTC → REJECT (solo 0.7 pts de buffer, aunque volumen ok)
- close 75,580 con vol 450 BTC → VALID
- close 75,620 con vol 180 BTC → REJECT (volumen insuficiente)

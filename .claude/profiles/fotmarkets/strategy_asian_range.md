# Fotmarkets — Asian Range (Secondary Strategy)

> ⛔ **Estado actualizado 2026-05-12: DISCARD** — backtest 60d EURUSD 5m demostró
> WR 32% / PF 0.83 / Total return -2.62% / 0% TPs hit. Ver
> `docs/backtest_findings_2026-05-12_asian_range_eurusd.md`.
>
> **Causa raíz estructural:** la ventana fotmarkets (CR 07:00–10:55 = UTC 13:00–16:55)
> es **NY open**, no London open. Los grabs reales ocurren UTC 08:00–11:00
> (CR 02:00–05:00) — fuera del horario operativo del trader. Por la 13:00 UTC,
> el grab de Londres ya está resuelto y el TP opuesto del rango es inalcanzable
> dentro de la ventana operativa.
>
> **Acción:** NO operar esta estrategia en fotmarkets. Mantener el doc como
> referencia y por si en el futuro se prueba en una ventana operativa diferente
> (ej. profile dedicado madrugador CR 02:00–05:00).
>
> Lo que sigue son las reglas teóricas originales — útiles si algún día se
> retoma con ventana London-open.

---

> Estado original: **secondary** (informativa). Primary strategy del profile sigue siendo
> Fotmarkets-Micro 5m (ver `strategy.md`).

## Tesis

Durante la sesión asiática (UTC 23:00-08:00 ≈ CR 17:00-02:00), pares forex mayores
(EURUSD, GBPUSD) se mueven en rango estrecho. Los stops del retail se acumulan justo
fuera de ese rango. La apertura de Londres frecuentemente *barre* uno de los extremos
y luego revierte — patrón ICT clásico de liquidity grab.

## Reglas

| Parámetro | Valor |
|---|---|
| Asset | EURUSD (primary), GBPUSD (secondary) |
| TF | 5m |
| Sesión Asia | UTC 23:00 – 08:00 (CR 17:00 – 02:00) |
| Sesión Londres | UTC 08:00 – 13:00 (CR 02:00 – 07:00); ventana fotmarkets CR 07:00-11:00 = London/NY overlap |
| Entry | Market en confirmación de grab (cierre de vuelta dentro del rango en ≤ 4 velas tras break) |
| SL | Sweep extreme + 2 pips buffer |
| TP | Lado opuesto del rango asiático |
| R:R mínimo | 1.5:1 (gate dinámico de `/min_rr_gate` decide caso por caso) |
| Risk | Mismo que primary (fase-aware: 10% / 5% / 2%) |
| Frecuencia | 0-1 setup/día (no siempre hay grab limpio) |
| Macro gate | OBLIGATORIO — si `macro_gate --check-tier` retorna HARD/WARN, no operar |

## Conflicto con Fotmarkets-Micro

Si en la misma vela aparece setup primary (Micro) y secondary (Asian Range) en
direcciones distintas → prioridad **primary**. No abrir ambas.

Si son misma dirección → entrar **una sola posición** con la mejor R:R proyectada.

## Backtest result (2026-05-12)

| Metric | Value | Threshold | Verdict |
|---|---|---|---|
| Trades | 25 | ≥ 10 needed | OK sample |
| WR | 32.0% | ≥ 45% | ❌ |
| PF | 0.827 | ≥ 1.2 | ❌ |
| Total return | -2.62% | > 0 | ❌ |
| Max DD | 8.26% | ≤ 12% | ✅ |
| Sharpe | -1.273 | > 0 | ❌ |
| TP hit ratio | 0% | > 50% | ❌ critical |
| OOS verdict | PASS (no overfit, just consistently losing) | — | — |

**Final:** DISCARD. No es problema de muestra ni de overfit — es problema estructural
de timing de ventana. Ver `docs/backtest_findings_2026-05-12_asian_range_eurusd.md`.

## Fuente

- Design doc: `docs/superpowers/specs/2026-05-12-youtube-improvements-bundle-design.md`
- Plan: `docs/superpowers/plans/2026-05-12-youtube-improvements-bundle.md` (Task 6)
- Origen del concepto: V3 Alex Ruiz — "Esta es la estrategia que seguiría si solo tuviera $100"

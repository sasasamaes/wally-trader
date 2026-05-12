# Fotmarkets — Asian Range (Secondary Strategy)

> Estado: **secondary** (informativa). Primary strategy del profile sigue siendo
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

## Estado pendiente de validación

No backtested aún en data histórica fotmarkets. Tratar como sandbox manual hasta acumular
≥ 10 trades con outcome registrado en `memory/trading_log.md`.

## Fuente

- Design doc: `docs/superpowers/specs/2026-05-12-youtube-improvements-bundle-design.md`
- Plan: `docs/superpowers/plans/2026-05-12-youtube-improvements-bundle.md` (Task 6)
- Origen del concepto: V3 Alex Ruiz — "Esta es la estrategia que seguiría si solo tuviera $100"

---
name: punkchainer-glossary
description: Use cuando necesites decodificar términos del glosario SMC/ICT + lenguaje exclusivo de la comunidad punkchainer's. Crítico para entender señales de Discord (especialmente perfil bitunix copy-validated). Incluye términos operativos comunes (BOS, ChoCH, OB, FVG, BSL/SSL, OTE, sweep) Y términos exclusivos de la comunidad como DUREX (mover SL a BE en TP1) y GORRAS (filtro anti-fake gurus).
---

# Glosario punkchainer's — términos comunidad

> Diccionario operativo + términos exclusivos. Crítico para profile bitunix (copy-validated trading) — sin entender el lenguaje de las señales, no puedes validarlas.

## 🛡 DUREX (Mandamiento OPERATIVO punkchainer)

**Verbo / Acción obligatoria.**

**Definición:**
Mover el Stop Loss al punto de entrada (**Break Even**) en el momento EXACTO en que la operación alcanza:
- **20% de recorrido a favor**, O
- **Primer objetivo parcial (TP1)**

Lo primero que ocurra.

**Filosofía oficial:**
> *"Sin globitos no hay fiesta. La prioridad número uno no es ganar dinero, es no perderlo. Proteger el capital es el único camino a la rentabilidad."*

**Implementación en el sistema:**

```
Cuando trade abierto alcanza:
  - 20% de la distancia al TP1, O
  - TP1 hit (cierre 40-50% según strategy)

→ Mover SL a precio de entrada (BE)
→ El trade ya NO PUEDE perder, máximo termina en BE+spread
```

**Aplicable a:**
- Profile **bitunix** (regla obligatoria al copiar señales)
- Profile **retail** (recomendado, alineado con regla de "TP1 → SL a BE" del strategy)
- Profile **fundingpips/ftmo** (crítico — protege capital de challenge)
- Profile **quantfury** (protege BTC stack)

**Cómo trackear:** después de ejecutar entry, anotar precio entry. Cuando precio se mueve 20% hacia TP o toca TP1 → ejecutar acción manual de mover SL a BE en el broker.

## 🧢 GORRAS (Filtro anti-fake)

**Sustantivo / Adjetivo despectivo.**

**Definición:**
Farsantes, estafadores o "vendehumos" en redes sociales fingiendo ser traders exitosos. Se caracterizan por:
- Coches de lujo alquilados
- Fajos de billetes en cámara
- Promesas de rentabilidad imposibles
- **Nunca muestran historial auditado**
- **Nunca operan en vivo**

**Filtro mental:**
> *"Cuidado con ese canal, huele a Gorras."*

**Aplicable al sistema:** cuando alguien externo (no la comunidad punkchainer's) te ofrece señales/curso/grupo:
- ¿Tiene historial auditado público? Si NO → **GORRAS**
- ¿Opera en vivo con su capital? Si NO → **GORRAS**
- ¿Promete % imposibles? (>20% mensual sostenido) → **GORRAS**

Por contraste, la comunidad punkchainer's expone sus señales en Discord en tiempo real, con resultados (winners y losers) — esto es **NO-Gorras**.

## Glosario operativo SMC/ICT (referencia rápida)

### Estructura de mercado
| Término | Definición |
|---|---|
| **BOS** (Break of Structure) | Rompimiento que confirma continuidad de tendencia |
| **ChoCH** (Change of Character) | Primer rompimiento que señala posible reversión |
| **HH** (Higher High) | Pico más alto que el anterior (tendencia alcista) |
| **HL** (Higher Low) | Valle más alto que el anterior (alcista) |
| **LH** (Lower High) | Pico más bajo que el anterior (bajista) |
| **LL** (Lower Low) | Valle más bajo que el anterior (bajista) |
| **MTF** | Multi-Timeframe Analysis |

### Zonas de reacción
| Término | Definición |
|---|---|
| **OB** (Order Block) | Última vela contraria antes de movimiento fuerte que rompe estructura |
| **Breaker Block** | OB que falló y fue roto — al regresar, actúa como S/R inverso |
| **FVG** (Fair Value Gap) | Brecha/ineficiencia de precio que actúa como imán |
| **iFVG** (inverted FVG) | FVG mitigado que actúa como nivel inverso |
| **Demand Zone** | Área donde compradores superan vendedores |
| **Supply Zone** | Área donde vendedores superan compradores |

### Liquidez
| Término | Definición |
|---|---|
| **BSL** (Buy Side Liquidity) | Stops de shorts arriba de máximos — el mercado los caza |
| **SSL** (Sell Side Liquidity) | Stops de longs debajo de mínimos — el mercado los caza |
| **Sweep** | Acción rápida de tomar liquidez (sacar stops) con mecha y regresar |
| **Liquidity Run** | Movimiento dirigido a tomar liquidez específica |
| **Trendline Liquidity** | Stops acumulados detrás de trendlines obvias |

### Power of 3 (AMD)
| Fase | Significado |
|---|---|
| **A** Accumulation | Smart money compra discretamente (rango lateral) |
| **M** Manipulation | Movimiento falso para cazar stops retail |
| **D** Distribution | Movimiento real en dirección opuesta a la manipulation |

### Premium / Discount / Equilibrium
| Término | Definición | Acción institucional |
|---|---|---|
| **Premium** | Zona >50% del rango | INSTITUCIONES VENDEN |
| **Equilibrium** (EQ) | Punto medio 50% | Recalibración |
| **Discount** | Zona <50% del rango | INSTITUCIONES COMPRAN |

### Patrones especiales
| Término | Definición |
|---|---|
| **SFP** (Swing Failure Pattern) | Precio rompe un swing pero cierra dentro del rango previo (señal reversión fuerte) |
| **OTE** (Optimal Trade Entry) | Fibonacci 62%-79% retracement |
| **Inducement** (IDM) | Trampa cerca de POI real para inducir entradas prematuras |
| **V-Shape Reversal** | Caída precipitada + recuperación rápida sin acumulación |
| **Pinbar** | Vela con cuerpo pequeño + mecha larga (rechazo fuerte) |
| **Doji** | Cuerpo inexistente, indecisión total |
| **Inside Bar** | Vela dentro del rango de la anterior (compresión vol) |

### Sesiones / killzones
| Término | Definición |
|---|---|
| **Asian Range** | Sesión Tokio, generalmente lateral, establece liquidez |
| **Killzone** | Ventanas overlap (London/NY) — alta volatilidad |
| **London Open** | 02:00-05:00 EST (CR 00:00-03:00, fuera de ventana retail) |
| **NY Open** | 08:00-11:00 EST (CR 06:00-09:00, ventana óptima) |
| **NY/London overlap** | 08:00-12:00 EST (CR 06:00-10:00, mejor sesión) |

### Conceptos operativos
| Término | Definición |
|---|---|
| **POI** (Point of Interest) | Cualquier nivel clave donde se espera reacción |
| **Daily Bias** | Dirección probable del día basada en HTF |
| **Mitigation** | Precio regresa a OB/FVG para cerrar órdenes pendientes |
| **Manipulation** | Movimiento falso para activar SL retail |
| **Smart Money** | Grandes participantes (bancos, hedge funds, instituciones) |
| **Order Flow** | Flujo neto de órdenes institucionales |
| **High Resistance Liquidity Run** | Movimiento lento creando muchos S/R (difícil atravesar después) |
| **Institutional Candle** | Vela que captura liquidez antes de movimiento opuesto |

### Métricas / cuenta
| Término | Definición |
|---|---|
| **Balance** | Saldo total sin contar trades abiertos |
| **Equity** | Valor real con flotantes incluidos |
| **Margin** | Cantidad requerida para mantener trade abierto |
| **Drawdown** (DD) | Caída de capital desde pico hasta mínimo |
| **Slippage** | Diferencia entre precio esperado y ejecutado |
| **Spread** | Diferencia Bid-Ask (costo broker) |
| **Lotaje** / Lot Size | Volumen de la operación |
| **Position Size** | Tamaño ajustado al riesgo de la cuenta |
| **Winrate** | % operaciones ganadoras / total |
| **RR** (Risk/Reward) | Ratio beneficio esperado / riesgo asumido |

## Cómo decodificar una señal típica de PunkAlgo

Ejemplo señal: `MSTRUSDT Short 20x entry 166.57`

Con este glosario, decodificas:
- **Asset:** MSTRUSDT (perpetual de MicroStrategy en exchange con perp)
- **Side:** Short = posición de venta (ganas si baja)
- **Leverage:** 20x (tu sistema CAP a 10x — ver bitunix rules)
- **Entry:** 166.57 (precio exacto de ejecución)

Implícito en una señal punkchainer típica:
- Probablemente identificaron BOS bajista en TF mayor
- Hay un POI (OB o FVG) cerca de 166.57 que justifica el entry
- Daily bias bajista (alineado con la dirección del trade)
- Sweep o liquidity run podría haber ocurrido recientemente

**Tu validación con `/signal`** debe verificar TODOS estos elementos antes de copiar.

## Aplicación de DUREX al sistema

### En profile bitunix (rule activa):

```
Después de ejecutar trade copiado:
  1. Anota precio_entry
  2. Espera al primer evento:
     - Precio toca (entry + 0.20 × distance_a_TP1) [LONG]
     - Precio toca (entry - 0.20 × distance_a_TP1) [SHORT]
     - Precio toca TP1
  3. Mueve SL → BE (precio_entry)
  4. Trade asegurado: máximo cierra en BE
```

### Comparación filosófica con strategy retail existente:

| Concepto | Retail Mean Reversion | DUREX punkchainer's |
|---|---|---|
| Cuándo mover SL a BE | TP1 hit | TP1 hit O 20% recorrido |
| Filosofía | "TP1 → SL a BE" | "Sin globitos no hay fiesta" |
| Diferencia | Solo TP1 | Más conservador (20% O TP1) |

DUREX es **más conservador** que la regla actual del retail strategy. Recomendable adoptar también en otros profiles:
- ✅ Bitunix: obligatorio (regla comunidad)
- ⚠️ Retail: considerar adoptar (más protección)
- ⚠️ FTMO/FundingPips: considerar (extra capital protection)
- ⚠️ Quantfury: considerar (protege BTC stack)

## Para más términos completos

Ver el PDF original: `Glosario de Términos Punkchainer.pdf` (6 páginas, glosario A-Z completo).

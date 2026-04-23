# Notion MCP Integration — Setup Guide

Esta guía te permite conectar tu workspace de Notion al sistema de trading para que cada trade (retail y FTMO) se loggee automáticamente en una DB de Notion **además del `.md` local**.

**Comportamiento:**
- Sin `.env` completo → solo `.md` local (comportamiento default)
- Con `.env` completo + Notion MCP conectado → dual-write (`.md` local + row en Notion DB)

---

## Paso 1 — Crear las 2 DBs en tu Notion

### DB 1: "Trades Retail"

Crea una nueva full-page database en Notion (workspace personal o página específica). Copia este schema exacto:

| Columna | Tipo | Opciones |
|---|---|---|
| **Name** | Title | (default — usar formato: `#N <asset> <direction>`) |
| **Date** | Date | — |
| **Time MX** | Text | — |
| **Asset** | Select | BTCUSDT.P |
| **Direction** | Select | LONG, SHORT |
| **Entry** | Number | — |
| **SL** | Number | — |
| **TP1** | Number | — |
| **TP2** | Number | — |
| **TP3** | Number | — |
| **Size (BTC)** | Number | — |
| **Leverage** | Number | — |
| **Result** | Select | TP1, TP2, TP3, SL, BE, partial, open |
| **PnL $** | Number | — |
| **PnL %** | Number | — |
| **R multiple** | Number | — |
| **Filters passed** | Text | (ej: "4/4") |
| **ML score** | Number | (opcional) |
| **Sentiment** | Number | (opcional) |
| **Notes** | Text | aprendizaje del trade |

### DB 2: "Trades FTMO"

Similar a la retail pero con columnas adicionales específicas de FTMO:

| Columna | Tipo | Opciones |
|---|---|---|
| **Name** | Title | `#N <asset> <direction>` |
| **Date** | Date | — |
| **Time MX** | Text | — |
| **Asset** | Select | BTCUSD, ETHUSD, EURUSD, GBPUSD, NAS100, SPX500 |
| **Direction** | Select | LONG, SHORT |
| **Entry** | Number | — |
| **SL** | Number | — |
| **TP1** | Number | — |
| **TP2** | Number | — |
| **Lots** | Number | — |
| **Magic** | Number | (default 77777) |
| **Ticket MT5** | Number | (se llena cuando EA ejecuta) |
| **Status** | Select | queued, sent_to_ea, filled, expired, canceled, manual_pending, closed |
| **Result** | Select | TP1, TP2, SL, BE, partial, open, N/A |
| **PnL $** | Number | — |
| **PnL %** | Number | — |
| **R multiple** | Number | — |
| **Filters passed** | Text | (ej: "7/7") |
| **Guardian verdict** | Select | OK, OK_WITH_WARN, BLOCK_SIZE, BLOCK_HARD, override |
| **Equity pre** | Number | — |
| **Equity post** | Number | — |
| **Notes** | Text | — |

---

## Paso 2 — Copiar los Database IDs

Con cada DB abierta en Notion:

1. Click en `•••` (top-right) → Copy link
2. URL tiene formato: `https://notion.so/<workspace>/<DATABASE_ID>?v=<VIEW_ID>`
3. El **DATABASE_ID** es el string hex de 32 caracteres después del workspace

**Ejemplo:**
```
https://notion.so/mi-workspace/1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d?v=xxx
                                └─────── DATABASE_ID ─────────┘
```

---

## Paso 3 — Llenar `.env`

```bash
cd ~/Documents/trading
# Si ya tienes .env, solo agrega las líneas nuevas
# Si no, copia del template:
cp .claude/.env.example .claude/.env
```

Edita `.claude/.env`:

```bash
NOTION_RETAIL_DB_ID=1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d
NOTION_FTMO_DB_ID=9f8e7d6c5b4a3210fedcba9876543210
```

**Important:** `.env` está gitignored. Nunca commitees las DB IDs reales.

---

## Paso 4 — Conectar Notion MCP en Claude Code

El servidor oficial de Notion se instala via OAuth. En Claude Code:

```bash
claude mcp add notion https://mcp.notion.com/mcp
```

Esto abre OAuth flow en tu browser:
1. Login a Notion con tu cuenta
2. Autorizá acceso a las 2 DBs que creaste
3. El MCP queda conectado

**Verificar:**
```bash
claude mcp list | grep notion
# Debería mostrar: notion: https://mcp.notion.com/mcp - ✓ Connected
```

---

## Paso 5 — Verificar integración

```bash
bash .claude/scripts/statusline.sh
# Retail mode: [RETAIL] ... 📝 Notion ✓
# FTMO mode:   [FTMO $10k] ... 📝 Notion ✓
```

Si no ves `📝 Notion ✓` → revisa que el `.env` tenga ambos DB IDs y que `claude mcp list` muestre notion conectado.

Primer test manual en Claude Code:
```
/profile retail
/journal
# Claude debería mencionar: "Appending al trading_log.md + creando row en Notion DB retail"
```

Verificá en tu Notion que apareció un nuevo row.

---

## Cómo funciona (comportamiento interno)

### Detección

Al inicio de sesión (`session_start.sh`):
1. Lee `.env` y verifica si `NOTION_RETAIL_DB_ID` y `NOTION_FTMO_DB_ID` están ambos llenos
2. Si sí → setea `NOTION_ENABLED=1` en contexto + statusline muestra `📝 Notion ✓`
3. Si no → `NOTION_ENABLED=0` + statusline muestra `📝 .md only`

### Dual-write

Cuando un command necesita escribir journal/orden/trade:

```
1. Siempre: append al .md local (.claude/profiles/<profile>/memory/...)
2. Si NOTION_ENABLED=1 y Claude tiene acceso a tools mcp__notion_*:
   - Usa mcp__notion_create_page o mcp__notion_create_database_row
   - Target DB: NOTION_RETAIL_DB_ID o NOTION_FTMO_DB_ID según profile activo
   - Schema según sección anterior
3. Si Notion write falla:
   - Warning al usuario: "Notion write failed: <error>. .md local preservado."
   - NO bloquea el flujo
```

### Schema mapping

Cada campo del `.md` local tiene un equivalente en columna Notion. El command se encarga de mapear antes del write. Ejemplo para un trade retail cerrado:

```yaml
# .md local format:
**Trade #N — YYYY-MM-DD**
- Entry: 77538
- SL: 77238
- PnL: +$1.20 (+12%)
- Filters: 4/4
- Result: TP2
```

→ row Notion con columnas: Name="#N BTCUSDT.P LONG", Date=YYYY-MM-DD, Entry=77538, SL=77238, PnL $=1.20, PnL %=12, Result=TP2, Filters passed="4/4".

---

## Commands integrados

| Command | Notion behavior (si conectado) |
|---|---|
| `/journal` | Cierra trade → append a Notion DB (retail o ftmo según profile) |
| `/order` (FTMO) | Encola orden → crea row Notion con status="queued" |
| `/sync` (FTMO) | Fill detectado → update Notion row status="filled" + resultado |
| `/trades` (FTMO) | Cross-reference Notion + mt5_state para vista enriquecida |
| `/challenge` (FTMO) | Agregados usan Notion DB como source of truth opcional |

---

## Troubleshooting

### Statusline no muestra "📝 Notion ✓"

1. Verifica `.env`:
   ```bash
   grep NOTION .claude/.env
   ```
   Ambos `NOTION_RETAIL_DB_ID` y `NOTION_FTMO_DB_ID` deben tener valores (no vacíos).

2. Verifica MCP:
   ```bash
   claude mcp list
   ```
   notion debe aparecer y decir "✓ Connected".

### Notion write falla con error 404

- DB ID incorrecto — verifica que copiaste el hash de 32 chars correcto
- El MCP no tiene permiso a esa DB — re-autorizá en OAuth: `claude mcp remove notion && claude mcp add notion https://mcp.notion.com/mcp`

### Notion write falla con error 429 (rate limit)

Notion tiene rate limit de 3 req/seg. Improbable en uso normal pero posible con backtests masivos. Claude retry automático 1 vez con 2s delay. Si persiste, write solo al .md y reporta warning.

### Quiero desactivar Notion temporalmente

```bash
# Comenta las líneas en .env:
# NOTION_RETAIL_DB_ID=...
# NOTION_FTMO_DB_ID=...
```

O deja vacíos (`NOTION_RETAIL_DB_ID=`). Sistema vuelve a `.md only`.

### Quiero migrar mi trading_log.md a Notion retroactivamente

El sistema no hace import masivo automático. Opciones:

1. **Manual:** abrir `.md`, copiar trade por trade a Notion (tedioso pero preciso)
2. **Script custom:** pedir a Claude que escriba uno: "parse .claude/profiles/retail/memory/trading_log.md y create rows en Notion DB <ID>"
3. **Dejar pasado en .md solo:** desde hoy todo va a Notion también, historia vieja queda en .md exclusivamente

---

## ¿Por qué dual-write y no solo Notion?

- **Redundancia:** Notion down → .md siempre funciona
- **Offline:** analizas sin internet con .md
- **Fast search:** grep en .md es instant, Notion API tiene latencia
- **Versionado:** .md vive en git, cada cambio queda trazado; Notion no tiene git
- **Portabilidad:** si cambias de Notion a otra herramienta, .md está listo
- **AI context:** Claude puede leer .md directamente en memoria; Notion requiere MCP round-trip

La combinación da: single source of truth (`.md` en git) + query/dashboard UX (Notion).

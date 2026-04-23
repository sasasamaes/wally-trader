# 🧠 Memoria persistente del sistema

Esta es la memoria oficial de **Wally Trader** — toda la información que Claude recuerda entre sesiones.

## 🔄 Cómo funciona la sincronización

**Claude lee memoria desde:**
```
~/.claude/projects/<project-path-encoded>/memory/
```

**Esta carpeta en el repo es la fuente de verdad** — backup + versionamiento de toda la memoria.

### Para sincronizar (de repo → Claude):

```bash
# Desde el root del proyecto:
./.claude/scripts/sync_memory.sh push
```

### Para backup (de Claude → repo):

```bash
./.claude/scripts/sync_memory.sh pull
```

## 📋 Archivos de memoria

| Archivo | Tipo | Contenido |
|---|---|---|
| `MEMORY.md` | index | Índice de todas las memorias |
| `user_profile.md` | user | Perfil del trader (capital, exchange, TV plan) |
| `user_goals_reality.md` | user | Objetivos vs realidad de trading |
| `trading_strategy.md` | project | Config de estrategia activa (Mean Reversion) |
| `market_regime.md` | project | Cómo detectar régimen + cuándo cambiar estrategia |
| `morning_protocol.md` | project | Protocolo 17 fases para análisis matutino |
| `trading_log.md` | project | Historial de trades ejecutados |
| `entry_rules.md` | feedback | Reglas de filtros + lecciones (ej: buffer 30pts) |
| `backtest_findings.md` | project | Resultados de backtests + limitaciones de data |
| `tradingview_setup.md` | reference | Setup de TV + workarounds de bugs MCP |
| `market_context_refs.md` | reference | APIs públicas que funcionan (F&G, OKX, etc.) |
| `communication_prefs.md` | feedback | Idioma, tono, formato preferido |

## 💡 Cuándo actualizar

**Automático (via Claude):**
- Después de cada trade → `trading_log.md` se actualiza
- Al detectar patrón en journal → se crea/actualiza feedback memory
- Al aprender algo nuevo sobre el usuario → se actualiza profile

**Manual (vía git):**
- Cuando cambies de máquina → clone + sync push
- Backup periódico → sync pull + commit
- Para compartir el sistema → el repo ya lo tiene

## ⚠️ Consideración importante

Las memorias pueden **divergir** entre las dos ubicaciones:
- Claude escribe en `~/.claude/projects/...`
- Tú lees/editas en el repo

**Solución:** usar `sync_memory.sh pull` antes de cada commit para asegurar que el repo tiene la versión más reciente de Claude.

## 🗂️ Estructura de una memoria

Cada archivo tiene frontmatter YAML + contenido:

```markdown
---
name: Nombre descriptivo
description: Cuándo/para qué se usa esta memoria
type: user | feedback | project | reference
---

Contenido de la memoria.

Para tipo `feedback` o `project`, incluir estructura:
- **Why:** razón por la que se guarda (incidente, preferencia)
- **How to apply:** cuándo y cómo usar esta info en el futuro
```

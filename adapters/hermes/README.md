# Hermes adapter (v1 — soporte total)

Genera `.hermes/skills/` desde `system/` para que [Hermes Agent (NousResearch)](https://github.com/NousResearch/hermes-agent) cargue el sistema Wally Trader como skills nativos.

## Conceptual mapping

Hermes NO tiene "subagents" ni "slash commands" como filesystem entries. Todo se proyecta como **skills** (estándar [agentskills.io](https://agentskills.io)):

| Source CC entity | Hermes destination | Slash invocation |
|---|---|---|
| `system/agents/<name>.md` | `.hermes/skills/wally-agents/<name>/SKILL.md` | activated by description match |
| `system/commands/<name>.md` | `.hermes/skills/wally-commands/<name>/SKILL.md` | `/<name>` (skill name = trigger) |
| `system/skills/<name>/` | `.hermes/skills/wally-skills/<name>/` (symlink) | activated by description match |
| `AGENTS.md` (root) | (no copy needed — Hermes reads it natively) | — |
| `CLAUDE.md` (root) | (no copy needed — Hermes reads it as fallback context) | — |

## Primera vez

```bash
bash adapters/hermes/install.sh
```

Hace:
1. Genera `.hermes/skills/wally-agents/` (12 skills desde agents)
2. Genera `.hermes/skills/wally-commands/` (29 skills desde commands)
3. Symlinks `.hermes/skills/wally-skills/ → ../../system/skills` (passthrough, 14 skills sin transformar)
4. Si Hermes está instalado (`~/.hermes/` existe): symlinks `~/.hermes/skills/wally-trader/ → <repo>/.hermes/skills/`
5. Instala git pre-commit hook v1 (auto-sync futuro)

## Auto-sync via git hook

Cada commit que toca `system/commands/` o `system/agents/` regenera `.hermes/skills/` y lo agrega al mismo commit. Sin overhead manual.

## MCP TradingView (opcional)

El schema exacto de MCP en `~/.hermes/config.yaml` no está completamente documentado en upstream. Hermes soporta MCP pero la configuración se hace vía CLI:

```bash
hermes config set mcp.tradingview.command node
hermes config set mcp.tradingview.args '["./tradingview-mcp/src/server.js"]'
hermes config set mcp.tradingview.cwd /Users/josecampos/Documents/wally-trader
```

O via el wizard `hermes setup` que pregunta por servers MCP interactivamente.

## Translations aplicadas

### Agents → Skills (`wally-agents/`)
- `name`, `description` → preservados
- `tools: A, B, C` (CC) → `metadata.hermes.requires_toolsets: [terminal, mcp, web, subagents]` (Hermes) según mapeo:
  - `mcp__*` → `mcp`
  - `WebFetch`, `WebSearch` → `web`
  - `Agent` → `subagents`
  - default siempre incluye `terminal`
- Body preservado con header de provenance (HTML comments)

### Commands → Skills (`wally-commands/`)
- `description` → preservado
- `argument-hint: <args>` → embebido como `<!-- args: <args> -->` en el body
- `allowed-tools` → descartado (Hermes resuelve tools dinámico)
- Filename → skill name → slash trigger (`morning.md` → `/morning`)
- Body preservado con header de provenance + nota de invocación

### Skills (`wally-skills/`)
- Symlink directo a `system/skills/` — formato agentskills.io ya compatible
- Zero translation
- Soporta refresh inmediato cuando edita `system/skills/`

## Tests

```bash
python3 -m pytest adapters/hermes/test_transform.py -v
```

12 tests cubren:
- agent → skill frontmatter (basic, MCP toolset, web toolset, subagents toolset, no-tools default)
- agent body preservation con provenance header
- command → skill (basic, argument-hint, slash naming, no-frontmatter)
- clean_group (orphan removal, missing-dir no-op)

## Troubleshooting

- `.hermes/skills/` stale después de edit: `bash adapters/hermes/install.sh` regenera
- Git hook no triggerea: verifica `ls .git/hooks/pre-commit` existe y tiene marker `hermes-adapter-v1`
- PyYAML not found: `pip3 install pyyaml`
- Hermes no encuentra skills: verifica que `~/.hermes/skills/wally-trader/` es symlink válido a `<repo>/.hermes/skills/`
- Skill no aparece en `/skills`: verifica que `SKILL.md` tiene frontmatter válido (yaml syntax)

## Diferencias Hermes vs OpenCode vs Claude Code

| Feature | Claude Code | OpenCode | Hermes |
|---|---|---|---|
| Subagents | ✅ `.claude/agents/` | ✅ `.opencode/agents/` | ❌ — proyecta a skills |
| Slash commands | ✅ `.claude/commands/` | ✅ `.opencode/commands/` | ⚠️ proyectado a skills (works) |
| Skills | ✅ `~/.claude/skills/` | ✅ `~/.config/opencode/skills/` | ✅ `~/.hermes/skills/` (primary) |
| Cron scheduling | ❌ | ❌ | ✅ nativo (`hermes cron`) |
| Multi-platform delivery | ❌ | ❌ | ✅ Telegram/Discord/Slack/WhatsApp/Signal |
| Serverless backend | ❌ | ❌ | ✅ Modal, Daytona, SSH |
| Voice memo | ❌ | ❌ | ✅ via gateway |
| Context file | `CLAUDE.md` | `AGENTS.md` + `CLAUDE.md` | `HERMES.md` > `AGENTS.md` > `CLAUDE.md` |
| MCP | ✅ user-scope | ✅ project + user | ✅ via `hermes config set` |

# Codex adapter — ⚠️ UNTESTED

Este adapter **no ha sido validado contra un Codex CLI vivo** por falta de acceso a OpenAI API en la sesión de desarrollo.

## Supuestos del diseño (pueden estar incorrectos)

- Codex CLI stores prompts at `~/.codex/prompts/<name>.md`
- Codex no distingue entre commands y agents — todo es prompt-template
- Skills se copian como referencia (Codex no tiene skills system native)
- MCP no se traduce (Codex usa TOML, formato distinto)

## Cuando valides

1. Instala Codex: `npm install -g @openai/codex`
2. Configura API key: `codex auth login`
3. Corre adapter: `bash adapters/codex/install.sh`
4. En Codex, intenta: `/cmd_status`
5. Reporta issues para que el adapter se corrija

## Convenciones de naming

- Commands: `cmd_<name>.md` (ej: `cmd_morning.md`, invoca con `/cmd_morning`)
- Agents: `agent_<name>.md` (ej: `agent_morning-analyst-ftmo.md`)
- Skills: referencia en `~/.codex/prompts/skills_ref/<name>/`

## Diferencias vs OpenCode adapter

- No git pre-commit hook (no confiable mientras UNTESTED)
- No watch daemon
- Output a `~/.codex/` (global, no project-local)

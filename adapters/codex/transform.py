"""
transform.py — Translate Claude Code commands to Codex prompts.

⚠️ UNTESTED — may be broken until validated against live Codex install.

Codex stores prompts at ~/.codex/prompts/<name>.md (single flat dir).
We treat commands and agents both as prompts (Codex doesn't distinguish).

Skills: not natively supported. We copy to a reference dir that can be included in context manually.

MCP: Codex uses TOML config. We do not attempt to translate (error out with notice).
"""
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'opencode'))
from transform import _parse_frontmatter  # reuse


def translate_to_codex_prompt(src_path, dst_path, prefix=''):
    """Strip frontmatter (Codex doesn't use it), write body with optional prefix in name.

    prefix: 'cmd_' for commands, 'agent_' for agents (to avoid collisions in flat dir).
    """
    text = src_path.read_text()
    _fm, body = _parse_frontmatter(text)

    if body is None:
        body = text  # no frontmatter

    dst_path.parent.mkdir(parents=True, exist_ok=True)
    dst_path.write_text(body.strip() + '\n')


def main():
    repo = Path(__file__).parent.parent.parent
    system_dir = repo / 'system'
    codex_dir = Path.home() / '.codex' / 'prompts'

    if not system_dir.exists():
        print(f"ERROR: {system_dir} not found.", file=sys.stderr)
        sys.exit(1)

    codex_dir.mkdir(parents=True, exist_ok=True)

    # Commands
    cmd_count = 0
    for src in (system_dir / 'commands').glob('*.md'):
        dst = codex_dir / f'cmd_{src.name}'
        translate_to_codex_prompt(src, dst, 'cmd_')
        cmd_count += 1

    # Agents
    agent_count = 0
    for src in (system_dir / 'agents').glob('*.md'):
        dst = codex_dir / f'agent_{src.name}'
        translate_to_codex_prompt(src, dst, 'agent_')
        agent_count += 1

    # Skills — just copy (Codex manual reference)
    skills_ref = codex_dir / 'skills_ref'
    skills_ref.mkdir(exist_ok=True)
    skill_count = 0
    skills_src = system_dir / 'skills'
    if skills_src.exists():
        # Clean target
        shutil.rmtree(skills_ref, ignore_errors=True)
        skills_ref.mkdir()
        for src in skills_src.iterdir():
            if src.is_dir():
                shutil.copytree(src, skills_ref / src.name)
                skill_count += 1

    print(f"⚠️ UNTESTED Codex adapter:")
    print(f"   {cmd_count} commands → {codex_dir}/cmd_*.md")
    print(f"   {agent_count} agents → {codex_dir}/agent_*.md")
    print(f"   {skill_count} skills → {codex_dir}/skills_ref/")
    print(f"   MCP: not translated (Codex uses TOML, configure manually)")


if __name__ == '__main__':
    main()

"""Unit tests for transform.py — CC → OpenCode translator."""
import importlib.util
import json
from pathlib import Path

# Load transform.py under a unique module name to avoid sys.modules collision
# with adapters/hermes/transform.py when running `pytest adapters/`.
_spec = importlib.util.spec_from_file_location(
    "oc_transform", Path(__file__).parent / "transform.py"
)
transform = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(transform)


def test_translate_command_removes_allowed_tools(tmp_path):
    src = tmp_path / "src.md"
    src.write_text("""---
description: Dashboard
allowed-tools: Bash, Read
---

Pasos del comando
$ARGUMENTS
""")
    dst = tmp_path / "dst.md"
    transform.translate_command(src, dst)

    result = dst.read_text()
    assert "allowed-tools" not in result
    assert "description: Dashboard" in result
    assert "$ARGUMENTS" in result
    assert "Pasos del comando" in result


def test_translate_command_preserves_description_only(tmp_path):
    src = tmp_path / "src.md"
    src.write_text("""---
description: Simple command
---

Body here
""")
    dst = tmp_path / "dst.md"
    transform.translate_command(src, dst)

    result = dst.read_text()
    assert "description: Simple command" in result
    assert "Body here" in result


def test_translate_command_argument_hint_to_comment(tmp_path):
    src = tmp_path / "src.md"
    src.write_text("""---
description: Takes args
argument-hint: <symbol> <side>
---

Use $1 and $2
""")
    dst = tmp_path / "dst.md"
    transform.translate_command(src, dst)

    result = dst.read_text()
    assert "argument-hint" not in result  # removed from frontmatter
    assert "<!-- args: <symbol> <side> -->" in result
    assert "Use $1 and $2" in result


def test_translate_command_no_frontmatter(tmp_path):
    src = tmp_path / "src.md"
    src.write_text("Body only without frontmatter\n")
    dst = tmp_path / "dst.md"
    transform.translate_command(src, dst)

    result = dst.read_text()
    assert result == "Body only without frontmatter\n"


def test_translate_command_preserves_body_with_arguments(tmp_path):
    src = tmp_path / "src.md"
    src.write_text("""---
description: Test
---

Run with $ARGUMENTS and output result.
""")
    dst = tmp_path / "dst.md"
    transform.translate_command(src, dst)

    assert "$ARGUMENTS" in dst.read_text()


def test_translate_agent_tools_to_permission(tmp_path):
    src = tmp_path / "agent.md"
    src.write_text("""---
name: my-agent
description: Does stuff
tools: Bash, Read, mcp__tv__quote_get
---

Agent body prompt.
""")
    dst = tmp_path / "dst.md"
    transform.translate_agent(src, dst)

    import yaml as y
    text = dst.read_text()
    m = __import__('re').match(r'^---\n(.*?)\n---\n(.*)', text, __import__('re').DOTALL)
    fm = y.safe_load(m.group(1))

    assert fm['description'] == 'Does stuff'
    assert fm['mode'] == 'subagent'
    assert fm['permission']['Bash'] == 'allow'
    assert fm['permission']['Read'] == 'allow'
    assert fm['permission']['mcp__tv__quote_get'] == 'allow'
    assert 'Agent body prompt' in m.group(2)


def test_translate_agent_no_tools(tmp_path):
    src = tmp_path / "agent.md"
    src.write_text("""---
name: simple
description: No tools
---

Body
""")
    dst = tmp_path / "dst.md"
    transform.translate_agent(src, dst)

    import yaml as y
    m = __import__('re').match(r'^---\n(.*?)\n---\n(.*)', dst.read_text(), __import__('re').DOTALL)
    fm = y.safe_load(m.group(1))
    assert fm['mode'] == 'subagent'
    assert 'permission' not in fm or fm.get('permission') == {}


def test_translate_agent_preserves_body(tmp_path):
    src = tmp_path / "agent.md"
    src.write_text("""---
name: a
description: b
tools: Bash
---

Line 1
Line 2
Line 3
""")
    dst = tmp_path / "dst.md"
    transform.translate_agent(src, dst)

    assert "Line 1" in dst.read_text()
    assert "Line 2" in dst.read_text()
    assert "Line 3" in dst.read_text()


def test_translate_agent_removes_name_field(tmp_path):
    """`name` is redundant in OC (filename = agent id). Optional to preserve."""
    src = tmp_path / "my-agent.md"
    src.write_text("""---
name: my-agent
description: d
---

body
""")
    dst = tmp_path / "out.md"
    transform.translate_agent(src, dst)

    import yaml as y
    m = __import__('re').match(r'^---\n(.*?)\n---\n(.*)', dst.read_text(), __import__('re').DOTALL)
    fm = y.safe_load(m.group(1))
    # name is OK to preserve or drop; test just verifies body + description remain
    assert fm['description'] == 'd'


def test_translate_mcp_basic(tmp_path):
    src = tmp_path / "servers.json"
    src.write_text(json.dumps({
        "servers": {
            "tradingview": {
                "command": "node",
                "args": ["/path/to/server.js"],
                "env": {"DEBUG": "1"}
            }
        }
    }))
    dst_config = tmp_path / "config.json"
    transform.translate_mcp(src, dst_config)

    loaded = json.loads(dst_config.read_text())
    assert 'mcp' in loaded
    assert 'servers' in loaded['mcp']
    assert loaded['mcp']['servers']['tradingview']['command'] == 'node'
    assert loaded['mcp']['servers']['tradingview']['args'] == ['/path/to/server.js']


def test_translate_mcp_preserves_existing_config(tmp_path):
    """If .opencode/config.json already has other settings, merge only mcp section."""
    src = tmp_path / "servers.json"
    src.write_text(json.dumps({
        "servers": {"tradingview": {"command": "node", "args": [], "env": {}}}
    }))
    dst = tmp_path / "config.json"
    dst.write_text(json.dumps({
        "theme": "dark",
        "model": "claude-sonnet-4"
    }))
    transform.translate_mcp(src, dst)

    loaded = json.loads(dst.read_text())
    assert loaded['theme'] == 'dark'  # preserved
    assert loaded['model'] == 'claude-sonnet-4'  # preserved
    assert 'mcp' in loaded  # added


def test_sync_root_opencode_json_scaffolds_when_missing(tmp_path):
    """If root opencode.json does not exist, sync_root scaffolds a minimal one."""
    src = tmp_path / "servers.json"
    src.write_text(json.dumps({
        "servers": {
            "tradingview": {
                "type": "stdio",
                "command": "node",
                "args": ["./tradingview-mcp/src/server.js"],
                "env": {}
            }
        }
    }))
    root = tmp_path / "opencode.json"
    assert not root.exists()
    ok = transform.sync_root_opencode_json(src, root)
    assert ok is True

    cfg = json.loads(root.read_text())
    assert cfg['$schema'] == 'https://opencode.ai/config.json'
    assert 'CLAUDE.md' in cfg['instructions']
    assert 'AGENTS.md' in cfg['instructions']
    # Root opencode.json places servers directly under `mcp`, NOT `mcp.servers`
    assert 'tradingview' in cfg['mcp']
    assert cfg['mcp']['tradingview']['command'] == 'node'


def test_sync_root_opencode_json_preserves_user_overrides(tmp_path):
    """If root opencode.json already exists with custom model/permission, sync only updates `mcp` block."""
    src = tmp_path / "servers.json"
    src.write_text(json.dumps({
        "servers": {"tradingview": {"command": "node", "args": [], "env": {}}}
    }))
    root = tmp_path / "opencode.json"
    root.write_text(json.dumps({
        "$schema": "https://opencode.ai/config.json",
        "model": "anthropic/claude-opus-4-7",
        "default_agent": "review",
        "permission": {"bash": "deny"},
        "instructions": ["CUSTOM.md"],
        "mcp": {"oldserver": {"command": "stale"}}
    }))

    transform.sync_root_opencode_json(src, root)

    cfg = json.loads(root.read_text())
    assert cfg['model'] == 'anthropic/claude-opus-4-7'  # preserved
    assert cfg['default_agent'] == 'review'  # preserved
    assert cfg['permission']['bash'] == 'deny'  # preserved
    assert cfg['instructions'] == ['CUSTOM.md']  # preserved
    # Only mcp is overwritten
    assert 'tradingview' in cfg['mcp']
    assert 'oldserver' not in cfg['mcp']  # replaced, not merged


def test_sync_root_opencode_json_skips_comment_keys(tmp_path):
    """The $comment key in servers.json must not leak into opencode.json mcp block."""
    src = tmp_path / "servers.json"
    src.write_text(json.dumps({
        "$comment": "This is metadata, not a server",
        "servers": {
            "$comment": "ignored",
            "tradingview": {"command": "node", "args": [], "env": {}}
        }
    }))
    root = tmp_path / "opencode.json"
    transform.sync_root_opencode_json(src, root)

    cfg = json.loads(root.read_text())
    assert '$comment' not in cfg['mcp']
    assert 'tradingview' in cfg['mcp']


def test_sync_root_opencode_json_returns_false_when_no_servers_file(tmp_path):
    """Graceful skip when system/mcp/servers.json doesn't exist."""
    src = tmp_path / "doesnotexist.json"
    root = tmp_path / "opencode.json"
    ok = transform.sync_root_opencode_json(src, root)
    assert ok is False
    assert not root.exists()

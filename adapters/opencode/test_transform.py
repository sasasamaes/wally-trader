"""Unit tests for transform.py — CC → OpenCode translator."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import transform


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

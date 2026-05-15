"""CI canary: run docs/api/_generate_stubs.py --check.

If this fails, the engineer changed an endpoint (route/schema/status code)
without regenerating the manual. Fix:

    cd "$(git rev-parse --show-toplevel)"
    python docs/api/_generate_stubs.py
    git add docs/api/routers/
    git commit
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_docs_routers_in_sync() -> None:
    """Idempotence: running --check after a clean repo state must exit 0."""
    rc = subprocess.call(
        [sys.executable, "docs/api/_generate_stubs.py", "--check"],
        cwd=REPO_ROOT,
    )
    assert rc == 0, (
        "docs/api/routers/*.md is out of sync with the code. "
        "Run `python docs/api/_generate_stubs.py` and commit the result."
    )

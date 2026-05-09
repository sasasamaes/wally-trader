import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent / ".claude/scripts"))

# Just smoke test that the module imports OK
def test_funding_alerts_imports():
    import funding_alerts
    assert hasattr(funding_alerts, "fetch_funding_binance")

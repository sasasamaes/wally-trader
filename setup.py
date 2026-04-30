#!/usr/bin/env python3
"""Universal cross-platform installer for Wally Trader.

Detects OS (macOS/Linux/Windows) and runs the appropriate setup steps:
  1. Verifica Python 3.9+
  2. Verifica deps de sistema (git, optional: Git Bash en Windows, brew en macOS)
  3. Instala Python deps via pip
  4. Genera adapters (OpenCode + Hermes)
  5. Verifica scripts canónicos funcionan
  6. Reporta status final + next steps por OS

Usage:
  python setup.py            — interactive setup
  python setup.py --check    — just verify, don't install
  python setup.py --quick    — skip optional features (no plyer, no MT5)

Compatible:
  - macOS    (Claude Code, OpenCode, Hermes)
  - Linux    (Claude Code, OpenCode, Hermes)
  - Windows  (Claude Code, OpenCode — via Git Bash or native)
"""
import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY_DEPS_CORE = [
    "pyyaml",
    "pandas",
    "numpy",
    "yfinance",
    "requests",
    "python-dotenv",
]
PY_DEPS_ML = [
    "xgboost",
    "scikit-learn",
]
PY_DEPS_OPTIONAL = {
    "plyer": "Cross-platform desktop notifications (Windows/Linux/macOS unified)",
    "vaderSentiment": "Sentiment analysis NLP (for /sentiment command)",
}


def color(text: str, code: str) -> str:
    """ANSI color helper (no-op on Windows cmd without VT)."""
    if platform.system() == "Windows" and not os.environ.get("WT_SESSION"):
        return text
    return f"\033[{code}m{text}\033[0m"


def green(t): return color(t, "32")
def red(t): return color(t, "31")
def yellow(t): return color(t, "33")
def blue(t): return color(t, "34")
def bold(t): return color(t, "1")


def section(title: str):
    print(f"\n{bold(blue('▶'))} {bold(title)}")


def ok(msg: str): print(f"  {green('✓')} {msg}")
def warn(msg: str): print(f"  {yellow('⚠')} {msg}")
def err(msg: str): print(f"  {red('✗')} {msg}")


def check_python():
    section("Python version")
    if sys.version_info < (3, 9):
        err(f"Python {sys.version_info.major}.{sys.version_info.minor} detectado — Wally requiere Python 3.9+")
        return False
    ok(f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    return True


def check_command(cmd: str, install_hint: str = ""):
    found = shutil.which(cmd)
    if found:
        ok(f"{cmd} ({found})")
        return True
    msg = f"{cmd} no encontrado en PATH"
    if install_hint:
        msg += f" — {install_hint}"
    warn(msg)
    return False


def check_system_deps():
    section("System dependencies")
    system = platform.system()
    is_mac = system == "Darwin"
    is_linux = system == "Linux"
    is_win = system == "Windows"

    print(f"  OS: {system} ({platform.platform()})")

    check_command("git", "instalar git: https://git-scm.com")
    check_command("python3" if not is_win else "python", "ya verificado arriba")

    if is_mac:
        check_command("brew", "opcional, https://brew.sh")
        check_command("osascript", "incluido en macOS")
    elif is_linux:
        check_command("notify-send", "para notificaciones: apt install libnotify-bin")
    elif is_win:
        check_command("bash", "Git Bash: https://git-scm.com/download/win — ESENCIAL para slash commands")
        check_command("powershell", "incluido en Windows")
    return True


def install_pip_deps(deps, label: str, optional: bool = False):
    section(f"Python deps {label}")
    if not deps:
        return True

    pip_cmd = [sys.executable, "-m", "pip", "install", "--upgrade"]
    if isinstance(deps, dict):
        deps_list = list(deps.keys())
    else:
        deps_list = deps

    print(f"  Installing: {', '.join(deps_list)}")
    try:
        subprocess.run(pip_cmd + deps_list, check=True, capture_output=False)
        for d in deps_list:
            ok(d)
        return True
    except subprocess.CalledProcessError as e:
        if optional:
            warn(f"Optional deps failed (no bloqueante): {e}")
            return True
        err(f"pip install failed: {e}")
        return False


def generate_adapters():
    section("Adapters (OpenCode + Hermes)")
    adapters = [
        ("opencode", ROOT / "adapters" / "opencode" / "transform.py"),
        ("hermes",   ROOT / "adapters" / "hermes"   / "transform.py"),
    ]
    for name, path in adapters:
        if not path.exists():
            warn(f"{name} adapter not found at {path}")
            continue
        try:
            result = subprocess.run([sys.executable, str(path)], capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                ok(f"{name} synced")
            else:
                warn(f"{name} sync warnings: {result.stderr[:200]}")
        except subprocess.TimeoutExpired:
            warn(f"{name} sync timeout")
    return True


def smoke_test_canonical_scripts():
    section("Smoke test scripts canónicos")
    scripts_dir = ROOT / ".claude" / "scripts"
    tests = [
        ("profile.py",          ["get"]),
        ("fotmarkets_phase.py", ["phase"]),
        ("fx_rate.py",          []),
        ("notify.py",           ["Wally setup", "Notification test OK"]),
    ]
    for script, args in tests:
        path = scripts_dir / script
        if not path.exists():
            warn(f"{script} not found")
            continue
        try:
            result = subprocess.run(
                [sys.executable, str(path)] + args,
                capture_output=True, text=True, timeout=10
            )
            if result.returncode in (0, 1):  # 1 is OK for some (e.g. "no profile set")
                first_line = result.stdout.strip().split("\n")[0] if result.stdout else "(no output)"
                ok(f"{script}: {first_line[:60]}")
            else:
                warn(f"{script} exit code {result.returncode}: {result.stderr[:100]}")
        except subprocess.TimeoutExpired:
            warn(f"{script} timeout")
        except Exception as e:
            err(f"{script} crashed: {e}")
    return True


def print_next_steps():
    system = platform.system()
    section("Next steps")
    print(f"\n  {bold('1. Configurar TradingView Desktop')}")
    print(f"     Lanzar con --remote-debugging-port=9222 (ver README sección TradingView MCP)")
    print(f"\n  {bold('2. Switch profile inicial')}")
    print(f"     {blue('python .claude/scripts/profile.py set retail')}")
    print(f"\n  {bold('3. Lanzar tu CLI preferido')}")
    if system == "Darwin":
        print(f"     {blue('claude')}      # Claude Code (recomendado en macOS)")
        print(f"     {blue('opencode')}    # alternativa multi-CLI")
    elif system == "Linux":
        print(f"     {blue('claude')}      # Claude Code")
        print(f"     {blue('opencode')}    # OpenCode")
    else:  # Windows
        print(f"     {blue('opencode')}              # OpenCode (recomendado en Windows)")
        print(f"     {blue('claude')}                # Claude Code")
        print(f"     {yellow('Si bash falla:')} usar wrappers en .claude\\scripts\\win\\")
    print(f"\n  {bold('4. (Opcional) Setup profiles avanzados')}")
    print(f"     Ver README sección 'Setup [profile]' para FTMO/FundingPips/Fotmarkets/Bitunix/Quantfury")


def main():
    parser = argparse.ArgumentParser(description="Wally Trader — universal setup")
    parser.add_argument("--check", action="store_true", help="Solo verifica, no instala")
    parser.add_argument("--quick", action="store_true", help="Skip optional deps (plyer, vader)")
    args = parser.parse_args()

    print(bold(blue("\n╔══════════════════════════════════════╗")))
    print(bold(blue("║   Wally Trader — Universal Setup    ║")))
    print(bold(blue("╚══════════════════════════════════════╝")))

    ok_python = check_python()
    if not ok_python:
        return 1

    check_system_deps()

    if args.check:
        section("Check-only mode — skipping install")
        smoke_test_canonical_scripts()
        return 0

    if not install_pip_deps(PY_DEPS_CORE, "core"):
        return 1
    install_pip_deps(PY_DEPS_ML, "ML")
    if not args.quick:
        install_pip_deps(PY_DEPS_OPTIONAL, "optional", optional=True)

    generate_adapters()
    smoke_test_canonical_scripts()
    print_next_steps()

    print(f"\n{green(bold('✓ Setup completo'))}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

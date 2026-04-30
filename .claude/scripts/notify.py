#!/usr/bin/env python3
"""Cross-platform desktop notification — macOS / Linux / Windows.

Usage:
  python notify.py "Title" "Message" [sound_name]

Backends:
  macOS:   osascript (built-in)
  Linux:   notify-send (libnotify)
  Windows: plyer (pip install plyer) OR PowerShell BurntToast OR fallback to print

Always logs to .claude/scripts/notifications.log regardless of backend.
"""
import datetime
import platform
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
LOG_FILE = SCRIPT_DIR / "notifications.log"


def notify_macos(title: str, message: str, sound: str = "Glass") -> bool:
    if not shutil.which("osascript"):
        return False
    try:
        cmd = [
            "osascript", "-e",
            f'display notification "{message}" with title "{title}" sound name "{sound}"'
        ]
        subprocess.run(cmd, check=True, timeout=5, capture_output=True)
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False


def notify_linux(title: str, message: str) -> bool:
    if not shutil.which("notify-send"):
        return False
    try:
        subprocess.run(
            ["notify-send", title, message],
            check=True, timeout=5, capture_output=True,
        )
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False


def notify_windows(title: str, message: str) -> bool:
    # Try plyer first (cross-platform Python lib)
    try:
        from plyer import notification
        notification.notify(title=title, message=message, timeout=5)
        return True
    except (ImportError, Exception):
        pass

    # Fallback: PowerShell with BurntToast (if installed)
    try:
        ps_cmd = (
            f'New-BurntToastNotification -Text "{title}", "{message}"'
        )
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            capture_output=True, timeout=5
        )
        if result.returncode == 0:
            return True
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    # Last resort: PowerShell ballontip via System.Windows.Forms
    try:
        ps_script = f"""
Add-Type -AssemblyName System.Windows.Forms
$balloon = New-Object System.Windows.Forms.NotifyIcon
$balloon.Icon = [System.Drawing.SystemIcons]::Information
$balloon.BalloonTipTitle = "{title}"
$balloon.BalloonTipText = "{message}"
$balloon.Visible = $true
$balloon.ShowBalloonTip(5000)
Start-Sleep -Seconds 6
$balloon.Dispose()
"""
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            timeout=8, capture_output=True
        )
        return True
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return False


def log_notification(title: str, message: str, success: bool):
    """Append to notifications.log regardless of GUI success."""
    try:
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status = "" if success else " [GUI_FAIL]"
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with LOG_FILE.open("a") as f:
            f.write(f"[{ts}]{status} {title}: {message}\n")
    except OSError:
        pass


def main(argv):
    title = argv[1] if len(argv) > 1 else "Trading Alert"
    message = argv[2] if len(argv) > 2 else "Revisa el chart"
    sound = argv[3] if len(argv) > 3 else "Glass"

    system = platform.system()
    success = False

    if system == "Darwin":
        success = notify_macos(title, message, sound)
    elif system == "Linux":
        success = notify_linux(title, message)
    elif system == "Windows":
        success = notify_windows(title, message)

    # Always print + log (terminal fallback)
    if not success:
        print(f"[NOTIFY] {title}: {message}", file=sys.stderr)

    log_notification(title, message, success)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))

"""Windows shell identity for the separate Flet desktop host process."""
import os
from pathlib import Path
import subprocess
import sys

APP_ID = "Kexinglu.Desktop"
ICON_NAME = "app-lu-v1.ico"


def configure() -> None:
    if sys.platform != "win32":
        return
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    frozen = bool(getattr(sys, "frozen", False))
    os.environ["FLET_APP_USER_MODEL_ID"] = APP_ID if frozen else APP_ID + ".Dev"
    os.environ["FLET_APP_RELAUNCH_DISPLAY_NAME"] = "客行录"
    os.environ["FLET_APP_RELAUNCH_ICON"] = str(root / "assets" / ICON_NAME) + ",0"
    command = [sys.executable] if frozen else [sys.executable, str(root / "main.py")]
    os.environ["FLET_APP_RELAUNCH_COMMAND"] = subprocess.list2cmdline(command)


configure()

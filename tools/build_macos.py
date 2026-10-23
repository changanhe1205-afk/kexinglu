"""Build an unsigned Mac evaluation bundle on a macOS runner."""
import os, platform, subprocess, sys
from pathlib import Path
if sys.platform != "darwin":
    raise SystemExit("Run on macOS; Windows cannot build this bundle")
root = Path(__file__).resolve().parents[1]
os.chdir(root)
import flet_desktop
host = flet_desktop.ensure_client_cached()
subprocess.run([sys.executable, "-m", "PyInstaller", "main.py", "--name=Kexinglu", "--windowed", "--noconfirm", "--clean", "--osx-bundle-identifier=com.changanhe.kexinglu", "--runtime-hook=packaged_startup.py", "--add-data=assets:assets", f"--add-data={host}:flet_desktop/app", "--collect-all=flet", "--collect-all=flet_desktop", "--collect-all=PIL", "--collect-all=pypinyin", "--collect-all=certifi"], check=True)
app = root/"dist/Kexinglu.app"
assert app.is_dir()
subprocess.run(["ditto", "-c", "-k", "--sequesterRsrc", "--keepParent", str(app), str(root/f"dist/Kexinglu-macOS-1.0.0-{platform.machine()}-unsigned.zip")], check=True)

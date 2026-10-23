"""Build an unsigned Mac evaluation bundle on a macOS runner."""
import os, platform, subprocess, sys, shutil
from pathlib import Path
if sys.platform != "darwin":
    raise SystemExit("Run on macOS; Windows cannot build this bundle")
root = Path(__file__).resolve().parents[1]
os.chdir(root)
import flet_desktop
host = flet_desktop.ensure_client_cached()
# Keep the original nested application out of PyInstaller's binary rewriting.
# Restore its complete framework layout after the outer Python app is built.
cache_app = host / "Flet.app"
assert cache_app.is_dir(), cache_app
saved = root / "build/macos-native-client/Flet.app"
saved.parent.mkdir(parents=True, exist_ok=True)
if saved.exists(): shutil.rmtree(saved)
shutil.copytree(cache_app, saved, symlinks=True)
shutil.rmtree(cache_app)
subprocess.run([sys.executable, "-m", "PyInstaller", "main.py", "--name=Kexinglu", "--windowed", "--noconfirm", "--clean", "--osx-bundle-identifier=com.changanhe.kexinglu", "--runtime-hook=packaged_startup.py", "--add-data=assets:assets", "--collect-all=flet", "--collect-all=flet_desktop", "--collect-all=PIL", "--collect-all=pypinyin", "--collect-all=certifi"], check=True)
app = root/"dist/Kexinglu.app"
assert app.is_dir()
native = app/"Contents/Resources/flet_desktop/app/Flet.app"
native.parent.mkdir(parents=True, exist_ok=True)
shutil.copytree(saved, native, symlinks=True)
subprocess.run(["codesign", "--force", "--deep", "--sign", "-", str(app)], check=True)
subprocess.run(["codesign", "--verify", "--deep", "--strict", str(app)], check=True)
subprocess.run(["ditto", "-c", "-k", "--sequesterRsrc", "--keepParent", str(app), str(root/f"dist/Kexinglu-macOS-1.0.0-{platform.machine()}-unsigned.zip")], check=True)

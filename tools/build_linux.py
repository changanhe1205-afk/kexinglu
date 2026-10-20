"""Build a self-contained Linux host; run only on Ubuntu 22.04 x64."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
if sys.platform != 'linux':
    raise SystemExit('Linux packages must be built on Linux')
import flet_desktop
host = flet_desktop.ensure_client_cached() / 'flet'
assert (host/'flet').is_file(), host
subprocess.run([sys.executable, '-m', 'PyInstaller', 'main.py', '--name=kexinglu',
    '--noconfirm', '--clean', '--runtime-hook=packaged_startup.py',
    '--add-data=assets:assets', f'--add-data={host}:flet_desktop/app/flet',
    '--collect-all=flet', '--collect-all=flet_desktop', '--collect-all=PIL',
    '--collect-all=pypinyin', '--collect-all=certifi'], check=True)
bundle = ROOT/'dist/kexinglu'
shutil.copy(ROOT/'assets/app.png', bundle/'kexinglu.png')
(bundle/'README.txt').write_text('Waylore / 客行录 1.0.0\nUbuntu 22.04+ x64\nRun ./kexinglu\nData: ~/.local/share/kexinglu\nSettings: ~/.config/kexinglu\n',encoding='utf-8')
with tarfile.open(ROOT/'dist/Kexinglu-Linux-1.0.0-x86_64.tar.gz','w:gz') as archive:
    archive.add(bundle,arcname='kexinglu')
deb = ROOT/'build/linux-deb'
shutil.copytree(bundle,deb/'opt/kexinglu',dirs_exist_ok=True)
(deb/'DEBIAN').mkdir(parents=True,exist_ok=True)
(deb/'DEBIAN/control').write_text('Package: kexinglu\nVersion: 1.0.0\nArchitecture: amd64\nMaintainer: Kexinglu contributors\nDepends: libgtk-3-0, libstdc++6, libsecret-1-0, libayatana-appindicator3-1, libgl1, libegl1, libgles2, xdg-utils\nSection: utils\nPriority: optional\nDescription: Waylore travel journals and memories\n')
apps=deb/'usr/share/applications';apps.mkdir(parents=True,exist_ok=True)
(apps/'kexinglu.desktop').write_text('[Desktop Entry]\nType=Application\nName=Waylore\nName[zh_CN]=客行录\nExec=/opt/kexinglu/kexinglu\nIcon=/opt/kexinglu/kexinglu.png\nTerminal=false\nCategories=Office;Utility;\nStartupWMClass=flet\n',encoding='utf-8')
subprocess.run(['dpkg-deb','--build','--root-owner-group',str(deb),'dist/Kexinglu-Linux-1.0.0-amd64.deb'],check=True)

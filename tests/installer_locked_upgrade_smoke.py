"""Reproduce a locked Python ZIP without touching the user's installation."""
import ctypes
from ctypes import wintypes
from pathlib import Path
import subprocess
import tempfile
import uuid
import re
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from release_integrity import verify_manifest
from app_version import VERSION

with tempfile.TemporaryDirectory(prefix='locked-upgrade-',dir=ROOT/'design/verification') as folder:
    temp=Path(folder);dest=temp/'installed'
    source=(ROOT/'installer.iss').read_text(encoding='utf-8-sig')
    source=re.sub(r'AppId=.*','AppId={{'+str(uuid.uuid4())+'}',source)
    source=source.replace('SourcePath + "\\dist\\installer"','"'+str(temp)+'"')
    source=source.replace('SourcePath + "\\dist\\客行录"','"'+str(ROOT/'dist/客行录')+'"')
    source=source.replace('SourcePath + "\\assets\\app.ico"','"'+str(ROOT/'assets/app.ico')+'"')
    source=source.replace('assets\\app.png',str(ROOT/'assets/app.png'))
    source=source.replace('{autodesktop}',str(temp/'desktop')).replace('{group}',str(temp/'startmenu'))
    source=re.sub(r'\[Run\].*?(?=\[Messages\])','[Run]\n\n',source,flags=re.S)
    script=temp/'fixture.iss';script.write_text(source,encoding='utf-8-sig')
    subprocess.run(['D:/Tools/InnoSetup/ISCC.exe',str(script)],check=True,stdout=subprocess.DEVNULL)
    exe=next(temp.glob('*.exe'))
    archive=dest/'_internal/base_library.zip';archive.parent.mkdir(parents=True)
    archive.write_bytes(b'OLD_ARCHIVE_SENTINEL')
    user_note=dest/'user-note.txt';user_note.write_text('keep me',encoding='utf8')
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.CreateFileW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE]
    kernel.CreateFileW.restype=wintypes.HANDLE
    kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    handle=kernel.CreateFileW(str(archive),0x80000000,1,None,3,0,None)
    assert handle!=wintypes.HANDLE(-1).value
    args=[str(exe),'/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/CURRENTUSER',f'/DIR={dest}']
    uninstaller=dest/'unins000.exe'
    try:
        result=subprocess.run(args+[f'/LOG={temp / "locked.log"}'],timeout=30)
        log=(temp/'locked.log').read_text(encoding='utf-8-sig')
        assert result.returncode!=0 and 'Upgrade preflight blocked:' in log,(result.returncode,log[-2000:])
        assert archive.read_bytes()==b'OLD_ARCHIVE_SENTINEL' and not (dest/'客行录.exe').exists()
        print('LOCKED_ZIP_BLOCKED_BEFORE_WRITING: PASS',flush=True)
        kernel.CloseHandle(handle);handle=None
        subprocess.run(args+[f'/LOG={temp / "installed.log"}'],check=True,timeout=120)
        verify_manifest(dest,VERSION)
        assert user_note.read_text(encoding='utf8')=='keep me'
        assert (temp/'desktop/客行录.lnk').exists()
        print('UNLOCKED_FULL_INSTALL_HASH_AND_SHORTCUT: PASS',flush=True)
        subprocess.run([sys.executable,str(ROOT/'tests/packaged_design_smoke.py'),str(dest/'客行录.exe')],check=True,timeout=40)
    finally:
        if handle:kernel.CloseHandle(handle)
        for logpath in temp.glob('*.log'):
            (ROOT/'design/verification'/('2613-'+logpath.name)).write_bytes(logpath.read_bytes())
        if uninstaller.exists():
            subprocess.run([str(uninstaller),'/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART'],check=True,timeout=40)
    assert user_note.read_text(encoding='utf8')=='keep me'
    print('UNINSTALL_PRESERVES_USER_FILE: PASS',flush=True)

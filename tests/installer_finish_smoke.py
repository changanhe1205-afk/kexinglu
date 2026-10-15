"""Run the same wizard with an isolated AppId and tiny fixture, then uninstall it."""
from pathlib import Path
import re
import subprocess
import tempfile
import time
import uuid
import sys
import installer_visual_smoke as ui

root=ui.ROOT
with tempfile.TemporaryDirectory(prefix='installer-qa-',dir=root/'design/verification') as folder:
    temp=Path(folder)
    source=(root/'installer.iss').read_text(encoding='utf-8-sig')
    source=re.sub(r'AppId=.*', 'AppId={{'+str(uuid.uuid4())+'}', source)
    source=source.replace('#define AppName "客行录"','#define AppName "客行录设计验证"')
    source=source.replace('SourcePath + "\\dist\\installer"', '"'+str(temp)+'"')
    source=source.replace('SourcePath + "\\assets\\app.ico"','"'+str(root/'assets/app.ico')+'"')
    source=source.replace('SourcePath + "\\dist\\客行录"','"'+str(root/'dist/客行录')+'"')
    source=source.replace('WizardSmallImageFile=assets\\app.png','WizardSmallImageFile='+str(root/'assets/app.png'))
    if '--full' in sys.argv:
        source=source.replace('Source: "assets\\app.png"','Source: "'+str(root/'assets/app.png')+'"')
    else:
        source=re.sub(r'\[Files\].*?(?=\[Icons\])',
            lambda _: '[Files]\nSource: "'+str(root/'assets/app.png')+'"; Flags: dontcopy\n'
            +'Source: "'+str(root/'assets/app.png')+'"; DestDir: "{app}"\n\n',source,flags=re.S)
    source=source.replace('{autodesktop}', str(temp/'desktop')).replace('{group}', str(temp/'startmenu'))
    source=re.sub(r'\[Run\].*?(?=\[Messages\])','[Run]\nFilename: "{cmd}"; Parameters: "/C exit"; Description: "启动客行录"; Flags: unchecked postinstall skipifsilent\n\n',source,flags=re.S)
    script=temp/'fixture.iss';script.write_text(source,encoding='utf-8-sig')
    subprocess.run(['D:/Tools/InnoSetup/ISCC.exe',str(script)],check=True,stdout=subprocess.DEVNULL)
    install_dir=temp/'installed'
    exe=next(temp.glob('*.exe'))
    proc=subprocess.Popen([str(exe),'/CURRENTUSER','/LANG=chinese','/SP-',f'/DIR={install_dir}',f'/LOG={temp / "install.log"}'])
    try:
        for _ in range(60):
            hwnd=next((h for h in ui.windows() if ui.caption(h)=='客行录 · 安装'),None)
            if hwnd:break
            time.sleep(.2)
        assert hwnd
        ui.screenshot(hwnd,'installer-preview')
        ui.click_text(hwnd,'开始安装')
        ui.screenshot(hwnd,'installer-location-preview')
        ui.click_text(hwnd,'下一步')
        ui.screenshot(hwnd,'installer-tasks-preview')
        ui.click_text(hwnd,'下一步')
        install=next(h for h in ui.windows(hwnd) if ui.caption(h).startswith('开始安装'))
        ui.u.PostMessageW(install,0xF5,0,0)
        captured=False
        observed=[]
        install_deadline=time.monotonic()+120
        while time.monotonic()<install_deadline:
            texts=[ui.caption(h) for h in ui.windows(hwnd)]
            number=next((int(t[:-1]) for t in texts if re.fullmatch(r'\d{1,3}%',t)),None)
            if number is not None:
                observed.append(number)
                if 35 <= number <= 90 and not captured:
                    ui.screenshot(hwnd,'installer-progress-preview',settle=.02)
                    captured=True
            if any('安装完成' in ui.caption(h) for h in ui.windows(hwnd)):break
            time.sleep(.02)
        assert any('安装完成' in ui.caption(h) for h in ui.windows(hwnd)), (observed[-20:],[ui.caption(h) for h in ui.windows(hwnd)])
        if '--full' in sys.argv:
            assert captured, observed
            assert min(observed)<max(observed),observed
            print('REAL_INSTALL_PROGRESS:',sorted(set(observed)),flush=True)
        ui.screenshot(hwnd,'installer-finish-preview')
        ui.click_text(hwnd,'完成')
        proc.wait(timeout=10)
        print('ISOLATED_INSTALL_FINISH: PASS')
        shortcut=temp/'desktop/客行录设计验证.lnk'
        assert shortcut.exists(), 'Default desktop shortcut missing'
        print('DEFAULT_DESKTOP_SHORTCUT: PASS',flush=True)
        if '--full' in sys.argv:
            sys.path.insert(0,str(root))
            from release_integrity import verify_manifest
            from app_version import VERSION
            verify_manifest(install_dir, VERSION)
            print('INSTALLED_PAYLOAD_SHA256: PASS',flush=True)
            subprocess.run([sys.executable,str(root/'tests/packaged_design_smoke.py'),
                            str(install_dir/'客行录.exe')],check=True)
            print('INSTALLED_APP_EMPTY_PROFILE_OFFLINE: PASS',flush=True)
        # Exercise the visible uninstaller, including cancellation before removal.
        uninstaller=install_dir/'unins000.exe'
        sentinel=install_dir/'user-owned-note.txt'
        sentinel.write_text('preserve user content',encoding='utf-8')
        before=set(ui.windows())
        unproc=subprocess.Popen([str(uninstaller),'/NORESTART'])
        def wait_dialog(word):
            for _ in range(100):
                for h in ui.windows():
                    if h not in before and any(word in ui.caption(c) for c in ui.windows(h)):
                        return h
                time.sleep(.05)
            raise AssertionError('Uninstall dialog missing: '+word)
        confirm=wait_dialog('是否卸载')
        ui.screenshot(confirm,'uninstaller-confirm-preview')
        ui.click_text(confirm,'否')
        unproc.wait(timeout=10)
        assert uninstaller.exists() and shortcut.exists()
        unproc=subprocess.Popen([str(uninstaller),'/NORESTART'])
        confirm=wait_dialog('是否卸载')
        yes=next(c for c in ui.windows(confirm) if ui.caption(c).startswith('是('))
        ui.u.PostMessageW(yes,0xF5,0,0)
        progress=wait_dialog('移除应用，保留你的珍藏')
        ui.screenshot(progress,'uninstaller-progress-preview',settle=.25)
        done=wait_dialog('客行录已卸载')
        ui.screenshot(done,'uninstaller-finish-preview')
        ui.click_text(done,'确定')
        unproc.wait(timeout=10)
        time.sleep(1)
        assert not shortcut.exists()
        assert sentinel.read_text(encoding='utf-8') == 'preserve user content'
        assert not (install_dir/'app.png').exists()
        print('VISIBLE_UNINSTALL_CANCEL_PROGRESS_FINISH: PASS',flush=True)
        # Explicit opt-out must survive installation; a subsequent upgrade resets
        # its default to checked (UsePreviousTasks=no), without touching real desktop.
        subprocess.run([str(exe),'/VERYSILENT','/SUPPRESSMSGBOXES','/CURRENTUSER',
                        '/LANG=chinese',f'/DIR={install_dir}','/TASKS='],check=True)
        assert not shortcut.exists(), 'Desktop opt-out ignored'
        subprocess.run([str(exe),'/VERYSILENT','/SUPPRESSMSGBOXES','/CURRENTUSER',
                        '/LANG=chinese',f'/DIR={install_dir}'],check=True)
        assert shortcut.exists(), 'Upgrade did not default to desktop shortcut'
        print('DESKTOP_OPT_OUT_AND_UPGRADE_DEFAULT: PASS',flush=True)
    finally:
        if (temp/'install.log').exists():
            (root/'design/verification/installer-fixture-last.log').write_bytes((temp/'install.log').read_bytes())
        if proc.poll() is None:subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],capture_output=True)
        uninstaller=install_dir/'unins000.exe'
        if uninstaller.exists():
            subprocess.run([str(uninstaller),'/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART'],check=True)
            time.sleep(1)

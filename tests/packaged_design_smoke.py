"""Launch the built app with temporary app-data folders and capture its own window."""
import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from PIL import ImageGrab

root = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root))
from app_version import VERSION
app_exe = Path(sys.argv[1]).resolve() if len(sys.argv)>1 else root/'dist/客行录/客行录.exe'
inject_tls = '--normal' not in sys.argv
kernel=ctypes.windll.kernel32
kernel.OpenProcess.restype=wintypes.HANDLE
kernel.QueryFullProcessImageNameW.argtypes=[wintypes.HANDLE,wintypes.DWORD,wintypes.LPWSTR,ctypes.POINTER(wintypes.DWORD)]
kernel.CloseHandle.argtypes=[wintypes.HANDLE]

def window_executable(hwnd):
    pid=wintypes.DWORD()
    ctypes.windll.user32.GetWindowThreadProcessId(hwnd,ctypes.byref(pid))
    handle=kernel.OpenProcess(0x1000,False,pid.value)
    if not handle:return None
    try:
        path=ctypes.create_unicode_buffer(32768);size=wintypes.DWORD(len(path))
        if kernel.QueryFullProcessImageNameW(handle,0,path,ctypes.byref(size)):
            return Path(path.value).resolve()
    finally:kernel.CloseHandle(handle)

with tempfile.TemporaryDirectory(prefix='kexinglu-package-') as folder:
    profile = Path(folder)
    env = dict(os.environ, APPDATA=folder, LOCALAPPDATA=folder, USERPROFILE=folder,
               HOMEDRIVE=profile.drive, HOMEPATH=str(profile)[len(profile.drive):],
               HTTP_PROXY='http://127.0.0.1:9', HTTPS_PROXY='http://127.0.0.1:9',
               ALL_PROXY='http://127.0.0.1:9', NO_PROXY='localhost,127.0.0.1,::1',
               FLET_VIEW_PATH=str(profile/'nonexistent-host'))
    previous = set()
    callback = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    @callback
    def snapshot(hwnd,_):
        previous.add(hwnd)
        return True
    ctypes.windll.user32.EnumWindows(snapshot,0)
    expected=(app_exe.parent/'_internal/flet_desktop/app/flet/flet.exe').resolve()
    proc = subprocess.Popen([str(app_exe)] + (['--test-tls-failure'] if inject_tls else []), env=env, cwd=folder)
    found = []
    try:
        for attempt in range(40):
            assert proc.poll() is None, f'Application exited: {proc.returncode}'
            callback = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
            @callback
            def visit(hwnd, _):
                pid = wintypes.DWORD()
                ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                title = ctypes.create_unicode_buffer(256)
                ctypes.windll.user32.GetWindowTextW(hwnd, title, 256)
                if hwnd not in previous and title.value == '客行录' and ctypes.windll.user32.IsWindowVisible(hwnd) and window_executable(hwnd)==expected:
                    found.append(hwnd)
                return True
            ctypes.windll.user32.EnumWindows(visit, 0)
            if found:
                break
            time.sleep(.5)
        assert found, 'Packaged window did not open'
        time.sleep(4)
        rect = wintypes.RECT()
        ctypes.windll.dwmapi.DwmGetWindowAttribute(found[0], 9, ctypes.byref(rect), ctypes.sizeof(rect))
        ImageGrab.grab(bbox=(rect.left,rect.top,rect.right,rect.bottom)).save(root/'design/packaged-preview.png')
        assert list(Path(folder).rglob('yingjianlu.db')), 'Database was not initialized'
        startup_log=(profile/'客行录/startup.log').read_text(encoding='utf-8')
        assert 'version='+VERSION in startup_log, startup_log
        if inject_tls:
            assert 'TEST_TLS_FAILURE probe passed' in startup_log, startup_log
        assert 'Startup failed' not in startup_log, startup_log
        print('FORCED_CERTIFICATE_VERIFY_FAILED_STARTUP: PASS' if inject_tls else 'NORMAL_OFFLINE_STARTUP: PASS',flush=True)
        assert not (profile/'.flet').exists(), 'Startup provisioned a per-user runtime cache'
        worker_pid = wintypes.DWORD()
        ctypes.windll.user32.GetWindowThreadProcessId(found[0],ctypes.byref(worker_pid))
        kernel=ctypes.windll.kernel32
        kernel.OpenProcess.restype=wintypes.HANDLE
        kernel.QueryFullProcessImageNameW.argtypes=[wintypes.HANDLE,wintypes.DWORD,wintypes.LPWSTR,ctypes.POINTER(wintypes.DWORD)]
        kernel.CloseHandle.argtypes=[wintypes.HANDLE]
        handle=kernel.OpenProcess(0x1000,False,worker_pid.value)
        try:
            exe=ctypes.create_unicode_buffer(32768);length=wintypes.DWORD(len(exe))
            assert kernel.QueryFullProcessImageNameW(handle,0,exe,ctypes.byref(length))
            expected=app_exe.parent/'_internal/flet_desktop/app/flet/flet.exe'
            assert Path(exe.value).resolve()==expected.resolve(),exe.value
            print('EMPTY_PROFILE_OFFLINE_BUNDLED_HOST: PASS',exe.value,flush=True)
        finally:
            kernel.CloseHandle(handle)
        from win_identity_probe import read_identity
        identity=read_identity(found[0])
        assert identity['id']=='Kexinglu.Desktop', identity
        assert identity['name']=='客行录', identity
        assert identity['icon'].endswith('app-lu-v1.ico,0'), identity
        assert Path(identity['icon'][:-2]).is_file()
        assert '客行录.exe' in identity['command'], identity
        print('TASKBAR_IDENTITY: PASS',identity,flush=True)
        print('PACKAGED_STARTUP: PASS')
    finally:
        for handle in found:
            if handle not in previous and window_executable(handle)==expected:
                ctypes.windll.user32.PostMessageW(handle, 0x0010, 0, 0)
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.terminate()
            proc.wait(timeout=5)

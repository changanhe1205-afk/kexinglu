"""Inspect real setup pages up to Ready; cancel before writing any installation."""
import ctypes
from ctypes import wintypes
from pathlib import Path
import subprocess
import time
import tempfile
from PIL import ImageGrab

ROOT=Path(__file__).resolve().parents[1]
u=ctypes.windll.user32
callback=ctypes.WINFUNCTYPE(wintypes.BOOL,wintypes.HWND,wintypes.LPARAM)
u.GetWindowTextW.argtypes=[wintypes.HWND,wintypes.LPWSTR,ctypes.c_int]
u.PostMessageW.argtypes=[wintypes.HWND,wintypes.UINT,wintypes.WPARAM,wintypes.LPARAM]
def caption(hwnd):
    buf=ctypes.create_unicode_buffer(2048);u.GetWindowTextW(hwnd,buf,len(buf));return buf.value
def windows(parent=None):
    found=[]
    @callback
    def visit(hwnd,_):
        if u.IsWindowVisible(hwnd):found.append(hwnd)
        return True
    if parent:u.EnumChildWindows(parent,visit,0)
    else:u.EnumWindows(visit,0)
    return found
def click_text(hwnd,words):
    target=next(h for h in windows(hwnd) if caption(h).startswith(words))
    u.PostMessageW(target,0xF5,0,0);time.sleep(.8)
def screenshot(hwnd,name,settle=.5):
    u.SetForegroundWindow(hwnd)
    u.SetCursorPos(5,5)
    time.sleep(settle)
    rect=wintypes.RECT()
    ctypes.windll.dwmapi.DwmGetWindowAttribute(hwnd,9,ctypes.byref(rect),ctypes.sizeof(rect))
    ImageGrab.grab(bbox=(rect.left,rect.top,rect.right,rect.bottom)).save(ROOT/'design'/f'{name}.png')

if __name__=='__main__':
    import sys
    sys.path.insert(0,str(ROOT))
    from app_version import VERSION
    scratch=tempfile.TemporaryDirectory(prefix='kexinglu-wizard-')
    proc=subprocess.Popen([str(ROOT/f'dist/installer/客行录-安装程序-{VERSION}.exe'),'/CURRENTUSER','/LANG=chinese','/SP-',f'/DIR={Path(scratch.name)/"app"}'])
    hwnd=None
    try:
        for _ in range(60):
            hwnd=next((h for h in windows() if caption(h)=='客行录 · 安装'),None)
            if hwnd:break
            time.sleep(.2)
        assert hwnd,'Installer window missing'
        texts=[caption(h) for h in windows(hwnd)]
        print('WELCOME:',texts,flush=True)
        assert any('把日常' in t for t in texts)
        screenshot(hwnd,'installer-preview')
        click_text(hwnd,'开始安装')
        screenshot(hwnd,'installer-location-preview')
        texts=[caption(h) for h in windows(hwnd)]
        assert any('安装位置' in t for t in texts),texts
        click_text(hwnd,'下一步')
        screenshot(hwnd,'installer-tasks-preview')
        click_text(hwnd,'下一步')
        texts=[caption(h) for h in windows(hwnd)]
        assert any('准备安装' in t for t in texts),texts
        screenshot(hwnd,'installer-ready-preview')
        click_text(hwnd,'取消')
        # Confirm cancellation in Inno's native task dialog.
        installer_pid=wintypes.DWORD()
        u.GetWindowThreadProcessId(hwnd,ctypes.byref(installer_pid))
        for h in windows():
            dialog_pid=wintypes.DWORD()
            u.GetWindowThreadProcessId(h,ctypes.byref(dialog_pid))
            if dialog_pid.value != installer_pid.value: continue
            yes=next((c for c in windows(h) if caption(c).startswith('是')),None)
            if yes:u.PostMessageW(yes,0xF5,0,0)
        proc.wait(timeout=10)
        print('INSTALLER_WELCOME_LOCATION_TASKS_READY_CANCEL: PASS')
    finally:
        if proc.poll() is None:
            subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],capture_output=True)

        scratch.cleanup()

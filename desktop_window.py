"""Center and round only this app window, identified by a unique startup title."""
import sys
import uuid
import flet as ft


class DesktopWindow:
    def __init__(self, page):
        self.page = page
        self.hwnd = None
        self.fallback = False
        self.token = '客行录 · ' + uuid.uuid4().hex
        page.title = self.token
        page.window.alignment = ft.Alignment.CENTER
        page.window.shadow = True

    async def initialize(self):
        await self.page.window.wait_until_ready_to_show()
        await self.page.window.center()
        if sys.platform == 'win32':
            import ctypes
            from ctypes import wintypes
            user = ctypes.windll.user32
            user.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
            user.FindWindowW.restype = wintypes.HWND
            self.hwnd = user.FindWindowW(None, self.token)
            if self.hwnd:
                preference = ctypes.c_int(2)
                fn = ctypes.windll.dwmapi.DwmSetWindowAttribute
                fn.argtypes = [wintypes.HWND, wintypes.DWORD, wintypes.LPCVOID, wintypes.DWORD]
                self.fallback = fn(self.hwnd, 33, ctypes.byref(preference), 4) != 0
                self.resize()
        if self.page.title == self.token:
            self.page.title = '客行录'
            self.page.update()

    def resize(self):
        if not self.hwnd or not self.fallback:
            return
        import ctypes
        from ctypes import wintypes
        user, gdi = ctypes.windll.user32, ctypes.windll.gdi32
        user.IsWindow.argtypes = [wintypes.HWND]
        user.IsZoomed.argtypes = [wintypes.HWND]
        user.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
        user.SetWindowRgn.argtypes = [wintypes.HWND, wintypes.HANDLE, wintypes.BOOL]
        if not user.IsWindow(self.hwnd):
            return
        if user.IsZoomed(self.hwnd) or self.page.window.full_screen:
            user.SetWindowRgn(self.hwnd, None, True)
            return
        rect = wintypes.RECT()
        user.GetWindowRect(self.hwnd, ctypes.byref(rect))
        user.GetDpiForWindow.argtypes = [wintypes.HWND]
        radius = round(16 * user.GetDpiForWindow(self.hwnd) / 96)
        gdi.CreateRoundRectRgn.argtypes = [ctypes.c_int] * 6
        gdi.CreateRoundRectRgn.restype = wintypes.HANDLE
        gdi.DeleteObject.argtypes = [wintypes.HANDLE]
        region = gdi.CreateRoundRectRgn(0, 0, rect.right-rect.left+1,
                                      rect.bottom-rect.top+1, radius, radius)
        if region and not user.SetWindowRgn(self.hwnd, region, True):
            gdi.DeleteObject(region)

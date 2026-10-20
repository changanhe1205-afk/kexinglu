"""Isolated native account UI and local mock authentication; sends no email."""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import desktop_design_smoke as qa
import cloud_view
import flet as ft
class FakeCloud:
    configured=True
    github_enabled=False
    enabled_providers=set()
    def refresh_providers(self): return set()
    uid=None
    email=None
    def password_login(self,email,password):
        assert email=='qa@example.com' and password=='qa-password'
        self.uid='qa';self.email=email
    def logout(self): self.uid=None;self.email=None
    def set_password(self,value): pass
fake=FakeCloud()
cloud_view.current_client=lambda:fake
passed=False
async def run(page):
    global passed
    try:
        qa.theme._apply('sage')
        qa.app.main(page)
        await asyncio.sleep(1)
        await qa.screenshot(page,'107-home')
        await qa.click(qa.nav(page,'我的'))
        def button(label):
            return next(c for c in qa.walk(page) if isinstance(c,(ft.TextButton,ft.FilledButton)) and c.content==label)
        await qa.click(button('登录账号'))
        await qa.screenshot(page,'107-account-password')
        await qa.click(button('验证码登录'))
        await qa.screenshot(page,'107-account-otp')
        await qa.click(button('密码登录'))
        for c in qa.walk(page):
            if isinstance(c,ft.TextField) and c.label=='邮箱账号': c.value='qa@example.com'
            if isinstance(c,ft.TextField) and c.label=='密码（至少 8 位）': c.value='qa-password'
        login=next(c for c in qa.walk(page) if isinstance(c,ft.FilledButton) and c.content=='登录' and c.visible)
        await qa.click(login)
        await asyncio.sleep(.6)
        assert fake.uid=='qa'
        await qa.screenshot(page,'107-account-signed-in')
        await qa.click(button('退出登录'))
        await asyncio.sleep(.6)
        assert fake.uid is None
        page.window.width=1080;page.window.height=700;page.update()
        await qa.screenshot(page,'107-account-small')
        passed=True
        print('ACCOUNT_UI: PASS password/code switches, mocked login/logout, compact window; no real auth calls',flush=True)
    finally:
        await page.window.destroy()
if __name__=='__main__':
    ft.run(run);qa.temp.cleanup();sys.exit(0 if passed else 1)

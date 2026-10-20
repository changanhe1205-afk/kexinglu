"""Native smoke in a temporary data folder. Never touches the user's library."""
import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parent))
import desktop_design_smoke as qa
import config
import flet as ft

passed=False
async def run(page):
    global passed
    try:
        qa.app.main(page)
        await asyncio.sleep(1)
        await qa.click(qa.nav(page,'我的'))
        for language,name in [('en','Me'),('ja','マイページ'),('zh-TW','我的')]:
            field=next(c for c in qa.walk(page) if isinstance(c,ft.Dropdown) and c.label=='语言 / Language')
            field.value=language
            field.on_select(SimpleNamespace(control=field))
            assert config.get('language')==language
            assert qa.has_text(page,name)
            assert qa.has_text(page,{'en':'Account & sync','ja':'アカウントと同期','zh-TW':'帳號與同步'}[language])
            await page.window.to_front()
            await qa.screenshot(page,'desktop-locale-'+language)
        passed=True
        print('PASS: locale selection persists, profile and navigation translate; isolated data only.',flush=True)
    finally: await page.window.destroy()
if __name__=='__main__':
    ft.run(run);qa.temp.cleanup();sys.exit(0 if passed else 1)

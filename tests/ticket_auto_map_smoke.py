import asyncio
import ctypes
from ctypes import wintypes
import sys
import travel_journal_smoke as base
import ticket_editing_smoke as editing
import ticket_db as db
import flet as ft
from PIL import ImageGrab
qa=base.qa;passed=False
async def shot(page,name):
    page.update();await asyncio.sleep(1)
    handle=ctypes.windll.user32.FindWindowW(None,'客行录 · 自动轨迹验证')
    assert handle
    ctypes.windll.user32.SetForegroundWindow(handle)
    rect=wintypes.RECT();ctypes.windll.dwmapi.DwmGetWindowAttribute(handle,9,ctypes.byref(rect),ctypes.sizeof(rect))
    ImageGrab.grab(bbox=(rect.left,rect.top,rect.right,rect.bottom)).save(qa.ROOT/'design/verification'/name)
async def run(page):
    global passed
    try:
        air=db.add_ticket(vehicle='飞机',from_city='徐州观音国际机场',to_city='北京首都国际机场',code='CA1234',depart_date='2026-10-10')
        rail=db.add_ticket(vehicle='高铁',from_city='北京南',to_city='上海虹桥',code='G123')
        qa.app.main(page);page.title='客行录 · 自动轨迹验证';page.update()
        await qa.click(qa.nav(page,'旅行日志'))
        assert not any(isinstance(c,ft.TextButton) and c.content in ('飞机轨迹','高铁轨迹') for c in qa.walk(page))
        await qa.click(qa.nav(page,'旅程票根'))
        assert qa.has_text(page,'已自动生成 · 飞机 1 / 高铁 1')
        await shot(page,'2614-ticket-auto-preview.png')
        await qa.click(base.button(page,'飞机地图'))
        atlas=page.views[-1].data['route_atlas'];assert atlas.automatic and len(atlas.routes)==1
        assert not any(isinstance(c,ft.TextField) for c in qa.walk(atlas.view))
        assert atlas.routes[0]['id']==air
        atlas.load(atlas.routes[0]);await shot(page,'2614-ticket-auto-atlas.png')
        atlas.switch('rail');assert atlas.routes[0]['id']==rail
        atlas.close()
        await qa.click(base.button(page,'新增机票'))
        editing.text(page,'出发地','上海浦东国际机场');editing.text(page,'目的地','东京成田国际机场')
        await qa.click(base.button(page,'保存新票根'))
        assert qa.has_text(page,'已自动生成 · 飞机 2 / 高铁 1')
        editing.text(page,'目的地','洛杉矶国际机场')
        await qa.click(base.button(page,'更新当前票根'))
        await qa.click(base.button(page,'飞机地图'))
        atlas=page.views[-1].data['route_atlas']
        assert any(r['points'][1]['lon']<0 for r in atlas.routes)
        atlas.close()
        delete=next(c for c in qa.walk(page) if isinstance(c,ft.TextButton) and c.content=='删除')
        await qa.click(delete)
        assert qa.has_text(page,'已自动生成 · 飞机 1 / 高铁 1')
        passed=True;print('TICKET_DERIVED_MAP: PASS (old tickets, moved entry, no route editor, auto create/update/delete, mode isolation)',flush=True)
    except Exception:
        import traceback;traceback.print_exc()
    finally:await page.window.destroy()
if __name__=='__main__':
    ft.run(run);qa.temp.cleanup();sys.exit(0 if passed else 1)

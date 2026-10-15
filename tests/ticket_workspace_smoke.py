import asyncio,sys,ctypes
from ctypes import wintypes
import travel_journal_smoke as base
import ticket_editing_smoke as editing
import travel_layout_smoke as capture
import ticket_db as db
import flet as ft
qa=base.qa
passed=False

async def run(page):
    global passed
    try:
        air=db.add_ticket(vehicle='飞机',from_city='徐州观音国际机场',to_city='北京首都国际机场',code='CA1234',depart_date='2026-10-10')
        for i in range(5):
            db.add_ticket(vehicle='飞机',from_city='上海浦东国际机场',to_city='东京成田国际机场',code=f'MU52{i}0')
        db.add_ticket(vehicle='高铁',from_city='北京南',to_city='上海虹桥',code='G123')
        qa.app.main(page)
        await asyncio.wait_for(asyncio.wrap_future(page.startup_window_task),15)
        h=page.desktop_window.hwnd
        assert h,'Native window not identified'
        rect=wintypes.RECT();user=ctypes.windll.user32
        user.GetWindowRect.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.RECT)]
        user.GetWindowRect(h,ctypes.byref(rect))
        user.MonitorFromWindow.argtypes=[wintypes.HWND,wintypes.DWORD]
        user.MonitorFromWindow.restype=wintypes.HANDLE
        class Monitor(ctypes.Structure):
            _fields_=[('size',wintypes.DWORD),('monitor',wintypes.RECT),('work',wintypes.RECT),('flags',wintypes.DWORD)]
        info=Monitor();info.size=ctypes.sizeof(info)
        user.GetMonitorInfoW.argtypes=[wintypes.HANDLE,ctypes.POINTER(Monitor)]
        user.GetMonitorInfoW(user.MonitorFromWindow(h,2),ctypes.byref(info))
        assert abs((rect.left+rect.right)-(info.work.left+info.work.right))<32
        assert abs((rect.top+rect.bottom)-(info.work.top+info.work.bottom))<32
        if not page.desktop_window.fallback:
            pref=ctypes.c_int()
            fn=ctypes.windll.dwmapi.DwmGetWindowAttribute
            fn.argtypes=[wintypes.HWND,wintypes.DWORD,wintypes.LPVOID,wintypes.DWORD]
            assert fn(h,33,ctypes.byref(pref),4)==0 and pref.value==2
        print('WINDOW_CENTER_AND_CORNERS: PASS',flush=True)
        page.title='客行录 · 自动轨迹验证';page.update()
        await qa.click(qa.nav(page,'旅程票根'))
        body=next(c for c in qa.walk(page) if isinstance(c.data,dict) and 'ticket_atlas' in c.data)
        state=body.data;atlas=state['ticket_atlas']
        assert not state['ticket_floating']['open'] and len(atlas.routes)==6
        await capture.shot(page,'2621-ticket-map.png')
        card=next(c for c in qa.walk(body) if isinstance(c,ft.Container) and c.tooltip=='徐州观音国际机场 → 北京首都国际机场')
        await qa.click(card)
        assert state['ticket_floating']['open'] and state['ticket_current']['id']==air
        await capture.shot(page,'2621-ticket-front.png')
        gesture=next(c for c in qa.walk(body) if isinstance(c,ft.GestureDetector) and c.on_tap)
        await gesture.on_tap(None)
        assert state['ticket_flip']['back']
        await capture.shot(page,'2621-ticket-back.png')
        await qa.click(next(c for c in qa.walk(body) if isinstance(c,ft.IconButton) and c.tooltip=='收起票根'))
        assert not state['ticket_floating']['open']
        await qa.click(base.button(page,'新增机票'))
        from types import SimpleNamespace as E
        import ticket_view
        assert len(ticket_view.AIRLINES)==41
        for code in ('G5','EU','JD','NS','GY','GX','9H','A6','JR'):
            assert ticket_view.airline_of(code+'1234')[0]==code
        airline=next(c for c in qa.walk(page) if isinstance(c,ft.Dropdown) and c.label=='航空公司')
        assert any(o.key=='G5' for o in airline.options)
        airline.value='G5';airline.on_select(E(control=airline))
        editing.text(page,'航班','G51234')
        editing.text(page,'出发地','上海浦东国际机场');editing.text(page,'目的地','洛杉矶国际机场')
        await qa.click(base.button(page,'保存新票根'))
        assert len(db.list_tickets())==8 and len(atlas.routes)==7
        await capture.shot(page,'2621-ticket-edit.png')
        await qa.click(next(c for c in qa.walk(body) if isinstance(c,ft.IconButton) and c.tooltip=='收起票根'))
        await qa.click(base.button(page,'高铁地图'));assert len(atlas.routes)==1
        view=atlas.v
        await qa.click(base.button(page,'飞机地图'));assert len(atlas.routes)==7
        from types import SimpleNamespace as E
        atlas.scroll(E(scroll_delta=E(x=35,y=10)));await asyncio.sleep(.12)
        assert atlas.v.lon!=view.lon
        page.window.width=1080;page.window.height=760;page.update();await asyncio.sleep(.5)
        await capture.shot(page,'2621-ticket-small.png')
        listing=next(c for c in qa.walk(body) if isinstance(c,ft.ListView) and c.on_scroll)
        await listing.scroll_to(offset=120,duration=200)
        await asyncio.sleep(.4)
        assert state['ticket_floating']['scroll']>0,'Ticket list did not scroll'
        # Foreground the isolated QA window, and let the actual timer move the list.
        for c in list(qa.walk(page)):
            if isinstance(c,ft.SnackBar):c.open=False
        page.update()
        page.window.focused=True
        rolling=state['ticket_rolling']
        rolling['focus']=None;rolling['hover']=rolling['form_hover']=False
        before_scroll=state['ticket_floating']['scroll']
        state['ticket_rolling']['deadline']=0
        await asyncio.sleep(2)
        assert state['ticket_floating']['scroll']!=before_scroll,'Auto scrolling did not advance'
        assert not state['ticket_floating']['open'],'Auto scroll opened a ticket'
        assert len(db.list_tickets())==8
        night=next(c for c in qa.walk(body) if isinstance(c,ft.Container) and c.tooltip=='地图风格：夜航地图')
        await qa.click(night)
        assert atlas.style_key=='night'
        await capture.shot(page,'2621-ticket-night.png')
        card=next(c for c in qa.walk(body) if isinstance(c,ft.Container) and c.tooltip=='上海浦东国际机场 → 洛杉矶国际机场')
        await qa.click(card)
        await qa.click(next(c for c in qa.walk(body) if isinstance(c,ft.IconButton) and c.tooltip=='编辑这张票根'))
        await qa.click(base.button(page,'删除'))
        assert len(db.list_tickets())==7 and len(atlas.routes)==6
        assert not state['ticket_floating']['open']
        from unittest.mock import patch
        import route_style
        with patch.object(route_style,'background',wraps=route_style.background) as background:
            atlas.draw();atlas.draw()
            assert background.call_count==0,'Unchanged map background rebuilt'
        await qa.click(base.button(page,'新增铁路票根'))
        editing.text(page,'出发地','北京南');editing.text(page,'目的地','上海虹桥')
        await qa.click(base.button(page,'保存新票根'))
        assert atlas.mode=='rail'
        route=next(r for r in atlas.routes if r['id']==state['ticket_current']['id'])
        assert all(0<=atlas.v(p['lon'],p['lat'])[0]<=atlas.v.width and
                   0<=atlas.v(p['lon'],p['lat'])[1]<=atlas.v.height for p in route['points'])
        print('AIRLINES_AND_ROUTE_REFRESH: PASS (G5 brand, 41 airlines, rail auto-switch/fit, cached basemap)',flush=True)
        passed=True;print('TICKET_WORKSPACE: PASS (map, overlay, flip, new/save, mode, pan, small window, auto browsing)',flush=True)
    except Exception:
        import traceback;traceback.print_exc()
    finally:await page.window.destroy()

if __name__=='__main__':
    ft.run(run);qa.temp.cleanup();sys.exit(0 if passed else 1)

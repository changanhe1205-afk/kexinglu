"""Native regression flow, using only temporary records and settings."""
import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace as Event
import time
import sys
import desktop_design_smoke as qa
import flet as ft
import travel_db
import theme

passed = False

def map_body(page):
    return next(c for c in qa.walk(page) if isinstance(c.data,dict) and 'map_state' in c.data)

def title_brand(page):
    drag = next(c for c in qa.walk(page) if isinstance(c,ft.WindowDragArea))
    return next(c for c in drag.content.controls if isinstance(c,ft.Row))

async def run(page):
    global passed
    try:
        qa.app.main(page)
        page.window.left=35
        page.window.top=35
        page.update()
        await asyncio.sleep(1)
        assert title_brand(page).visible is False
        await qa.screenshot(page,'222-home')
        await qa.click(qa.nav(page,'旅程票根'))
        assert title_brand(page).visible is True
        datefield=next(c for c in qa.walk(page) if isinstance(c,ft.TextField) and c.label=='出发日期')
        datefield.value='2026-10-05'
        datebutton=next(c for c in qa.walk(page) if isinstance(c,ft.IconButton) and c.tooltip=='选择日期')
        await qa.click(datebutton)
        picker=next(c for c in qa.walk(page) if isinstance(c,ft.DatePicker))
        assert picker.value.day==5
        for day in (5,7):
            picker.value=datetime(2026,10,day).astimezone().astimezone(timezone.utc)
            picker.on_change(Event(control=picker))
            assert datefield.value==f'2026-10-{day:02d}'
        page.pop_dialog()
        await qa.screenshot(page,'222-date')
        travel_db.add_log(title='北京之行',city='北京',visit_date='2026-10-05',lon=116.4,lat=39.9)
        travel_db.add_log(title='西湖散步',city='杭州',visit_date='2026-10-07',lon=120.15,lat=30.27)
        await qa.click(qa.nav(page,'旅行日志'))
        body=map_body(page)
        state=body.data['map_state']
        gesture=next(c for c in qa.walk(body) if isinstance(c,ft.GestureDetector) and c.on_scale_update is not None)
        assert gesture.on_pan_update is None
        assert gesture.trackpad_scroll_causes_scale is False
        v=state['mapview']
        anchor=ft.Offset(220,220)
        old=v.lonlat_at(220,220)
        gesture.on_scale_start(Event(local_focal_point=anchor))
        gesture.on_scale_update(Event(local_focal_point=anchor,scale=2))
        gesture.on_scale_end(Event())
        assert abs(state['mapview'].zoom-v.zoom-1)<.0001
        new=state['mapview'].lonlat_at(220,220)
        assert abs(old[0]-new[0])<.000001
        gesture.on_scale_start(Event(local_focal_point=anchor))
        gesture.on_scale_update(Event(local_focal_point=ft.Offset(250,240),scale=.5))
        gesture.on_scale_end(Event())
        assert abs(state['mapview'].zoom-v.zoom)<.0001
        z=state['mapview'].zoom
        gesture.on_scroll(Event(scroll_delta=ft.Offset(0,-120),local_position=anchor))
        await asyncio.sleep(.15)
        assert state['mapview'].zoom == z
        base=state['mapview']
        gesture.on_scroll(Event(scroll_delta=ft.Offset(48,24),local_position=anchor))
        await asyncio.sleep(.15)
        assert state['mapview'].lon != base.lon and state['mapview'].lat != base.lat
        assert state['mapview'].zoom == z
        await qa.click(next(c for c in qa.walk(body) if c.tooltip=='查看全部足迹'))
        # Exercise Windows pointer events through the rendered Flutter hit-test tree.
        await asyncio.sleep(.6)
        import ctypes
        from ctypes import wintypes
        u=ctypes.windll.user32
        u.SetProcessDPIAware()
        hwnd=u.FindWindowW(None,'客行录')
        rect=wintypes.RECT()
        ctypes.windll.dwmapi.DwmGetWindowAttribute(hwnd,9,ctypes.byref(rect),ctypes.sizeof(rect))
        u.SetForegroundWindow(hwnd)
        px=round(rect.left+(rect.right-rect.left)*.47)
        py=round(rect.top+(rect.bottom-rect.top)*.55)
        u.SetCursorPos(px,py)
        await asyncio.sleep(.2)
        before=state['mapview'].zoom
        before_lat=state['mapview'].lat
        u.mouse_event(0x0800,0,0,120,0)
        await asyncio.sleep(.6)
        assert state['mapview'].zoom == before and state['mapview'].lat != before_lat
        before_lon=state['mapview'].lon
        u.mouse_event(0x1000,0,0,120,0)
        await asyncio.sleep(.4)
        assert state['mapview'].lon != before_lon and state['mapview'].zoom == before
        await qa.click(next(c for c in qa.walk(body) if c.tooltip=='滚动：平移（点击切换缩放）'))
        gesture.on_scroll(Event(scroll_delta=ft.Offset(0,-120),local_position=anchor))
        await asyncio.sleep(.15)
        assert state['mapview'].zoom > before
        await qa.click(next(c for c in qa.walk(body) if c.tooltip=='滚动：缩放（点击切换平移）'))
        before_lon=state['mapview'].lon
        u.mouse_event(2,0,0,0,0)
        for delta in range(5,46,5):
            u.SetCursorPos(px+delta,py+10)
            await asyncio.sleep(.04)
        u.mouse_event(4,0,0,0,0)
        await asyncio.sleep(.5)
        assert state['mapview'].lon != before_lon, 'Native mouse pan did not reach map'
        print('PASS real Windows wheel and drag input',flush=True)
        await qa.click(next(c for c in qa.walk(body) if c.tooltip=='查看全部足迹'))
        zoom=state['mapview'].zoom
        for g in state['groups']:
            x,y=state['mapview'](g['lon'],g['lat'])
            assert 0 < x < state['mapview'].width and 0 < y < state['mapview'].height
        await asyncio.sleep(2)
        await qa.screenshot(page,'222-map')
        await qa.click(qa.nav(page,'旅程票根'))
        assert not state['active']
        t=time.perf_counter()
        await qa.click(qa.nav(page,'旅行日志'))
        elapsed=time.perf_counter()-t
        assert map_body(page) is body and state['mapview'].zoom==zoom
        print(f'PASS map pinch/scroll/pan, fit, cached return {elapsed:.3f}s',flush=True)
        await qa.click(qa.nav(page,'我的'))
        assert title_brand(page).visible is False
        tile=next(c for c in qa.walk(page) if isinstance(c,ft.Container) and c.tooltip=='应用主题：午夜蓝')
        await qa.click(tile)
        await qa.screenshot(page,'222-profile-dark')
        await qa.click(qa.nav(page,'旅行日志'))
        assert map_body(page) is not body
        await qa.screenshot(page,'222-map-dark')
        page.window.width=1080
        page.window.height=700
        await asyncio.sleep(.8)
        await qa.screenshot(page,'222-map-small')
        passed=True
        print('INTERACTION_RESULT: PASS',flush=True)
    except Exception:
        import traceback
        traceback.print_exc()
    finally:
        await page.window.destroy()

if __name__=='__main__':
    ft.run(run)
    qa.temp.cleanup()
    sys.exit(0 if passed else 1)

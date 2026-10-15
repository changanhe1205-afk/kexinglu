import asyncio
import inspect
import sys
from types import SimpleNamespace as Event
import desktop_design_smoke as qa
import flet as ft
import ticket_db
import ticket_design
import ticket_view
passed=False

async def run(page):
    global passed
    try:
        qa.app.main(page)
        page.window.left=35
        page.window.top=35
        cities={'CA':'北京','MU':'上海','CZ':'广州','HU':'海口','MF':'厦门','3U':'成都'}
        for prefix,city in cities.items():
            ticket_db.add_ticket(vehicle='飞机',from_city=city,to_city='杭州',code=prefix+'1234',
                depart_date='2026-10-07',passenger='林晓',style='classic',note='沿着街巷走走，留一点时间给自己。')
        ticket_db.add_ticket(vehicle='高铁',from_city='南京',to_city='杭州',code='G123',depart_date='2026-10-07')
        ticket_db.add_ticket(vehicle='火车',from_city='北京',to_city='杭州',code='Z123',depart_date='2026-10-07')
        await qa.click(qa.nav(page,'旅程票根'))
        assert qa.has_text(page,'铁路 · 高铁 / 火车')
        assert qa.has_text(page,'飞机')
        await qa.screenshot(page,'222-ticket-groups')
        await qa.click(next(c for c in qa.walk(page) if getattr(c,'tooltip',None)=='票根分类：铁路'))
        listing=next(c for c in qa.walk(page) if isinstance(c,ft.ListView) and any(qa.has_text(x,'铁路 · 高铁 / 火车') for x in c.controls))
        assert len([c for c in listing.controls if isinstance(c,ft.Container) and c.tooltip and '→' in str(c.tooltip)])==2
        assert not any(qa.has_text(c,'CA1234') for c in listing.controls)
        await qa.screenshot(page,'222-rail-category')
        await qa.click(next(c for c in qa.walk(page) if getattr(c,'tooltip',None)=='票根分类：全部'))
        for prefix,city in cities.items():
            await qa.click(next(c for c in qa.walk(page) if isinstance(c,ft.Container) and c.tooltip==city+' → 杭州' and qa.has_text(c,prefix+'1234')))
            gesture=next(c for c in qa.walk(page) if isinstance(c,ft.GestureDetector) and c.on_tap)
            result=gesture.on_tap(Event(control=gesture))
            if inspect.isawaitable(result): await result
            assert qa.has_text(page,ticket_design.POSTER_THEMES[prefix][0].replace('，','\n'))
            assert qa.has_text(page,ticket_view.AIRLINES[prefix][0])
            await qa.screenshot(page,'222-poster-'+prefix)
        for style in ('digital','midnight','minimal','rose'):
            picker=next(c for c in qa.walk(page) if isinstance(c,ft.Dropdown) and c.label=='飞机票面样式')
            picker.value=style
            picker.on_select(Event(control=picker))
            gesture=next(c for c in qa.walk(page) if isinstance(c,ft.GestureDetector) and c.on_tap)
            result=gesture.on_tap(Event(control=gesture))
            if inspect.isawaitable(result): await result
            await qa.screenshot(page,'222-poster-'+style)
        await qa.click(qa.nav(page,'我的'))
        await qa.screenshot(page,'222-logo-light')
        import ctypes
        from win_identity_probe import read_identity
        identity=read_identity(ctypes.windll.user32.FindWindowW(None,'客行录'))
        assert identity['id']=='Kexinglu.Desktop.Dev',identity
        assert identity['icon'].endswith('app-lu-v1.ico,0'),identity
        print('POSTERS_GROUPS_AND_SHELL: PASS',flush=True)
        passed=True
    except Exception:
        import traceback;traceback.print_exc()
    finally:
        await page.window.destroy()
if __name__=='__main__':
    ft.run(run)
    qa.temp.cleanup()
    sys.exit(0 if passed else 1)

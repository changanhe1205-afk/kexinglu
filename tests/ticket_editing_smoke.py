"""Native regression for airport autocomplete, partial deletion, and new/edit separation."""
import asyncio
import ctypes
from types import SimpleNamespace as Event
import sys
import travel_journal_smoke as base
import flet as ft
import ticket_db as db
import ticket_view as view
import ticket_design

qa=base.qa;passed=False

def field(page,label):
    return next(c for c in qa.walk(page) if isinstance(c,ft.TextField) and c.label==label)

def text(page,label,value):
    c=field(page,label);c.value=value
    if c.on_change:c.on_change(Event(control=c))
    return c

def dismiss_toast(page):
    # Keep the actual edit dialog stack unmodified; snack bars close themselves.
    for c in qa.walk(page):
        if isinstance(c,ft.SnackBar):c.open=False
    page.update()

async def run(page):
    global passed
    try:
        original_id=db.add_ticket(vehicle='飞机',from_city='北京首都国际机场',to_city='杭州萧山国际机场',
            code='MU5812',price='680',depart_date='2026-10-06',style='classic')
        original=db.get_ticket(original_id)
        for query in ('徐州','观音','XUZ','xuzhou','xuz','徐州观音国际机场'):
            assert ('XUZ','徐州观音国际机场') in view.airport_matches(query)
        for name in ('徐州观音国际机场','徐州','观音机场','XUZ','xuz','XUZ · 徐州观音国际机场'):
            assert view.airport_code(name)=='XUZ',name
        assert view.airport_code('北京大兴国际机场')=='PKX'
        assert view.airport_code('上海浦东国际机场')=='PVG'
        qa.app.main(page);page.window.left=25;page.window.top=25;page.update();await asyncio.sleep(.8)
        await qa.click(qa.nav(page,'旅程票根'))
        route=next(c for c in qa.walk(page) if isinstance(c,ft.Container) and c.on_click and qa.has_text(c,'北京首都国际机场 → 杭州萧山国际机场'))
        await qa.click(route)
        assert base.button(page,'更新当前票根')
        flight=text(page,'航班','MU5812')
        # Actual keyboard deletion goes through Flutter's TextField event stream.
        await flight.focus();page.update();await asyncio.sleep(.3)
        user=ctypes.windll.user32;hwnd=user.FindWindowW(None,'客行录');user.SetForegroundWindow(hwnd)
        assert user.GetForegroundWindow()==hwnd
        for key in (0x23,0x08,0x08): # End, Backspace, Backspace
            user.keybd_event(key,0,0,0);user.keybd_event(key,0,2,0)
        await asyncio.sleep(.6)
        assert flight.value=='MU58',repr(flight.value)
        for code in ('MU5','MU','M','','3U8633','MU5816'):
            text(page,'航班',code);assert flight.value==code
        airline=next(c for c in qa.walk(page) if isinstance(c,ft.Dropdown) and c.label=='航空公司')
        airline.value='CA';airline.on_select(Event(control=airline))
        assert flight.value=='MU5816','Changing airline replaced the typed flight'
        await qa.click(base.button(page,'新增机票'))
        await qa.click(base.button(page,'放弃修改并新建'))
        assert db.get_ticket(original_id)==original
        assert field(page,'航班').value=='' and base.button(page,'保存新票根')
        text(page,'出发地','徐州')
        assert qa.has_text(page,'徐州观音国际机场')
        assert not any(isinstance(c,ft.AlertDialog) and c.open for c in qa.walk(page))
        await qa.screenshot(page,'262-airport-inline')
        await qa.click(next(c for c in qa.walk(page) if isinstance(c,ft.Container) and c.tooltip=='选用：XUZ · 徐州观音国际机场'))
        text(page,'目的地','HGH')
        await qa.click(next(c for c in qa.walk(page) if isinstance(c,ft.Container) and c.tooltip=='选用：HGH · 杭州萧山国际机场'))
        text(page,'航班','MU5816');text(page,'票价（CNY）','CNY 680.50')
        assert qa.has_text(page,'CNY 680.50')
        await qa.click(base.button(page,'保存新票根'));dismiss_toast(page)
        assert len(db.list_tickets())==2 and db.get_ticket(original_id)==original
        new=next(t for t in db.list_tickets() if t['id']!=original_id)
        assert new['code']=='MU5816' and new['price']=='680.50'
        text(page,'航班','MU581');await qa.click(base.button(page,'更新当前票根'));dismiss_toast(page)
        assert len(db.list_tickets())==2 and db.get_ticket(new['id'])['code']=='MU581'
        assert db.get_ticket(original_id)==original
        for style in ticket_design.AIR_STYLES:
            picker=next(c for c in qa.walk(page) if isinstance(c,ft.Dropdown) and c.label=='飞机票面样式')
            picker.value=style;picker.on_select(Event(control=picker))
            assert qa.has_text(page,'CNY 680.50'),style
        await qa.screenshot(page,'262-ticket-cny')
        await qa.click(base.button(page,'另存为新票根'));dismiss_toast(page)
        assert len(db.list_tickets())==3
        await qa.click(base.button(page,'新增铁路票根'))
        assert field(page,'车次')
        text(page,'车次','G834');text(page,'车次','G83')
        assert field(page,'车次').value=='G83'
        text(page,'出发地','杭州')
        assert any(isinstance(c,ft.Container) and str(c.tooltip or '').startswith('选用：杭州') for c in qa.walk(page))
        print('TICKET_EDITING_NATIVE: PASS (real Backspace, XUZ, inline suggestions, CNY in 5 styles, new/edit/copy isolation, rail)',flush=True)
        passed=True
    except Exception:
        import traceback;traceback.print_exc()
    finally:await page.window.destroy()

if __name__=='__main__':
    ft.run(run);qa.temp.cleanup();sys.exit(0 if passed else 1)

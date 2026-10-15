import asyncio,sys
import flet as ft
from types import SimpleNamespace as E
import travel_journal_smoke as base
import ticket_auto_map_smoke as visual
import travel_db as db
qa=base.qa;passed=False
async def shot(page,name):
    import ctypes
    h=ctypes.windll.user32.FindWindowW(None,'客行录 · 自动轨迹验证')
    ctypes.windll.user32.SetWindowPos(h,-1,0,0,0,0,0x13)
    try:await visual.shot(page,name)
    finally:ctypes.windll.user32.SetWindowPos(h,-2,0,0,0,0,0x13)

async def run(page):
    global passed
    try:
        from PIL import Image
        photo=qa.Path(qa.temp.name)/'travel.jpg';Image.new('RGB',(700,480),'#829F9B').save(photo)
        first=db.add_log(title='湖边散步',city='杭州',visit_date='2026-10-05',note='沿着湖岸慢慢走，记住这一天的风。')
        db.add_photos(first,[str(photo)])
        db.add_log(title='海边的一天',city='厦门',visit_date='2026-09-22',note='傍晚在海边看日落。')
        qa.app.main(page);page.title='客行录 · 自动轨迹验证';page.update()
        await qa.click(qa.nav(page,'旅行日志'))
        body=next(c for c in qa.walk(page) if isinstance(c.data,dict) and 'map_state' in c.data)
        await asyncio.sleep(.8)
        state=body.data['map_state'];wide=state['map_w']
        assert not state['editor_open'] and len(state['groups'])==2
        await shot(page,'2618-travel-overview.png')
        search=next(c for c in qa.walk(page) if isinstance(c,ft.TextField) and c.label=='查找地点')
        search.value='杭州';search.on_change(E(control=search))
        assert len(state['groups'])==2,'Search removed map markers'
        search.value='';search.on_change(E(control=search))
        await qa.click(base.button(page,'记录旅程'))
        assert state['editor_open'] and state['map_w']<wide
        base.set_field(page,'地点','山间小路');base.set_field(page,'城市（可不填）','成都')
        await qa.click(next(c for c in qa.walk(page) if isinstance(c,ft.IconButton) and c.tooltip=='收起编辑（保留草稿）'))
        assert not state['editor_open'] and state['map_w']==wide
        await qa.click(next(c for c in qa.walk(page) if isinstance(c,ft.IconButton) and c.tooltip=='展开 / 收起记录'))
        assert next(c for c in qa.walk(page) if isinstance(c,ft.TextField) and c.label=='地点').value=='山间小路'
        await qa.click(base.button(page,'记录旅程'))
        await qa.click(base.button(page,'继续编辑'))
        assert next(c for c in qa.walk(page) if isinstance(c,ft.TextField) and c.label=='地点').value=='山间小路'
        await qa.click(base.button(page,'保存'))
        assert len(db.list_logs())==3 and len(state['groups'])==3
        await shot(page,'2618-travel-editor.png')
        def card(title):
            return next(c for c in qa.walk(body) if isinstance(c,ft.Container) and c.on_click and c.on_hover
                and any(isinstance(t,ft.Text) and t.value==title for t in qa.walk(c)))
        base.set_field(page,'地点','山间小路草稿')
        await qa.click(card('成都'))
        assert next(c for c in qa.walk(page) if isinstance(c,ft.TextField) and c.label=='地点').value=='山间小路草稿'
        await qa.click(card('杭州'))
        await qa.click(base.button(page,'继续编辑'))
        assert next(c for c in qa.walk(page) if isinstance(c,ft.TextField) and c.label=='地点').value=='山间小路草稿'
        await qa.click(card('杭州'))
        await qa.click(base.button(page,'放弃修改并继续'))
        assert next(c for c in qa.walk(page) if isinstance(c,ft.TextField) and c.label=='地点').value=='湖边散步'
        await qa.click(next(c for c in qa.walk(page) if isinstance(c,ft.IconButton) and c.tooltip=='收起编辑（保留草稿）'))
        await qa.click(next(c for c in qa.walk(page) if isinstance(c,ft.Container) and c.tooltip=='全屏看地图'))
        assert state['fs'];await asyncio.sleep(.2)
        await qa.click(next(c for c in qa.walk(page) if isinstance(c,ft.Container) and c.tooltip=='退出全屏'))
        assert not state['fs']
        gesture=next(c for c in qa.walk(body) if isinstance(c,ft.GestureDetector) and c.on_scroll)
        before=state['mapview'].lon
        gesture.on_scroll(E(scroll_delta=E(x=40,y=15)));await asyncio.sleep(.1)
        assert state['mapview'].lon!=before
        from unittest.mock import patch
        import map_data
        # Sustained small movements must reuse the expensive province artwork.
        with patch.object(map_data,'build_overlay',wraps=map_data.build_overlay) as overlay:
            before=state['mapview'].lon
            for _ in range(40):
                gesture.on_scroll(E(scroll_delta=E(x=1,y=0)))
                await asyncio.sleep(.04)
            assert state['mapview'].lon!=before
            assert overlay.call_count<=1, f'Excessive pan rebuilds: {overlay.call_count}'
            print(f'PAN_REUSE: PASS (40 events, {overlay.call_count} province rebuilds)',flush=True)
        page.window.width=1080;page.window.height=760;page.update();await asyncio.sleep(.5)
        await shot(page,'2618-travel-small.png')
        await qa.click(base.button(page,'旅行手账'))
        assert base.button(page,'新建手账')
        page.pop_dialog();await asyncio.sleep(.3)
        assert len(db.list_logs())==3
        passed=True;print('TRAVEL_LAYOUT: PASS (map retained, search keeps map, collapse preserves draft, cancel new, save, fullscreen, pan, compact window, notebook entry)',flush=True)
    except Exception:
        import traceback;traceback.print_exc()
    finally:await page.window.destroy()
if __name__=='__main__':
    ft.run(run);qa.temp.cleanup();sys.exit(0 if passed else 1)

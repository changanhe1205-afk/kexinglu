import asyncio,sys
import flet as ft
import ticket_auto_map_smoke as visual
import ticket_db as db
import route_style
import config
qa=visual.qa;passed=False
async def run(page):
    global passed
    try:
        for start,end in [('北京首都国际机场','上海浦东国际机场'),('徐州观音国际机场','广州白云国际机场'),('成都天府国际机场','杭州萧山国际机场')]:
            db.add_ticket(vehicle='飞机',from_city=start,to_city=end,code='CA1234')
        db.add_ticket(vehicle='高铁',from_city='北京南',to_city='上海虹桥',code='G123')
        qa.app.main(page);page.title='客行录 · 自动轨迹验证';page.update()
        await qa.click(qa.nav(page,'旅程票根'))
        await qa.click(visual.base.button(page,'飞机地图'))
        atlas=page.views[-1].data['route_atlas']
        original=db.list_tickets();pos=(atlas.v.lon,atlas.v.lat,atlas.v.zoom)
        await visual.shot(page,'2617-day-atlas.png')
        await qa.click(next(c for c in qa.walk(atlas.view) if isinstance(c,ft.Container) and c.tooltip=='地图风格：夜航地图'))
        assert route_style.current()=='night' and atlas.view.bgcolor=='#101E30'
        assert (atlas.v.lon,atlas.v.lat,atlas.v.zoom)==pos
        assert not any(isinstance(c,ft.Image) and str(c.src).startswith('http') for c in qa.walk(atlas.view))
        await visual.shot(page,'2617-night-atlas.png')
        import tile_map
        atlas.v=tile_map.View(atlas.v.width,atlas.v.height,117,35,6)
        atlas.draw();page.update()
        assert any(isinstance(c,ft.Text) and c.value=='济南' for c in qa.walk(atlas.map))
        await visual.shot(page,'2617-city-labels.png')
        atlas.home()
        atlas.switch('rail');assert atlas.style_key=='night'
        atlas.close();await visual.shot(page,'2617-night-preview.png')
        assert config.load()['ticket_map_style']=='night'
        await qa.click(visual.base.button(page,'飞机地图'))
        atlas=page.views[-1].data['route_atlas'];assert atlas.style_key=='night'
        atlas.world();await visual.shot(page,'2617-night-world.png')
        atlas.change_style('day');atlas.close()
        await visual.shot(page,'2617-day-preview.png')
        assert db.list_tickets()==original
        passed=True;print('ROUTE_STYLES: PASS (two skins, offline vector map, preview sync, persistent preference, view preserved, ticket data unchanged)',flush=True)
    except Exception:
        import traceback;traceback.print_exc()
    finally:await page.window.destroy()
if __name__=='__main__':
    ft.run(run);qa.temp.cleanup();sys.exit(0 if passed else 1)

import asyncio
import sys
import travel_journal_smoke as base
import flet as ft
import travel_routes as db
import route_atlas
qa=base.qa
passed=False
async def run(page):
    global passed
    try:
        qa.app.main(page)
        await qa.click(qa.nav(page,'旅行日志'))
        route_atlas.open_atlas(page,'air')  # Legacy route renderer, no longer a travel-log entry.
        atlas=page.views[-1].data['route_atlas']
        assert 73<atlas.v.lon<136
        atlas.start.value='北京';atlas.end.value='上海';atlas.show_preview()
        assert len(atlas.preview)==2 and not db.list_routes('air')
        atlas.save();assert len(db.list_routes('air'))==1
        first=atlas.selected
        atlas.new();atlas.start.value='徐州观音国际机场 | 117.555,34.059';atlas.end.value='上海';atlas.save()
        assert len(db.list_routes('air'))==2 and atlas.selected!=first
        atlas.switch('rail');assert not atlas.routes
        atlas.start.value='北京';atlas.via.value='济南';atlas.end.value='上海';atlas.save()
        assert len(db.list_routes('rail'))==1 and len(atlas.routes[0]['points'])==3
        assert all(c.data['mode']=='rail' for c in atlas.map.controls if isinstance(c.data,dict) and 'route_endpoint' in c.data)
        await qa.screenshot(page,'2612-rail-atlas')
        atlas.switch('air');atlas.world()
        assert atlas.v.zoom<3
        await qa.screenshot(page,'2612-world-atlas')
        atlas.new();atlas.start.value='东京 | 139.69,35.68';atlas.end.value='洛杉矶 | -118.24,34.05';atlas.show_preview()
        assert len(atlas.preview)==2
        atlas.save();atlas.home()
        await qa.screenshot(page,'2612-flight-atlas')
        atlas.load(atlas.routes[-1]);atlas.title.value='京沪飞行';atlas.save()
        assert len(db.list_routes('air'))==3
        atlas.start.value='不存在的地方';atlas.show_preview();assert '未找到' in atlas.status.value
        from types import SimpleNamespace as E
        atlas.begin_pick(atlas.start)
        atlas.pick_point(E(local_position=E(x=atlas.v.width/2,y=atlas.v.height/2)))
        assert '|' in atlas.start.value and atlas.pick_target is None
        before=atlas.v.lon
        atlas.scroll(E(scroll_delta=E(x=30,y=10)));await asyncio.sleep(.1)
        assert atlas.v.lon!=before
        before=atlas.v.zoom
        atlas.scale_start(E(local_focal_point=E(x=200,y=200)))
        atlas.scale_update(E(local_focal_point=E(x=210,y=205),scale=1.5))
        await asyncio.sleep(.1)
        assert atlas.v.zoom>before
        atlas.load(atlas.routes[0]);atlas.remove()
        await qa.click(next(c for c in qa.walk(page) if isinstance(c,ft.FilledButton) and c.content=='删除'))
        assert len(db.list_routes('air'))==2
        atlas.close();assert page.views[-1].route!='/travel-routes'
        await qa.click(qa.nav(page,'影视收藏'))
        passed=True;print('ROUTE_ATLAS: PASS',flush=True)
    except Exception:
        import traceback;traceback.print_exc()
    finally:await page.window.destroy()
if __name__=='__main__':
    ft.run(run);qa.temp.cleanup();sys.exit(0 if passed else 1)

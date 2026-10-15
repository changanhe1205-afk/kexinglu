import asyncio,sys,json
import desktop_design_smoke as qa
import travel_layout_smoke as capture
import flet as ft
import ticket_db,theme,background
passed=False
async def run(page):
 global passed
 try:
  for a,b in [('余姚北','枣庄'),('独山东','贵阳北'),('枣庄','济南西'),('重庆西','独山东'),('成都东','都匀东'),('厦门北','福州南'),('贵阳北','杭州东')]:
   ticket_db.add_ticket(vehicle='高铁',from_city=a,to_city=b,code='G123')
  theme.set_theme(preset='sea')
  qa.app.main(page)
  await asyncio.wait_for(asyncio.wrap_future(page.startup_window_task),15)
  page.title='客行录 · 自动轨迹验证';page.update()
  await qa.click(qa.nav(page,'旅程票根'))
  body=next(c for c in qa.walk(page) if isinstance(c.data,dict) and 'ticket_atlas' in c.data)
  atlas=body.data['ticket_atlas'];atlas.switch('rail')
  assert len(atlas.routes)==7
  for r in atlas.routes:
   for p in r['points']:
    assert not p['approximate']
    x,y=atlas.v(p['lon'],p['lat']);assert 0<x<atlas.v.width and 0<y<atlas.v.height
  await capture.shot(page,'2622-rail-all.png')
  await qa.click(qa.nav(page,'我的'))
  await capture.shot(page,'2622-appearance.png')
  # Render every local SVG in the same native renderer used by the application.
  page.add(ft.Row(wrap=True,controls=[ft.Image(src=background.preset_src(rel),width=200,height=112,fit=ft.BoxFit.COVER) for _,rel in background.PRESETS if rel.endswith('.svg')]))
  await asyncio.sleep(1)
  # A separate simple contact sheet keeps all six renderings visible.
  page.clean();page.add(ft.Column(controls=[ft.Row(controls=[ft.Image(src=background.preset_src(rel),width=360,height=202,fit=ft.BoxFit.COVER) for _,rel in background.PRESETS[3+i:6+i]]) for i in (0,3)]))
  await capture.shot(page,'2622-backgrounds.png')
  assert '山行' not in [n for n,_ in background.PRESETS]
  qa.Path(background.STATE_PATH).write_text(json.dumps({'type':'preset','value':'assets/bg_shanxing.png'}),encoding='utf8')
  assert background.current()==background.default_src()
  assert not background.set_preset('assets/bg_shanxing.png')
  passed=True;print('APPEARANCE_AND_SEVEN_RAIL_ROUTES: PASS',flush=True)
 except Exception:
  import traceback;traceback.print_exc()
 finally:await page.window.destroy()
if __name__=='__main__':
 ft.run(run);qa.temp.cleanup();sys.exit(0 if passed else 1)

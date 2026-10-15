"""Public documentation screenshots, generated only from synthetic demo records."""
import asyncio,sys
import desktop_design_smoke as qa
import travel_layout_smoke as capture
import flet as ft
import ticket_db,travel_db,theme
passed=False
async def run(page):
 global passed
 try:
  theme.set_theme(preset='sea')
  for a,b in [('北京南','上海虹桥'),('上海虹桥','杭州东'),('杭州东','福州南')]:
   ticket_db.add_ticket(vehicle='高铁',from_city=a,to_city=b,code='G101',depart_date='2026-10-01')
  for title,city in [('沿湖慢行','杭州'),('一座城的清晨','苏州'),('听海的一天','厦门')]:
   travel_db.add_log(title=title,city=city,visit_date='2026-10-01',note='演示记录 · 用文字留住旅途里的片刻。')
  qa.app.main(page)
  await asyncio.wait_for(asyncio.wrap_future(page.startup_window_task),15)
  page.title='客行录 · 自动轨迹验证';page.update()
  await qa.click(qa.nav(page,'旅程票根'))
  body=next(c for c in qa.walk(page) if isinstance(c.data,dict) and 'ticket_atlas' in c.data)
  body.data['ticket_atlas'].switch('rail')
  await capture.shot(page,'release-tickets.png')
  await qa.click(qa.nav(page,'旅行日志'))
  await asyncio.sleep(12)  # Allow asynchronous online map tiles to load before capture.
  await capture.shot(page,'release-travel.png')
  for name in ('release-tickets.png','release-travel.png'):
   from PIL import Image
   path=qa.ROOT/'docs/images'/name;path.parent.mkdir(parents=True,exist_ok=True)
   im=Image.open(qa.OUT/name);im.thumbnail((1320,900));im.save(path,optimize=True)
  passed=True;print('PUBLIC_DEMO_SCREENSHOTS: PASS')
 finally:await page.window.destroy()
if __name__=='__main__':
 ft.run(run);qa.temp.cleanup();sys.exit(0 if passed else 1)

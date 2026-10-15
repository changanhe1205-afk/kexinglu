"""Native dismissal regression: no orphan routes, discard never overwrites saved work."""
import asyncio,sys,ctypes
from copy import deepcopy
from ctypes import wintypes
import travel_journal_smoke as base
qa=base.qa
import flet as ft
import travel_db
import travel_journal as journal
from notebook_collage import element
passed=False

def studio_for(page):
 return next(v.data['notebook_studio'] for v in page.views if isinstance(v.data,dict) and 'notebook_studio' in v.data)

async def returned(page,old_full):
 await qa.click(base.button(page,'返回旅行日志'))
 await asyncio.sleep(.4)
 assert not page._dialogs.controls, 'Native dismiss callbacks left orphan dialogs'
 assert len(page.views)==1 and page.window.full_screen==old_full

async def run(page):
 global passed
 try:
  qa.app.main(page);travel_db.add_log(title='退出测试',city='杭州',visit_date='2026-10-07')
  await qa.click(qa.nav(page,'旅行日志'));old_full=page.window.full_screen
  for source in ('新建手账','新建空白手账'):
   await qa.click(base.button(page,'旅行手账'));await qa.click(base.button(page,source))
   await qa.click(base.button(page,'开始编排' if source=='新建手账' else '开始创作'))
   studio=studio_for(page);assert page.window.full_screen
   assert not page._dialogs.controls, 'Creator route must be dismissed before studio opens'
   studio.request_close();studio.request_close()
   assert sum(c.open for c in page._dialogs.controls)==1
   await qa.click(base.button(page,'继续编辑'));assert studio.alive
   studio.request_close();await qa.click(base.button(page,'放弃修改'))
   assert not studio.alive and not journal.list_books()
   await returned(page,old_full)
  # Save a real notebook, change it, then discard. The saved version must survive.
  await qa.click(base.button(page,'旅行手账'));await qa.click(base.button(page,'新建空白手账'))
  await qa.click(base.button(page,'开始创作'));studio=studio_for(page)
  studio.append(element(text='必须保留的原稿'));assert studio.save()
  saved=deepcopy(journal.get_book(studio.book['id']))
  studio.change('text','这次修改要放弃');studio.request_close()
  await qa.click(base.button(page,'放弃修改'));assert journal.get_book(saved['id'])==saved
  await qa.click(base.button(page,'打开手账'));studio=studio_for(page)
  studio.append(element(text='这次保存并退出'));studio.request_close()
  await qa.click(base.button(page,'保存并退出'));assert len(journal.get_book(saved['id'])['pages'][0]['design']['elements'])==2
  await returned(page,old_full)
  u=ctypes.windll.user32;u.SetProcessDPIAware();handle=u.FindWindowW(None,'客行录');u.SetForegroundWindow(handle)
  await qa.screenshot(page,'268-return-to-travel')
  # Real mouse click on the main navigation proves no invisible modal blocks it.
  rect=wintypes.RECT();ctypes.windll.dwmapi.DwmGetWindowAttribute(handle,9,ctypes.byref(rect),ctypes.sizeof(rect))
  u.SetCursorPos(rect.left+round((rect.right-rect.left)*.747),rect.top+round((rect.bottom-rect.top)*.935))
  u.mouse_event(2,0,0,0,0);u.mouse_event(4,0,0,0,0);await asyncio.sleep(.6)
  assert any(isinstance(c,ft.Container) and c.tooltip=='应用主题：午夜蓝' for c in qa.walk(page)), 'Invisible modal blocked real navigation click'
  await qa.screenshot(page,'268-navigation-usable')
  passed=True;print('NATIVE_EXIT: PASS (record/blank creation, fullscreen restored, continue then discard, duplicate exit, original data preserved, save-and-exit, no orphan dialogs, real mouse navigation)',flush=True)
 except Exception:
  import traceback;traceback.print_exc()
 finally:await page.window.destroy()

if __name__=='__main__':
 ft.run(run);qa.temp.cleanup();sys.exit(0 if passed else 1)

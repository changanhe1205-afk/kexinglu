"""Exercise actual native perspective frames, navigation, and all bindings."""
import asyncio
import ctypes
from ctypes import wintypes
from types import SimpleNamespace as Event
from unittest.mock import patch
import sys
import travel_journal_smoke as base
from notebook_book import NotebookBook
import travel_journal as journal
import travel_db
import flet as ft
from PIL import ImageGrab

qa=base.qa;passed=False
def snap():
    handle=ctypes.windll.user32.FindWindowW(None,'客行录')
    rect=wintypes.RECT();ctypes.windll.dwmapi.DwmGetWindowAttribute(handle,9,ctypes.byref(rect),ctypes.sizeof(rect))
    picture=ImageGrab.grab(bbox=(rect.left,rect.top,rect.right,rect.bottom))
    picture.thumbnail((1080,760));return picture

async def run(page):
    global passed
    try:
        for i,title in enumerate(('杭州·湖边慢行','苏州·雨巷','厦门·看海','成都·茶馆','写在最后')):
            travel_db.add_log(title=title,city=title[:2],visit_date=f'2026-10-0{i+1}',note='把日常留给远方，把回忆留在纸上。\n'+'这是一段长手记，向下滚动也能继续阅读。\n'*8)
        qa.app.main(page);page.window.left=25;page.window.top=25;page.update();await asyncio.sleep(.6)
        await qa.click(qa.nav(page,'旅行日志'));await qa.click(base.button(page,'旅行手账'))
        await qa.click(base.button(page,'新建手账'));await qa.click(base.button(page,'开始编排'));await base.enter_classic_after_creation(page)
        viewer=next(c for c in qa.walk(page) if isinstance(c,NotebookBook))
        for style in journal.STYLES:
            base.select(page,'纸页风格',style)
            assert viewer.book['style']==style
        base.select(page,'纸页风格','ocean')
        await qa.click(base.button(page,'阅读预览'))
        await qa.screenshot(page,'261-book-cover')
        frames=[snap()]
        with patch('notebook_book.motion_enabled',return_value=True):
            turning=asyncio.create_task(qa.click(base.button(page,'下一页')))
            await asyncio.sleep(.08)
            assert viewer.busy
            await qa.click(base.button(page,'下一页'))  # A rapid second request must not skip pages.
            for _ in range(12):
                frames.append(snap());await asyncio.sleep(.04)
            await turning
        assert viewer.index==0 and not viewer.busy
        frames.append(snap())
        frames[0].save(qa.ROOT/'design/verification/261-book-flip.gif',save_all=True,append_images=frames[1:],
                       duration=[450]+[65]*(len(frames)-2)+[850],loop=0)
        await qa.screenshot(page,'261-book-spread')
        viewer.drag_start(None);viewer.drag_update(Event(primary_delta=-100,local_delta=None))
        await viewer.drag_end(None);assert viewer.index==2
        await qa.click(base.button(page,'下一页'));assert viewer.index==4
        await qa.click(base.button(page,'下一页'));assert viewer.index==4
        await qa.screenshot(page,'261-book-final-leaf')
        with patch('notebook_book.motion_enabled',return_value=False):
            await qa.click(base.button(page,'上一页'));assert viewer.index==2
        await qa.click(base.button(page,'上一页'));assert viewer.index==0
        await qa.click(base.button(page,'上一页'));assert viewer.index==-1
        await qa.click(base.button(page,'上一页'));assert viewer.index==-1
        await qa.click(base.button(page,'继续编排'))
        base.select(page,'纸页风格','linen');await qa.click(base.button(page,'保存手账'))
        await qa.screenshot(page,'261-book-styles')
        journal.export_html(viewer.book,qa.ROOT/'design/verification/261-notebook-sample.html')
        assert journal.get_book(viewer.book['id'])['style']=='linen'
        print('NATIVE_3D_NOTEBOOK: PASS (8 styles, perspective frames, rapid click, swipe, boundaries, reduced motion)',flush=True)
        passed=True
    except Exception:
        import traceback;traceback.print_exc()
    finally:await page.window.destroy()

if __name__=='__main__':
    ft.run(run);qa.temp.cleanup();sys.exit(0 if passed else 1)

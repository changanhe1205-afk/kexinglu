"""Real Flet canvas workflow in an isolated profile, never the user's notebooks."""
import asyncio
from types import SimpleNamespace as Event
from copy import deepcopy
from unittest.mock import AsyncMock, patch
import sys
import travel_journal_smoke as base
import flet as ft
import travel_journal as journal
from notebook_book import NotebookBook
from notebook_collage import PAPERS, LAYOUTS

qa=base.qa;passed=False

async def run(page):
    global passed
    try:
        qa.app.main(page);page.window.left=25;page.window.top=25;page.update();await asyncio.sleep(.6)
        await qa.click(qa.nav(page,'旅行日志'));await qa.click(base.button(page,'旅行手账'))
        await qa.click(base.button(page,'新建空白手账'))
        await qa.click(base.button(page,'开始创作'));await base.enter_classic_after_creation(page)
        base.select(page,'翻到','0')
        await qa.click(base.button(page,'设计这一页 · 自由拼贴'))
        for key in PAPERS:base.select(page,'本页纸张',key)
        for key in LAYOUTS:base.select(page,'套用版式（可撤销）',key)
        base.select(page,'套用版式（可撤销）','daily');base.select(page,'本页纸张','blue')
        await qa.click(base.button(page,'添加文字'));base.set_field(page,'文字内容','独立编辑的蓝色日记')
        node=next(c for c in qa.walk(page) if isinstance(c,ft.Container) and c.data=={'collage_element':7})
        gesture=node.content
        gesture.on_pan_start(Event())
        old=node.left
        gesture.on_pan_update(Event(local_delta=ft.Offset(23,16)))
        assert node.left>old
        await qa.click(base.button(page,'复制'));await qa.click(base.button(page,'删除元素'))
        await qa.click(base.button(page,'撤销'))
        node=next(c for c in qa.walk(page) if isinstance(c,ft.Container) and c.data=={'collage_element':8})
        node.content.on_tap(Event())
        await qa.click(base.button(page,'删除元素'))
        node=next(c for c in qa.walk(page) if isinstance(c,ft.Container) and c.data=={'collage_element':7})
        node.content.on_tap(Event())
        await qa.click(base.button(page,'删除元素'))
        with patch.object(ft.FilePicker,'pick_files',new=AsyncMock(return_value=[Event(path=str(qa.ROOT/'assets/bg_shanxing.png'))])):
            await qa.click(base.button(page,'添加相片'))
        slider=next(c for c in qa.walk(page) if isinstance(c,ft.Slider) and c.min==-30)
        slider.value=-5;slider.on_change(Event(control=slider))
        await qa.click(base.button(page,'下移一层'))
        await qa.screenshot(page,'264-collage-editor')
        await qa.click(base.button(page,'应用到这一页'))
        viewer=next(c for c in qa.walk(page) if isinstance(c,NotebookBook))
        original=deepcopy(viewer.book['pages'][0]['design'])
        await qa.click(base.button(page,'设计这一页 · 自由拼贴'))
        base.select(page,'套用版式（可撤销）','blank')
        await qa.click(base.button(page,'取消'))
        assert viewer.book['pages'][0]['design']==original
        for key,paper in zip(('postcard','garden','memo','film'),('rose','sage','kraft','grid')):
            await qa.click(base.button(page,'添加空白页'))
            await qa.click(base.button(page,'设计这一页 · 自由拼贴'))
            base.select(page,'套用版式（可撤销）',key);base.select(page,'本页纸张',paper)
            await qa.click(base.button(page,'应用到这一页'))
        await qa.click(base.button(page,'保存手账'))
        loaded=journal.get_book(viewer.book['id']);assert loaded['pages'][0]['design']==original
        assert len(loaded['pages'])==5 and loaded['pages'][1]['design']['paper']=='rose'
        base.select(page,'翻到','0');await qa.click(base.button(page,'阅读预览'))
        await qa.screenshot(page,'264-collage-spread')
        await qa.click(base.button(page,'下一页'));assert viewer.index==2
        await qa.click(base.button(page,'上一页'));assert viewer.index==0
        journal.export_html(loaded,qa.ROOT/'design/verification/264-collage.html')
        await qa.click(base.button(page,'返回书架'));await qa.click(base.button(page,'经典编排'))
        viewer=next(c for c in qa.walk(page) if isinstance(c,NotebookBook))
        assert viewer.book['pages'][0]['design']==original
        page.window.width=1080;page.window.height=760;page.update();await asyncio.sleep(.3)
        base.select(page,'翻到','0')
        await qa.click(base.button(page,'设计这一页 · 自由拼贴'))
        await qa.screenshot(page,'264-collage-small')
        await qa.click(base.button(page,'取消'))
        print('COLLAGE_NATIVE: PASS (blank book, 6 papers, 6 layouts, text edit, drag, duplicate, delete, undo, cancel, save/reopen, flip, export)',flush=True)
        passed=True
    except Exception:
        import traceback;traceback.print_exc()
    finally:await page.window.destroy()

if __name__=='__main__':
    ft.run(run);qa.temp.cleanup();sys.exit(0 if passed else 1)

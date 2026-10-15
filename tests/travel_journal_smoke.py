"""Native notebook workflow against an isolated profile and source records."""
import asyncio
from dataclasses import fields
from types import SimpleNamespace as Event
import sys
from unittest.mock import AsyncMock, patch
import desktop_design_smoke as qa
import flet as ft
from flet.controls.base_control import BaseControl
from PIL import Image
import travel_db
import travel_journal as journal

passed=False

def walk(root):
    seen,stack=set(),[root]
    while stack:
        obj=stack.pop()
        if isinstance(obj,BaseControl):
            if id(obj) in seen or getattr(obj,'visible',True) is False:continue
            if isinstance(obj,ft.AlertDialog) and not obj.open:continue
            seen.add(id(obj));yield obj
            stack.extend(getattr(obj,f.name) for f in fields(obj) if f.name!='data')
        elif isinstance(obj,(list,tuple)):stack.extend(obj)
        elif isinstance(obj,dict):stack.extend(obj.values())
qa.walk=walk

_click=qa.click
async def click_and_wait(control):
    page=control.page
    await asyncio.sleep(.25)  # Let the native route mount before clicking it.
    await _click(control)
    while (pending:=getattr(page,'notebook_transition',None)) is not None and not pending.done():
        await asyncio.wait_for(asyncio.wrap_future(pending),5)
qa.click=click_and_wait

def button(page,label):
    return next(c for c in walk(page) if isinstance(c,(ft.TextButton,ft.FilledButton,ft.OutlinedButton)) and c.content==label)

def set_field(page,label,value):
    control=next(c for c in walk(page) if isinstance(c,ft.TextField) and c.label==label)
    control.value=value
    if control.on_change:control.on_change(Event(control=control))

def select(page,label,value):
    control=next(c for c in walk(page) if isinstance(c,ft.Dropdown) and c.label==label)
    control.value=value
    if control.on_select:control.on_select(Event(control=control))


async def enter_classic_after_creation(page):
    """New books now open fullscreen; classic editing stays on the bookshelf."""
    studio=next(v.data['notebook_studio'] for v in page.views if isinstance(v.data,dict) and 'notebook_studio' in v.data)
    assert page.window.full_screen
    assert studio.save();studio.request_close()
    await qa.click(button(page,'经典编排'))

async def run(page):
    global passed
    try:
        image=qa.Path(qa.temp.name)/'lake.jpg'
        Image.new('RGB',(900,600),'#6E958C').save(image)
        a=travel_db.add_log(title='西湖边的午后',city='杭州',visit_date='2026-10-05',note='走过长堤，风里有桂花的气息。')
        b=travel_db.add_log(title='海边的一日',city='厦门',visit_date='2026-09-10',note='日落之前，沿着海岸慢慢走。')
        travel_db.add_photos(a,[str(image)])
        original=travel_db.list_logs()
        qa.app.main(page);page.window.left=25;page.window.top=25
        page.update();await asyncio.sleep(1)
        await qa.click(qa.nav(page,'旅行日志'))
        self_empty=journal.list_books();assert not self_empty
        await qa.screenshot(page,'260-travel-entry')
        await qa.click(button(page,'旅行手账'))
        await qa.click(button(page,'新建手账'))
        select(page,'收录范围','record');select(page,'选择旅行记录',str(a))
        set_field(page,'手账名称','杭州 · 慢下来的两日')
        await qa.click(button(page,'开始编排'))
        assert not journal.list_books()
        await enter_classic_after_creation(page)
        await qa.screenshot(page,'260-notebook-cover')
        select(page,'翻到','0')
        set_field(page,'这一页的手记','桂花落在石板路上。\n把这段慢下来的时间，留给自己。')
        await qa.click(button(page,'添加空白页'))
        set_field(page,'页标题','写在旅途之后')
        set_field(page,'这一页的手记','下一次，再沿湖走一走。')
        await qa.click(button(page,'前移一页'))
        await qa.click(button(page,'保存手账'))
        stored=journal.get_book(journal.list_books()[0]['id'])
        assert len(stored['pages'])==2 and stored['pages'][0]['title']=='写在旅途之后'
        assert stored['pages'][1]['source_id']==a
        await qa.click(button(page,'下一页'))
        export_path=qa.Path(qa.temp.name)/'独立电子手账.html'
        with patch.object(ft.FilePicker,'save_file',new=AsyncMock(return_value=str(export_path))):
            await qa.click(button(page,'导出电子版'))
        assert 'data:image/jpeg;base64,' in export_path.read_text(encoding='utf-8')
        with patch.object(ft.FilePicker,'save_file',new=AsyncMock(return_value=None)):
            await qa.click(button(page,'导出电子版'))
        await qa.screenshot(page,'260-notebook-page')
        await qa.click(button(page,'阅读预览'))
        await qa.screenshot(page,'260-notebook-reading')
        await qa.click(button(page,'返回书架'))
        await qa.click(button(page,'经典编排'))
        set_field(page,'手账名称','不保存的修改')
        await qa.click(button(page,'返回书架'))
        await qa.click(button(page,'放弃修改'))
        assert journal.list_books()[0]['title']=='杭州 · 慢下来的两日'
        await qa.click(button(page,'新建手账'))
        select(page,'收录范围','place')
        assert len([c for c in walk(page) if isinstance(c,ft.Checkbox)])==1
        select(page,'收录范围','all')
        set_field(page,'手账名称','所有走过的地方')
        await qa.click(button(page,'开始编排'));await enter_classic_after_creation(page)
        await qa.click(button(page,'保存手账'))
        all_book=journal.get_book(journal.list_books()[0]['id'])
        assert len(all_book['pages'])==2
        select(page,'纸页风格','night')
        await qa.screenshot(page,'260-notebook-night')
        await qa.click(button(page,'保存手账'))
        await qa.click(button(page,'返回书架'))
        await qa.screenshot(page,'260-notebook-shelf')
        await qa.click(button(page,'返回旅行日志'))
        await qa.click(qa.nav(page,'我的'))
        await qa.click(next(c for c in walk(page) if isinstance(c,ft.Container) and c.tooltip=='应用主题：午夜蓝'))
        await qa.click(qa.nav(page,'旅行日志'))
        page.window.width=1080;page.window.height=700;page.update();await asyncio.sleep(.8)
        await qa.click(button(page,'旅行手账'))
        await qa.click(button(page,'经典编排'))
        await qa.screenshot(page,'260-notebook-dark-small')
        await qa.click(button(page,'返回书架'))
        await qa.click(next(c for c in walk(page) if isinstance(c,ft.IconButton) and c.tooltip=='删除手账'))
        await qa.click(button(page,'删除手账'))
        assert len(journal.list_books())==1
        # Map may fill coordinates; notebook editing must not mutate text/photos.
        after=travel_db.list_logs()
        for x,y in zip(original,after):
            for key in ('title','note','photos','visit_date'):assert x[key]==y[key]
        print('TRAVEL_NOTEBOOK_NATIVE_WORKFLOW: PASS',flush=True)
        passed=True
    except Exception:
        import traceback;traceback.print_exc()
    finally:
        await page.window.destroy()

if __name__=='__main__':
    ft.run(run)
    qa.temp.cleanup()
    sys.exit(0 if passed else 1)

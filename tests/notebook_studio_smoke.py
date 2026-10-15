"""Exercise the real native studio against isolated user data."""
import asyncio
import base64
from io import BytesIO
from types import SimpleNamespace as Event
from unittest.mock import AsyncMock, patch
from PIL import Image, ImageDraw, ImageStat
import sys
import json
import flet as ft
import travel_journal_smoke as base
import travel_journal as journal
from notebook_collage import TEXT_PRESETS, element

qa=base.qa;passed=False

async def run(page):
    global passed
    try:
        sticker=qa.Path(qa.temp.name)/'透明花朵.png'
        im=Image.new('RGBA',(160,160),(0,0,0,0));d=ImageDraw.Draw(im)
        for x,y in [(30,50),(65,20),(100,50),(80,95),(35,95)]:d.ellipse((x,y,x+45,y+45),fill='#8BA7BB')
        d.ellipse((65,65,100,100),fill='#F6DE93');im.save(sticker)
        qa.app.main(page);page.window.left=20;page.window.top=20;page.update();await asyncio.sleep(.5)
        old_resize=page.on_resize;old_keyboard=page.on_keyboard_event;old_full=page.window.full_screen
        await qa.click(qa.nav(page,'旅行日志'));await qa.click(base.button(page,'旅行手账'))
        await qa.click(base.button(page,'新建空白手账'))
        base.set_field(page,'手账名称','山野之间 · 自由手账')
        await qa.click(base.button(page,'开始创作'))
        studio=next(v.data['notebook_studio'] for v in page.views if isinstance(v.data,dict) and 'notebook_studio' in v.data)
        assert page.window.full_screen, 'New notebook must open fullscreen'
        studio.fullscreen();await asyncio.sleep(.3)
        assert not journal.list_books()
        with patch.object(journal,'save_book',side_effect=OSError('模拟磁盘写入失败')):
            assert not studio.save() and studio.alive and studio.saved is None
        assert '保存失败' in studio.status.value
        assert not any(isinstance(c,ft.AlertDialog) and c.open for c in qa.walk(page))
        studio.append(element(**TEXT_PRESETS['书页标题']));studio.change('text','山野之间');studio.change('x',28);studio.change('y',25)
        studio.append(element(**TEXT_PRESETS['手写句子']));studio.change('text','风经过的地方，都值得记下。');studio.change('x',30);studio.change('y',100)
        studio.change('shadow',True);studio.change('highlight','#F5E7A0')
        node=next(c for c in studio.canvas.content.content.controls if c.data=={'collage_element':1})
        gesture=node.content;gesture.on_pan_start(Event());gesture.on_pan_update(Event(local_delta=ft.Offset(12,8)))
        assert studio.current()['x']>30
        width=studio.current()['w'];studio.checkpoint();studio.drag_resize(Event(local_delta=ft.Offset(-15,10)))
        assert studio.current()['w']<width
        studio.change('locked',True);before=studio.current()['x'];studio.change('x',200);assert studio.current()['x']==before
        studio.change('locked',False)
        studio.category.value='import';studio.paint_materials()
        with patch.object(ft.FilePicker,'pick_files',new=AsyncMock(return_value=[Event(path=str(sticker)),Event(path=str(qa.ROOT/'assets/bg_shanxing.png'))])):
            await studio.import_materials(None)
        assert len(studio.book['materials'])==2
        with patch.object(ft.FilePicker,'pick_files',new=AsyncMock(return_value=None)):
            await studio.import_materials(None)
        assert len(studio.book['materials'])==2 and not studio.importing
        mat=studio.book['materials'][0]
        decoded=Image.open(BytesIO(base64.b64decode(mat['image'])));assert decoded.getpixel((0,0))[3]==0
        studio.add_material(studio.book['materials'][1]);studio.change('x',30);studio.change('y',190);studio.change('w',330);studio.change('h',235)
        studio.add_material(mat);studio.change('x',300);studio.change('y',440);studio.change('w',85);studio.change('h',85)
        sticker.unlink()  # A notebook must not depend on the source path.
        studio.duplicate();count=len(studio.design['elements']);studio.remove();assert len(studio.design['elements'])==count-1
        studio.undo();assert len(studio.design['elements'])==count
        studio.undo(True);assert len(studio.design['elements'])==count-1
        studio.select(0);studio.hide_layer(0);assert studio.design['elements'][0]['hidden'];studio.hide_layer(0)
        await qa.screenshot(page,'265-studio-workspace')
        with Image.open(qa.ROOT/'design/verification/265-studio-workspace.png') as shot:
            w,h=shot.size
            region=shot.crop((int(w*.40),int(h*.40),int(w*.58),int(h*.58)))
            assert min(ImageStat.Stat(region).stddev)>15, 'Photo missing from rendered canvas'
        studio.fullscreen();await asyncio.sleep(.4);assert page.window.full_screen
        await qa.screenshot(page,'265-studio-fullscreen');studio.fullscreen();await asyncio.sleep(.3)
        studio.set_zoom(1.8);assert studio.zoom==1.8;studio.set_zoom(1)
        studio.add_page();studio.append(element(text='第二页，独立编辑'));studio.goto(0)
        assert len(studio.book['pages'])==2
        assert studio.save();book_id=studio.book['id'];assert len(journal.get_book(book_id)['materials'])==2
        studio.append(element(text='撤销测试'));studio.undo();assert studio.book['id']==book_id
        assert studio.save();assert len(journal.list_books())==1
        studio.preview(None);await qa.click(base.button(page,'下一页'));await asyncio.sleep(.8)
        await qa.screenshot(page,'265-studio-preview');await qa.click(base.button(page,'继续创作'))
        output=qa.ROOT/'design/verification/265-studio-export.html'
        with patch.object(ft.FilePicker,'save_file',new=AsyncMock(return_value=str(output))):await studio.export(None)
        (qa.ROOT/'design/verification/265-studio-fixture.json').write_text(json.dumps(studio.book,ensure_ascii=False),encoding='utf-8')
        html=output.read_text(encoding='utf-8');assert 'data:image/png;base64,' in html and 'text-shadow:' in html
        studio.remove_material(mat);assert len(studio.book['materials'])==1
        studio.window_event(Event(type='close'));await qa.click(base.button(page,'继续编辑'));assert studio.alive
        studio.request_close();await qa.click(base.button(page,'放弃修改'))
        assert not studio.alive and page.on_resize==old_resize and page.on_keyboard_event==old_keyboard
        assert page.window.full_screen==old_full
        assert len(journal.get_book(book_id)['materials'])==2
        await qa.click(base.button(page,'打开手账'))
        studio=next(v.data['notebook_studio'] for v in page.views if isinstance(v.data,dict) and 'notebook_studio' in v.data)
        page.window.width=1080;page.window.height=760;page.update();await asyncio.sleep(.5)
        studio.category.value='text';studio.refresh();await qa.screenshot(page,'265-studio-small')
        studio.request_close()
        if studio.alive:await qa.click(base.button(page,'保存并退出'))
        print('STUDIO_NATIVE: PASS (creation, three panels, fullscreen, text effects, drag/resize, lock, transparent import, library persistence, undo/redo, multi-page, save/reopen, export, discard, handler restore, 1080x760)',flush=True)
        passed=True
    except Exception:
        import traceback;traceback.print_exc()
    finally:await page.window.destroy()

if __name__=='__main__':
    ft.run(run);qa.temp.cleanup();sys.exit(0 if passed else 1)

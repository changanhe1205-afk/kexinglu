"""Real Windows mouse drag into a Flet DragTarget; isolated notebook profile."""
import asyncio
import ctypes
from ctypes import wintypes
from copy import deepcopy
from types import SimpleNamespace as Event
import sys
import time
from PIL import Image, ImageChops, ImageGrab
import flet as ft
import travel_journal_smoke as base
import travel_journal as journal
from notebook_materials import catalog

qa=base.qa;passed=False;u=ctypes.windll.user32
u.SetProcessDPIAware()

async def run(page):
    global passed
    try:
        qa.app.main(page);page.window.left=20;page.window.top=20;page.update();await asyncio.sleep(.6)
        await qa.click(qa.nav(page,'旅行日志'));await qa.click(base.button(page,'旅行手账'))
        await qa.click(base.button(page,'新建空白手账'))
        assert not any(isinstance(c,ft.Dropdown) and c.label=='创作方式' for c in qa.walk(page))
        await qa.click(base.button(page,'开始创作'))
        studio=next(v.data['notebook_studio'] for v in page.views if isinstance(v.data,dict) and 'notebook_studio' in v.data)
        assert page.window.full_screen, 'New notebook must open fullscreen'
        studio.fullscreen();await asyncio.sleep(.5)
        assert len(catalog('sticker'))==48 and len(catalog('tape'))==12 and len(catalog('note'))==8
        u.SetForegroundWindow(u.FindWindowW(None,'客行录'));await asyncio.sleep(.4)
        await qa.screenshot(page,'267-studio-before-drag')
        handle=u.FindWindowW(None,'客行录');rect=wintypes.RECT()
        ctypes.windll.dwmapi.DwmGetWindowAttribute(handle,9,ctypes.byref(rect),ctypes.sizeof(rect))
        scale=u.GetDpiForWindow(handle)/96
        shot=ImageGrab.grab(bbox=(rect.left,rect.top,rect.right,rect.bottom)).convert('RGB')
        diff=ImageChops.difference(shot,Image.new('RGB',shot.size,'#FAF7EF'))
        mask=diff.convert('L').point(lambda v:255 if v==0 else 0)
        from PIL import ImageDraw
        ImageDraw.Draw(mask).rectangle((0,0,int(shot.width*.25),shot.height),fill=0)
        ImageDraw.Draw(mask).rectangle((int(shot.width*.78),0,shot.width,shot.height),fill=0)
        box=mask.getbbox();assert box
        target=(rect.left+(box[0]+box[2])//2,rect.top+(box[1]+box[3])//2)
        source=(rect.left+round(62*scale),rect.top+round(416*scale))
        before=len(studio.design['elements'])
        material_controls=tuple(studio.materials.controls)
        mounted_paper=studio.canvas.content
        u.SetForegroundWindow(handle);u.SetCursorPos(*source);await asyncio.sleep(.2)
        u.mouse_event(0x0002,0,0,0,0)
        for step in range(1,31):
            u.SetCursorPos(round(source[0]+(target[0]-source[0])*step/30),round(source[1]+(target[1]-source[1])*step/30))
            await asyncio.sleep(.025)
        released=time.perf_counter();u.mouse_event(0x0004,0,0,0,0)
        while len(studio.design['elements'])==before and time.perf_counter()-released<2:await asyncio.sleep(.01)
        print('DROP_MODEL_LATENCY_MS:',round((time.perf_counter()-released)*1000),flush=True)
        await asyncio.sleep(.25)
        assert len(studio.design['elements'])==before+1, (source,target,box)
        assert time.perf_counter()-released<1, 'Drop event queue exceeded one second'
        assert tuple(studio.materials.controls)==material_controls and studio.canvas.content is mounted_paper
        obj=studio.current()
        assert abs(obj['x']+obj['w']/2-210)<12 and abs(obj['y']+obj['h']/2-290)<12, (source,target,box,scale,{k:obj[k] for k in ['x','y','w','h']})
        # Scale-aware placement and boundary checks on the same acceptance path.
        template=deepcopy(catalog('tape')[0][1]);studio.set_zoom(1.6)
        studio.accept_material(Event(src=Event(data={'material_element':template}),local_position=ft.Offset(studio.width*.95,studio.width*580/420*.98)))
        obj=studio.current();assert obj['x']+obj['w']<=420 and obj['y']+obj['h']<=580
        assert template==catalog('tape')[0][1]
        count=len(studio.design['elements']);studio.accept_material(Event(src=Event(data={'material_element':template}),local_position=ft.Offset(-10,20)))
        assert len(studio.design['elements'])==count
        studio.undo();assert len(studio.design['elements'])==count-1
        studio.set_zoom(1);studio.select(-1)
        await qa.screenshot(page,'267-studio-dragged')
        studio.search.value='相机';studio.paint_materials();page.update()
        assert len([c for c in qa.walk(page) if isinstance(c,ft.Draggable)])==3
        studio.search.value='';studio.choose_category('note');studio.append(deepcopy(catalog('note')[0][1]))
        studio.change('x',60);studio.change('y',345);studio.select(-1);studio.choose_category('sticker')
        assert studio.save();assert len(journal.get_book(studio.book['id'])['pages'][0]['design']['elements'])==2
        await qa.screenshot(page,'267-studio-materials')
        studio.choose_category('daily')
        assert len([c for c in qa.walk(studio.materials) if isinstance(c,ft.Draggable)])==12
        await qa.screenshot(page,'267-studio-daily')
        studio.choose_category('travel');await qa.screenshot(page,'267-studio-travel')
        studio.choose_category('frame');await qa.screenshot(page,'267-studio-frames')
        studio.choose_category('sticker');studio.browse_materials(3)
        assert studio.material_page==3
        studio.search.value='相机';studio.search_materials(None)
        assert studio.material_page==0 and len([c for c in qa.walk(studio.materials) if isinstance(c,ft.Draggable)])==3
        # A realistically crowded page must not recreate artwork or the palette
        # for every mouse event. Timings cover Python/Flet patch generation.
        for n in range(60):
            extra=deepcopy(catalog('daily')[n%12][1]);extra.update(x=(n%6)*60,y=(n//6)*48,w=38,h=38)
            studio.design['elements'].append(extra)
        studio.selected=len(studio.design['elements'])-1;studio.refresh()
        await asyncio.sleep(.4)
        palette=tuple(studio.materials.controls);paper=studio.canvas.content
        node=next(c for c in paper.content.controls if c.data=={'collage_element':studio.selected})
        handle=next(c for c in paper.content.controls if c.data=='resize_handle')
        node.content.on_pan_start(Event());times=[]
        for n in range(90):
            started=time.perf_counter()
            node.content.on_pan_update(Event(local_delta=ft.Offset(-1 if n<45 else 1,-.5 if n<45 else .5)))
            times.append((time.perf_counter()-started)*1000)
            await asyncio.sleep(.016)
        node.content.on_pan_end(Event())
        assert studio.canvas.content is paper and tuple(studio.materials.controls)==palette
        assert next(c for c in paper.content.controls if c.data=='resize_handle') is handle
        studio.change('rotation',15)
        assert studio.canvas.content is paper, 'Style changes recreated the entire paper'
        p95=sorted(times)[int(len(times)*.95)]
        print('62_ELEMENT_MOVE_PATCH_MS: median=',round(sorted(times)[45],2),'p95=',round(p95,2),flush=True)
        assert p95<32, 'Movement processing cannot keep up with drag events'
        assert studio.save();studio.request_close();passed=True
        print('REAL_MOUSE_MATERIAL_DROP: PASS (auto fullscreen, bounded palette, stable mounted controls, center placement, zoom, edge clamp, outside rejected, undo, pagination, search, save)',flush=True)
    except Exception:
        import traceback;traceback.print_exc()
    finally:
        u.mouse_event(0x0004,0,0,0,0)
        await page.window.destroy()

if __name__=='__main__':
    ft.run(run);qa.temp.cleanup();sys.exit(0 if passed else 1)

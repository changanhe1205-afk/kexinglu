"""Isolated real Flet tests of collection create/edit/flip/reduced motion flows."""
import asyncio
import sys
from types import SimpleNamespace as Event
import desktop_design_smoke as qa
import flet as ft
import database as db
import food_db
import config
from collection_motion import FlipCard
passed=False

# Traverse declared live children, excluding Flet's historical/private references.
from dataclasses import fields
from flet.controls.base_control import BaseControl
def live_walk(root):
    seen, stack = set(), [root]
    while stack:
        obj=stack.pop()
        if isinstance(obj,BaseControl):
            if id(obj) in seen or getattr(obj,'visible',True) is False: continue
            if isinstance(obj,ft.AlertDialog) and not obj.open: continue
            seen.add(id(obj)); yield obj
            stack.extend(getattr(obj,f.name) for f in fields(obj) if f.name != 'data')
        elif isinstance(obj,(list,tuple)): stack.extend(obj)
        elif isinstance(obj,dict): stack.extend(obj.values())
qa.walk=live_walk

def field(page,label):
    return next(c for c in qa.walk(page) if isinstance(c,ft.TextField) and c.label==label)
def button(page,label):
    return next(c for c in qa.walk(page) if isinstance(c,(ft.TextButton,ft.FilledButton,ft.OutlinedButton)) and c.content==label)
def card(page):
    return next(c for c in qa.walk(page) if isinstance(c,FlipCard))
def input_text(page,label,text):
    c=field(page,label);c.value=text
    if c.on_change: c.on_change(Event(control=c))

async def run(page):
    global passed
    try:
        config.set("collection_motion",False) # Old saved switch must no longer suppress animation.
        qa.app.main(page)
        page.window.left=35;page.window.top=35
        import ctypes
        ctypes.windll.user32.SetCursorPos(5,5)
        page.update()
        db.init_db()
        for title in ('海边的午后','未完成的告别'):
            db.add_movie(dict(title=title,kind='电影',genre='剧情',watch_date='2026-10-05',rating=4,
                review='平静的镜头里藏着细小的告别。',poster=''))
        await qa.click(qa.nav(page,'影视收藏'))
        await qa.click(button(page,'添加影视'))
        input_text(page,'片名','雨中的车站')
        # Keep the existing form labels and save through its real callback.
        review=next(c for c in qa.walk(page) if isinstance(c,ft.TextField) and c.multiline)
        review.value='在那个下着雨的车站，人物的沉默比台词更有力量。看完之后，仍记得远去的列车。'
        await qa.click(button(page,'保存'))
        await asyncio.sleep(.08)
        c=card(page)
        await asyncio.sleep(1.0)
        assert len(db.list_movies())==3
        assert not c.busy and c.surface.rotate==0
        await asyncio.sleep(3)
        await qa.screenshot(page,'250-movie-front')
        c=button(page,'翻面看感想').on_click.__self__
        import ctypes
        from ctypes import wintypes
        from PIL import ImageGrab
        rect=wintypes.RECT()
        hwnd=ctypes.windll.user32.FindWindowW(None,'客行录')
        ctypes.windll.dwmapi.DwmGetWindowAttribute(hwnd,9,ctypes.byref(rect),ctypes.sizeof(rect))
        frames=[]
        def capture():
            frame=ImageGrab.grab(bbox=(rect.left,rect.top,rect.right,rect.bottom))
            frame.thumbnail((960,720)); frames.append(frame)
        capture()
        turning=asyncio.create_task(c.turn())
        await asyncio.sleep(.05)
        assert c.busy and c.surface.scale.scale_x==.035
        for _ in range(12):
            capture(); await asyncio.sleep(.04)
        await turning
        frames[0].save(qa.ROOT/'design/movie-motion.gif',save_all=True,append_images=frames[1:],duration=[650]+[65]*11+[1000],loop=0)
        assert c.back_visible and not c.busy
        await qa.screenshot(page,'250-movie-back')
        from unittest.mock import patch
        with patch('collection_motion.motion_enabled',return_value=False):
            await c.turn()
        assert not c.back_visible and not c.busy
        assert not any(isinstance(x,ft.Switch) and x.label=='收藏动效' for x in qa.walk(page))
        c.hover(Event(data='true'))
        assert c.surface.rotate < 0
        c.hover(Event(data='false'))
        assert c.surface.rotate == 0
        await qa.click(button(page,'沉浸阅读'))
        assert button(page,'返回影库')
        await qa.screenshot(page,'250-movie-reader')
        await qa.click(button(page,'返回影库'))
        await qa.click(next(c for c in qa.walk(page) if isinstance(c,ft.IconButton) and c.tooltip=='编辑收藏'))
        input_text(page,'片名','雨中的车站 · 重看')
        await qa.click(button(page,'保存'))
        await asyncio.sleep(.6)
        assert len(db.list_movies())==3 and any(m['title'].endswith('重看') for m in db.list_movies())
        await qa.click(next(x for x in qa.walk(page) if isinstance(x,ft.IconButton) and x.tooltip=='下一部'))
        await asyncio.sleep(.9)
        assert any(isinstance(x,ft.Text) and x.value=='02 / 03' for x in qa.walk(page))
        await qa.click(next(x for x in qa.walk(page) if isinstance(x,ft.Container) and x.tooltip=='查看收藏：海边的午后'))
        await asyncio.sleep(.9)
        assert any(isinstance(x,ft.Text) and x.value=='03 / 03' for x in qa.walk(page))
        first=next(x for x in qa.walk(page) if isinstance(x,ft.Container) and x.tooltip=='查看收藏：雨中的车站 · 重看')
        last=next(x for x in qa.walk(page) if isinstance(x,ft.Container) and x.tooltip=='查看收藏：海边的午后')
        pending=asyncio.create_task(qa.click(first))
        await asyncio.sleep(.04)
        await qa.click(last)
        await pending
        assert any(isinstance(x,ft.Text) and x.value=='03 / 03' for x in qa.walk(page))
        await qa.click(button(page,'剧集'))
        assert not any(isinstance(x,FlipCard) for x in qa.walk(page))
        await qa.click(button(page,'全部'))
        search=next(x for x in qa.walk(page) if isinstance(x,ft.TextField) and '搜索' in (x.hint_text or ''))
        search.value='不存在的影片';search.on_change(Event(control=search))
        assert not any(isinstance(x,FlipCard) for x in qa.walk(page))
        search.value='';search.on_change(Event(control=search))
        assert any(isinstance(x,FlipCard) for x in qa.walk(page))
        print('PASS movies: add/edit, index/next selection, empty filter/search, flip, reduced motion; old switch ignored',flush=True)
        await qa.click(qa.nav(page,'食光小记'))
        assert not any(isinstance(x,ft.Switch) and x.label=='收藏动效' for x in qa.walk(page))
        input_text(page,'名称','生椰拿铁')
        input_text(page,'店铺 / 地点','街角咖啡')
        input_text(page,'价格','18')
        input_text(page,'感想','椰香很轻，适合慢慢喝。今天和朋友聊了很久。')
        await qa.click(next(c for c in qa.walk(page) if isinstance(c,ft.FilledButton) and c.content=='饮料'))
        await qa.click(next(c for c in qa.walk(page) if isinstance(c,ft.IconButton) and c.tooltip=='4 星'))
        assert not food_db.list_food(), 'Live preview must not write a record'
        await qa.click(button(page,'保存收藏'))
        await asyncio.sleep(.6)
        assert len(food_db.list_food())==1
        assert food_db.list_food()[0]['rating']==4
        await asyncio.sleep(3)
        await qa.screenshot(page,'250-food-photo')
        await qa.click(button(page,'翻看照片 / 小票'))
        assert card(page).back_visible
        await qa.screenshot(page,'250-food-receipt')
        input_text(page,'价格','20')
        await qa.click(button(page,'保存收藏'))
        await asyncio.sleep(.6)
        assert len(food_db.list_food())==1 and food_db.list_food()[0]['price']=='20'
        await qa.click(button(page,'再记一份'))
        input_text(page,'名称','热汤面')
        await qa.click(button(page,'保存收藏'))
        await asyncio.sleep(.6)
        assert len(food_db.list_food())==2
        print('PASS food: live draft, save, receipt flip, edit without duplicate, new record',flush=True)
        await qa.click(qa.nav(page,'我的'))
        await qa.click(next(c for c in qa.walk(page) if isinstance(c,ft.Container) and c.tooltip=='应用主题：午夜蓝'))
        await qa.click(qa.nav(page,'食光小记'))
        await qa.click(button(page,'翻看照片 / 小票'))
        await qa.screenshot(page,'250-food-dark')
        page.window.width=1080;page.window.height=700
        await asyncio.sleep(.7)
        await qa.screenshot(page,'250-food-small')
        await qa.click(qa.nav(page,'影视收藏'))
        await qa.screenshot(page,'250-movie-small')
        await qa.click(button(page,'翻面看感想'))
        await qa.screenshot(page,'250-movie-small-back')
        passed=True
        print('COLLECTIONS_RESULT: PASS',flush=True)
    except Exception:
        import traceback;traceback.print_exc()
    finally:
        await page.window.destroy()

if __name__=='__main__':
    ft.run(run)
    qa.temp.cleanup()
    sys.exit(0 if passed else 1)

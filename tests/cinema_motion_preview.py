"""Capture the actual native sleeve, switch and flip animations with temporary records."""
import asyncio
import ctypes
from ctypes import wintypes
from types import SimpleNamespace as Event
from PIL import ImageGrab
import collection_experience_smoke as ui
qa=ui.qa
ft=ui.ft

async def run(page):
    try:
        qa.app.main(page)
        page.window.left=35;page.window.top=35;page.update()
        ui.db.init_db()
        for title in ('海边的午后','雨中的车站'):
            ui.db.add_movie(dict(title=title,kind='电影',genre='剧情',watch_date='2026-10-05',rating=4,
                review='那些没有说出口的话，在散场以后，依然留在心里。',poster=''))
        await qa.click(qa.nav(page,'影视收藏'))
        await asyncio.sleep(.7)
        c=ui.card(page)
        hwnd=ctypes.windll.user32.FindWindowW(None,'客行录')
        ctypes.windll.user32.SetForegroundWindow(hwnd)
        ctypes.windll.user32.SetCursorPos(5,5)
        rect=wintypes.RECT()
        ctypes.windll.dwmapi.DwmGetWindowAttribute(hwnd,9,ctypes.byref(rect),ctypes.sizeof(rect))
        frames=[]
        async def actions():
            await asyncio.sleep(.25)
            c.hover(Event(data='true'));await asyncio.sleep(.4)
            c.hover(Event(data='false'));await asyncio.sleep(.25)
            await c.celebrate()
            await qa.click(next(x for x in qa.walk(page) if isinstance(x,ft.IconButton) and x.tooltip=='下一部'))
            await asyncio.sleep(1)
            await qa.click(ui.button(page,'翻面看感想'))
            await asyncio.sleep(.5)
        sequence=asyncio.create_task(actions())
        while not sequence.done():
            frame=ImageGrab.grab(bbox=(rect.left,rect.top,rect.right,rect.bottom))
            frame.thumbnail((960,720));frames.append(frame)
            await asyncio.sleep(.06)
        await sequence
        frames[0].save(qa.ROOT/'design/cinema-effects.gif',save_all=True,
            append_images=frames[1:],duration=85,loop=0)
        print('NATIVE_CINEMA_EFFECTS_CAPTURE: PASS',flush=True)
    finally:
        await page.window.destroy()

if __name__=='__main__':
    ft.run(run)
    qa.temp.cleanup()

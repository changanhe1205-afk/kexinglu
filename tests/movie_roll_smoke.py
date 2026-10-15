"""Native automatic movie rotation with isolated records and lifecycle checks."""
import asyncio
import sys
import time
import ctypes
from types import SimpleNamespace as Event
from unittest.mock import patch
import travel_journal_smoke as base
import movie_view
import database as db
import flet as ft

qa=base.qa;passed=False

async def wait_until(predicate,timeout=3):
    start=time.monotonic()
    while not predicate():
        assert time.monotonic()-start<timeout,'Rotation did not finish'
        await asyncio.sleep(.04)

async def run(page):
    global passed
    try:
        ctypes.windll.user32.SetCursorPos(5,5)
        qa.app.main(page);db.init_db()
        for i in range(6):db.add_movie(dict(title=f'轮播作品 {i+1}',kind='剧集' if i==5 else '电影',rating=4,review='留在散场后的回忆。',poster='',genre='剧情',watch_date='2026-10-08'))
        await qa.click(qa.nav(page,'影视收藏'))
        body=next(c for c in qa.walk(page) if isinstance(c.data,dict) and 'movie_rolling' in c.data)
        state=body.data['movie_rolling'];focus=body.data['movie_focus']
        ids=[m['id'] for m in focus['items']];assert focus['id']==ids[0]
        state['hover']=False
        with patch('movie_view.motion_enabled',return_value=True):
            await wait_until(lambda:focus['id']==ids[1],8)
            await wait_until(lambda:not state['busy'])
            await qa.screenshot(page,'2611-cinema-rolling')
            # Subsequent transitions use accelerated deadlines; same actual timer.
            rows=next(c for c in qa.walk(body) if isinstance(c,ft.ListView) and c.controls and c.controls[0].data==ids[0])
            mounted=tuple(rows.controls)
            offsets=[];rows.on_scroll=lambda e:offsets.append(e.pixels);rows.update()
            with patch.object(db,'list_movies',side_effect=AssertionError('Autoplay must not query SQLite')):
                for target in ids[2:]+ids[:1]:
                    await wait_until(lambda:not focus['card'].busy)
                    state['hover']=False;state['deadline']=0
                    await wait_until(lambda:focus['id']==target)
                    await wait_until(lambda:not state['busy'])
            assert tuple(rows.controls)==mounted
            assert offsets and max(offsets)>0, 'Directory did not actually scroll'
            for reason in ('hover','search'):
                state[reason]=True;state['deadline']=0;before=focus['id'];await asyncio.sleep(.5)
                assert focus['id']==before;state[reason]=False
            focus['card'].back_visible=True;state['deadline']=0;await asyncio.sleep(.5)
            assert focus['id']==before;focus['card'].back_visible=False
            await qa.click(next(c for c in qa.walk(page) if isinstance(c,ft.IconButton) and c.tooltip=='编辑收藏'));state['deadline']=0;await asyncio.sleep(.5)
            assert focus['id']==before
            page.pop_dialog();await asyncio.sleep(.4)
            with patch('movie_view.motion_enabled',return_value=False):
                state['deadline']=0;await asyncio.sleep(.5);assert focus['id']==before
            next_button=next(c for c in qa.walk(body) if isinstance(c,ft.IconButton) and c.tooltip=='下一部')
            await qa.click(next_button);assert focus['id']==ids[1]
            await qa.click(base.button(page,'剧集'))
            assert len(focus['items'])==1;before=focus['id'];state['deadline']=0;await asyncio.sleep(.5);assert focus['id']==before
            search=next(c for c in qa.walk(body) if isinstance(c,ft.TextField) and c.hint_text=='搜索片名 / 题材 / 感想…')
            search.value='不存在的影片';search.on_change(Event(control=search));await asyncio.sleep(.3)
            assert not focus['items']
            task=state['task'];await qa.click(qa.nav(page,'首页'));await asyncio.sleep(.3)
            assert not state['active'] and task.done()
        passed=True
        print('MOVIE_AUTO_ROLL: PASS (6s default, ordered wraparound, no database reload or directory rebuild, hover/search/back/dialog pause, reduced motion, manual next, single/empty result, cancellation on navigation)',flush=True)
    except Exception:
        import traceback;traceback.print_exc()
    finally:await page.window.destroy()

if __name__=='__main__':
    ft.run(run);qa.temp.cleanup();sys.exit(0 if passed else 1)

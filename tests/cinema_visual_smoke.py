"""Real poster, dark theme and compact window checks for the screening room."""
import asyncio
import ctypes
import sys
import travel_journal_smoke as base
import database as db
import flet as ft
qa=base.qa;passed=False

async def run(page):
    global passed
    try:
        qa.app.main(page);db.init_db()
        for title,kind,poster,review in [
            ('雾里的山，远处的你','电影','bg_shanxing.png','有些电影像一封迟来的信。散场之后，山间的风仍在耳边。'),
            ('慢慢经过的夏天','剧集','bg_mint.jpg','喜欢那些没有说出口的对白，也喜欢日常里不动声色的温柔。'),
            ('雨中的车站','电影','','列车向前，故事留在身后。')]:
            db.add_movie(dict(title=title,kind=kind,genre='剧情',watch_date='2026-10-09',rating=5,
                review=review,poster=str(qa.ROOT/'assets'/poster) if poster else ''))
        await qa.click(qa.nav(page,'影视收藏'))
        await qa.click(next(c for c in qa.walk(page) if isinstance(c,ft.Container) and c.tooltip=='查看收藏：雾里的山，远处的你'))
        body=next(c for c in qa.walk(page) if isinstance(c.data,dict) and 'movie_rolling' in c.data)
        body.data['movie_rolling']['hover']=True
        ctypes.windll.user32.SetForegroundWindow(ctypes.windll.user32.FindWindowW(None,'客行录'))
        await qa.screenshot(page,'2611-cinema-poster')
        page.window.width=1080;page.window.height=760;page.update();await asyncio.sleep(.5)
        await qa.screenshot(page,'2611-cinema-small')
        await qa.click(qa.nav(page,'我的'))
        await qa.click(next(c for c in qa.walk(page) if isinstance(c,ft.Container) and c.tooltip=='应用主题：午夜蓝'))
        await qa.click(qa.nav(page,'影视收藏'))
        await qa.screenshot(page,'2611-cinema-dark')
        passed=True;print('CINEMA_VISUAL: PASS (real poster, missing poster, 1080x760, dark theme)',flush=True)
    except Exception:
        import traceback;traceback.print_exc()
    finally:await page.window.destroy()

if __name__=='__main__':
    ft.run(run);qa.temp.cleanup();sys.exit(0 if passed else 1)

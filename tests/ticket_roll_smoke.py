"""Actual Flet ticket rotation; drafts and railway tickets must stay put."""
import asyncio
import ctypes
import sys
from types import SimpleNamespace as Event
from unittest.mock import patch
import travel_journal_smoke as base
import ticket_editing_smoke as editing
import ticket_db as db
import flet as ft
qa=base.qa;passed=False

async def until(check,timeout=3):
    async with asyncio.timeout(timeout):
        while not check():await asyncio.sleep(.04)

async def run(page):
    global passed
    try:
        ctypes.windll.user32.SetCursorPos(5,5)
        for i,(start,end,code) in enumerate([('北京首都国际机场','杭州萧山国际机场','CA1701'),('徐州观音国际机场','广州白云国际机场','CZ3258'),('上海浦东国际机场','成都天府国际机场','MU5401')]):
            db.add_ticket(vehicle='飞机',from_city=start,to_city=end,code=code,depart_date=f'2026-10-0{i+1}',price='680',style='classic')
        rail=db.add_ticket(vehicle='高铁',from_city='杭州东',to_city='上海虹桥',code='G123',depart_date='2026-10-04')
        original=db.list_tickets()
        qa.app.main(page);await qa.click(qa.nav(page,'旅程票根'))
        body=next(c for c in qa.walk(page) if isinstance(c.data,dict) and 'ticket_rolling' in c.data)
        state=body.data['ticket_rolling'];current=body.data['ticket_current'];draft=body.data['ticket_preview'];flip=body.data['ticket_flip']
        ids=[t['id'] for t in state['items']];assert current['id']==ids[0]
        with patch('ticket_view.motion_enabled',return_value=True):
            await until(lambda:current['id']==ids[1],8);await until(lambda:not state['busy'])
            await qa.screenshot(page,'2610-ticket-carousel')
            for target in (ids[2],ids[0]):
                state['deadline']=0;await until(lambda:current['id']==target);await until(lambda:not state['busy'])
            for reason in ('hover','form_hover','focus'):
                state[reason]=True;state['deadline']=0;await asyncio.sleep(.4);assert current['id']==ids[0]
                state[reason]=None if reason=='focus' else False
            flip['back']=True;state['deadline']=0;await asyncio.sleep(.4);assert current['id']==ids[0];flip['back']=False
            # Typing during the outgoing animation must abort the transition.
            state['deadline']=0;await until(lambda:state['busy'])
            editing.text(page,'票价（CNY）','1234') if any(isinstance(c,ft.TextField) and c.label=='票价（CNY）' for c in qa.walk(page)) else editing.text(page,'票价','1234')
            await until(lambda:not state['busy']);assert draft['draft'] and current['id']==ids[0]
            state['deadline']=0;await asyncio.sleep(.5);assert current['id']==ids[0]
            assert db.list_tickets()==original, 'Playback changed saved ticket data'
            await qa.click(base.button(page,'新增机票'))
            await qa.click(base.button(page,'放弃修改并新建'))
            assert current['id'] is None and draft['draft']
            state['deadline']=0;await asyncio.sleep(.4);assert current['id'] is None
            await qa.click(next(c for c in qa.walk(page) if isinstance(c,ft.Container) and c.tooltip=='票根分类：铁路'))
            route=next(c for c in qa.walk(page) if isinstance(c,ft.Container) and c.on_click and qa.has_text(c,'杭州东 → 上海虹桥'))
            await qa.click(route);state['deadline']=0;await asyncio.sleep(.4);assert current['id']==rail
            await qa.click(next(c for c in qa.walk(page) if isinstance(c,ft.Container) and c.tooltip=='票根分类：飞机'))
            assert current['id']==ids[0]
            with patch('ticket_view.motion_enabled',return_value=False):
                state['deadline']=0;await asyncio.sleep(.4);assert current['id']==ids[0]
            await qa.click(next(c for c in qa.walk(page) if isinstance(c,ft.IconButton) and c.tooltip=='下一张机票'))
            assert current['id']==ids[1]
            next(c for c in qa.walk(page) if isinstance(c,ft.IconButton) and c.tooltip=='放大票面').on_click(None)
            state['deadline']=0;await asyncio.sleep(.4);assert current['id']==ids[1]
            page.pop_dialog();await asyncio.sleep(.3)
            task=state['task'];await qa.click(qa.nav(page,'首页'));await asyncio.sleep(.2)
            assert not state['active'] and task.done()
            for ticket in db.list_tickets():db.delete_ticket(ticket['id'])
            await qa.click(qa.nav(page,'旅程票根'))
            body=next(c for c in qa.walk(page) if isinstance(c.data,dict) and 'ticket_rolling' in c.data)
            assert not body.data['ticket_rolling']['items'] and body.data['ticket_current']['id'] is None
        passed=True;print('TICKET_AUTO_ROLL: PASS (6s rotation, ordered loop, hover/focus/back pause, draft during animation, new ticket protection, railway excluded, no data writes, leave cancellation)',flush=True)
    except Exception:
        import traceback;traceback.print_exc()
    finally:await page.window.destroy()

if __name__=='__main__':
    ft.run(run);qa.temp.cleanup();sys.exit(0 if passed else 1)

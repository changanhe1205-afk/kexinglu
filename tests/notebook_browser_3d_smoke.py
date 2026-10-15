"""Use installed Chrome's CDP for an offline export; no browser dependency install."""
import base64
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from websockets.sync.client import connect
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import travel_journal as journal

root=Path(__file__).resolve().parents[1];out=root/'design/verification'
book=journal.new_book([dict(id=i,title=f'第 {i} 程 · 沿湖慢行',city='杭州',visit_date=f'2026-10-0{i}',
    note='把路上的片刻留在纸上。\n'+'长页仍可以上下滚动阅读。\n'*15,photos=[]) for i in range(1,6)],'山野之间，慢慢走')
if '--collage' in sys.argv:
    from notebook_collage import make_design
    for item,layout,paper in zip(book['pages'],('daily','postcard','garden','film','memo'),('blue','rose','sage','grid','kraft')):
        item['design']=make_design(item,layout,paper)
if '--studio' in sys.argv:
    from copy import deepcopy
    book=json.loads((out/'265-studio-fixture.json').read_text(encoding='utf-8'))
    book['pages']=[deepcopy(book['pages'][0]) for _ in range(5)]
file=journal.export_html(book,out/('265-studio-browser.html' if '--studio' in sys.argv else '261-notebook-browser.html'))
with tempfile.TemporaryDirectory(prefix='notebook-cdp-') as profile:
    with socket.socket() as probe:probe.bind(('127.0.0.1',0));port=probe.getsockname()[1]
    proc=subprocess.Popen(['C:/Program Files/Google/Chrome/Application/chrome.exe','--headless=new',
        '--disable-gpu','--no-first-run','--disable-background-networking','--proxy-server=http://127.0.0.1:9',
        f'--remote-debugging-port={port}',f'--user-data-dir={profile}','--window-size=1200,900','about:blank'],
        stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
        for _ in range(60):
            try:
                with opener.open(f'http://127.0.0.1:{port}/json',timeout=1) as response:tabs=json.load(response)
                tabs=[tab for tab in tabs if tab['type']=='page']
                if tabs:break
            except OSError:time.sleep(.1)
        with connect(tabs[0]['webSocketDebuggerUrl'],max_size=15_000_000) as ws:
            sequence=0;errors=[]
            def call(method,params=None):
                global sequence
                sequence+=1;ws.send(json.dumps(dict(id=sequence,method=method,params=params or {})))
                while True:
                    result=json.loads(ws.recv(timeout=10))
                    if result.get('method')=='Runtime.exceptionThrown':errors.append(result)
                    if result.get('id')==sequence:
                        assert 'error' not in result,result
                        return result.get('result',{})
            def js(expression):
                result=call('Runtime.evaluate',dict(expression=expression,returnByValue=True,awaitPromise=True))
                assert 'exceptionDetails' not in result,result
                return result.get('result',{}).get('value')
            def pause():js('new Promise(r=>setTimeout(r,850))')
            def screenshot(name):
                data=call('Page.captureScreenshot',dict(format='png'))['data']
                (out/name).write_bytes(base64.b64decode(data))
            call('Runtime.enable');call('Page.enable');call('Page.navigate',dict(url=file.as_uri()));pause()
            assert js('document.title')==book['title'],(js('document.title'),js('location.href'))
            assert js('window.notebook.index')==0
            assert js('document.querySelector("#prev").disabled')
            screenshot('261-html-cover.png')
            js('document.querySelector("#next").click();document.querySelector("#next").click()')
            js('new Promise(r=>setTimeout(r,200))')
            assert js('window.notebook.busy')
            assert js('getComputedStyle(document.querySelector(".flipper")).transform')!='none'
            screenshot('261-html-turning.png');pause()
            assert js('window.notebook.index')==1
            if '--collage' in sys.argv or '--studio' in sys.argv:
                assert js('document.querySelector("#left .collage-sheet") !== null')
                assert js('document.querySelectorAll("#left .scrap").length')>=(4 if '--studio' in sys.argv else 7)
                if '--studio' in sys.argv:
                    assert js('Array.from(document.querySelectorAll("#left .scrap img")).every(i=>i.complete && i.naturalWidth>0)')
                    assert js('getComputedStyle(document.querySelectorAll("#left .scrap")[1]).textShadow')!='none'
                    assert js('document.querySelector("#left .scrap-image img").src.startsWith("data:image/png;base64,")')
                    screenshot('265-studio-browser.png')
                screenshot('264-html-collage.png')
            else:
                assert js('document.querySelector("#left .paper").scrollHeight > document.querySelector("#left .paper").clientHeight')
            js('document.activeElement.blur()');call('Input.dispatchKeyEvent',dict(type='keyDown',key='ArrowRight',code='ArrowRight'));pause()
            assert js('window.notebook.index')==2
            call('Input.dispatchMouseEvent',dict(type='mousePressed',x=700,y=350,button='left',clickCount=1))
            call('Input.dispatchMouseEvent',dict(type='mouseMoved',x=860,y=350,button='left',buttons=1))
            call('Input.dispatchMouseEvent',dict(type='mouseReleased',x=860,y=350,button='left',clickCount=1));pause()
            assert js('window.notebook.index')==1
            js("document.querySelector('#contents').click();document.querySelectorAll('#toc a')[5].click()");pause()
            assert js('window.notebook.index')==3 and js('document.querySelector("#next").disabled')
            assert js('document.querySelector("#right").innerText.includes("旅途未完")')
            for key in journal.STYLES:
                js(f'document.querySelector("#style").value={json.dumps(key)};document.querySelector("#style").dispatchEvent(new Event("change"))')
                assert js('document.querySelector("#book").dataset.style')==key
            js('document.querySelector("#style").value="ocean";document.querySelector("#style").dispatchEvent(new Event("change"))')
            screenshot('261-html-spread.png')
            call('Emulation.setEmulatedMedia',dict(features=[dict(name='prefers-reduced-motion',value='reduce')]))
            js('document.querySelector("#prev").click()');assert js('window.notebook.index')==2
            assert not js('window.notebook.busy')
            call('Emulation.setDeviceMetricsOverride',dict(width=390,height=844,deviceScaleFactor=1,mobile=True))
            screenshot('261-html-mobile.png')
            assert js('document.documentElement.scrollWidth<=window.innerWidth')
            call('Emulation.setEmulatedMedia',dict(media='print'))
            assert js('getComputedStyle(document.querySelector("#source")).display')=='block'
            assert js('document.querySelectorAll("#source .paper").length')==5
            assert not errors,errors
            print('OFFLINE_3D_BROWSER: PASS (turn matrix, buttons, rapid click, keyboard, swipe, TOC, 8 styles, odd page, long text, reduced motion, mobile, print)',flush=True)
            call('Browser.close')
    finally:
        try:proc.wait(timeout=6)
        except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=5)

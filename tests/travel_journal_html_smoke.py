"""Render the portable export in a browser with a fresh, offline profile."""
from pathlib import Path
import subprocess
import sys
import tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import travel_journal as journal

root=Path(__file__).resolve().parents[1]
out=root/'design/verification'
book=journal.new_book([
    dict(id=1,title='沿湖慢行',city='杭州',visit_date='2026-10-05',
         note='湖风轻轻吹过。\n把今天值得记住的片刻，收进自己的手账。',photos=[]),
    dict(id=2,title='山间的一封信',city='黄山',visit_date='2026-10-06',
         note='下次出发前，再翻开这一页。',photos=[]),
], '走过的地方，写给自己')
file=journal.export_html(book,out/'260-notebook-sample.html')
with tempfile.TemporaryDirectory(prefix='notebook-browser-') as profile:
    browser=Path('C:/Program Files/Google/Chrome/Application/chrome.exe')
    result=subprocess.run([str(browser),'--headless=new','--disable-gpu','--no-first-run',
        '--no-default-browser-check','--disable-background-networking',
        '--proxy-server=http://127.0.0.1:9',f'--user-data-dir={profile}',
        '--window-size=1100,900',f'--screenshot={out / "260-notebook-html.png"}',
        '--dump-dom',file.as_uri()],capture_output=True,timeout=40,
        creationflags=subprocess.CREATE_NO_WINDOW)
    assert result.returncode==0,result.stderr.decode('utf-8',errors='replace')
    dom=result.stdout.decode('utf-8',errors='replace')
    assert '走过的地方，写给自己' in dom and 'href="#p2"' in dom
    assert (out/'260-notebook-html.png').stat().st_size>1000
    print('OFFLINE_BROWSER_NOTEBOOK_EXPORT: PASS')

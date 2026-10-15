"""Offline 3D notebook export; no CDN, server, or runtime download."""
from html import escape
import json
from pathlib import Path
from string import Template
import sys


def render(book):
    from travel_journal import STYLES, BINDINGS
    esc=lambda value:escape(str(value or ''),quote=True)
    leaves=[]
    for i,item in enumerate(book['pages'],1):
        if item.get('design'):
            from notebook_collage import html_canvas
            leaves.append(f'<article id="p{i}" class="paper collage-paper">'+html_canvas(item['design'])+'</article>')
            continue
        photos=''.join('<figure><img loading="lazy" src="data:image/jpeg;base64,'+esc(p['image'])+
            '"><figcaption>'+esc(p.get('caption'))+'</figcaption></figure>' for p in item['photos'] if p.get('included',True))
        leaves.append(f'<article id="p{i}" class="paper"><small>旅途手记 / {i:02d}</small>'
            f'<h2>{esc(item["title"])}</h2><p class="meta">{esc(item["place"])} · {esc(item["date"])}</p>'
            f'<div class="note">{esc(item["note"])}</div><div class="photos">{photos}</div>'
            f'<footer>客行录 · {i:02d}</footer></article>')
    contents=''.join(f'<a href="#p{i}" data-page="{i}">{i:02d}　{esc(p["title"])}</a>' for i,p in enumerate(book['pages'],1))
    styles={k:dict(paper=v[1],ink=v[2],accent=v[3],**BINDINGS[k]) for k,v in STYLES.items()}
    options=''.join(f'<option value="{k}" {"selected" if k==book["style"] else ""}>{v[0]}</option>' for k,v in STYLES.items())
    root=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent))
    return Template((root/'assets/notebook_reader.html').read_text(encoding='utf-8')).substitute(
        title=esc(book['title']),subtitle=esc(book.get('subtitle')),count=len(leaves),
        pages=''.join(leaves),contents=contents,options=options,
        styles=json.dumps(styles,ensure_ascii=False),initial=json.dumps(book['style']))

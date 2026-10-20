"""Pure desktop/mobile translation. No imports that open the user's database."""
from copy import deepcopy
import base64
import math
from pathlib import Path

TABLES = {'movie': 'movies', 'food': 'food_items', 'travel': 'travel_logs',
          'ticket': 'tickets', 'book': 'travel_notebooks'}
FIELDS = {
    'movie': {'title':'title','category':'kind','date':'watch_date','rating':'rating','note':'review','image':'poster'},
    'food': {'title':'name','place':'place','date':'eat_date','price':'price','rating':'rating','note':'note','image':'image'},
    'travel': {'title':'title','city':'city','date':'visit_date','rating':'rating','note':'note','image':'image','lon':'lon','lat':'lat'},
    'ticket': {'from':'from_city','to':'to_city','date':'depart_date','code':'code','seat':'seat','passenger':'passenger','price':'price','note':'note','image':'image'},
}
BOOK_STYLES = ['paper','ocean','kraft','rose','mono','night']

def to_shared(kind, row):
    raw = deepcopy(row)
    raw.pop('id', None)
    if kind == 'book':
        return book_to_shared(raw)
    result = {'_desktop': raw}
    for common, desktop in FIELDS[kind].items():
        result[common] = raw.get(desktop) if raw.get(desktop) is not None else ''
    if kind == 'ticket': result['mode'] = 'air' if raw.get('vehicle') == '飞机' else 'rail'
    if kind == 'travel': result['photos'] = deepcopy(raw.get('photos', []))
    return result

def to_desktop(kind, data):
    if kind == 'book': return book_to_desktop(data)
    row = deepcopy(data.get('_desktop', {}))
    row.pop('id', None)
    for common, desktop in FIELDS[kind].items():
        row[desktop] = data.get(common, '')
    if kind == 'movie': row['kind'] = row.get('kind') or '电影'
    if kind == 'food': row['kind'] = row.get('kind') or '饭菜'
    if kind == 'ticket':
        row['vehicle'] = '飞机' if data.get('mode') == 'air' else (
            '火车' if row.get('vehicle') == '火车' else '高铁')
        row.setdefault('style', 'classic')
    if kind == 'travel': row['photos'] = deepcopy(data.get('photos', []))
    return row

def book_to_shared(doc):
    result = {'title': doc.get('title','旅行手账'), '_desktop': deepcopy(doc), 'pages': []}
    style = doc.get('style', 'paper')
    result['style'] = BOOK_STYLES.index(style) if style in BOOK_STYLES else 0
    for i, page in enumerate(doc.get('pages', [])):
        design = page.get('design')
        if not design:
            # Legacy journal pages have no freeform design; expose their content.
            elements = [dict(kind='text',text=page.get('title',''),x=30,y=35,w=350,size=28),
                        dict(kind='text',text=page.get('note',''),x=30,y=100,w=350,size=18)]
            for j, photo in enumerate(page.get('photos', [])):
                if photo.get('included', True):
                    elements.append(dict(kind='photo',image=photo.get('image',''),x=30,y=230+j*35,w=250,size=24))
        else: elements = design.get('elements', [])
        converted = []
        for j, e in enumerate(elements):
            image = e.get('image')
            converted.append({
                'id': e.get('_mobile_id', f'desktop-{i}-{j}'),
                'kind': 'image' if image else ('sticker' if e.get('kind')=='sticker' else 'text'),
                'text': {'$inline': image} if image else e.get('text',''),
                'x': max(0,min(.9,float(e.get('x',30))/420)),
                'y': max(0,min(.94,float(e.get('y',30))/580)),
                'width': max(.01,min(1,float(e.get('w',220))/420)),
                'size': max(10,min(100,float(e.get('size',18))*360/420)),
                'rotation': math.radians(float(e.get('rotation',0))), '_desktop':deepcopy(e),
            })
        result['pages'].append({'elements':converted, '_desktop':deepcopy(page)})
    return result

def _embedded(value):
    if isinstance(value, dict) and '$inline' in value: return value['$inline']
    if isinstance(value, str) and len(value)<1024 and Path(value).is_file():
        return base64.b64encode(Path(value).read_bytes()).decode('ascii')
    return value

def book_to_desktop(data):
    doc = deepcopy(data.get('_desktop', {}))
    doc['title'] = data.get('title','旅行手账')
    previous = doc.get('style')
    style = int(data.get('style',0)) % len(BOOK_STYLES)
    # Preserve desktop-only style when its mobile fallback was not changed.
    doc['style'] = previous if previous and previous not in BOOK_STYLES and style==0 else BOOK_STYLES[style]
    doc['schema'] = 1
    doc.setdefault('subtitle','把路上的片刻，留在这一册。')
    pages = []
    for page in data.get('pages',[]):
        p = deepcopy(page.get('_desktop', {}))
        p.setdefault('title',doc['title']); p.setdefault('photos',[])
        design = p.setdefault('design', {'paper':'plain','elements':[]})
        elements=[]
        for e in page.get('elements',[]):
            part=deepcopy(e.get('_desktop', {}))
            original=deepcopy(part)
            changes=dict(x=float(e['x'])*420,y=float(e['y'])*580,w=float(e['width'])*420,
                         size=float(e['size'])*420/360,rotation=math.degrees(float(e['rotation'])))
            # Mobile limits must not silently crop an untouched desktop layout.
            equivalents={
                'x':max(0,min(.9,float(original.get('x',30))/420)),
                'y':max(0,min(.94,float(original.get('y',30))/580)),
                'w':max(.01,min(1,float(original.get('w',220))/420)),
                'size':max(10,min(100,float(original.get('size',18))*360/420)),
                'rotation':math.radians(float(original.get('rotation',0))),
            }
            for key,value in changes.items():
                mobile_key='width' if key=='w' else key
                if key not in original or not math.isclose(float(e[mobile_key]),equivalents[key],abs_tol=1e-8):
                    part[key]=value
            part['_mobile_id']=e['id']
            part.setdefault('h',90); part.setdefault('color','#34465B');part.setdefault('background','')
            if e['kind']=='image':
                part['kind']='photo';part['image']=_embedded(e['text']);part['text']=''
                part.setdefault('h',part['w'])
            else:
                part.setdefault('kind',e['kind']);part['text']=e['text']
            elements.append(part)
        design['elements']=elements
        pages.append(p)
    doc['pages']=pages
    def embed_images(value):
        if isinstance(value,list):return [embed_images(v) for v in value]
        if isinstance(value,dict):return {k:_embedded(v) if k=='image' else embed_images(v) for k,v in value.items()}
        return value
    return embed_images(doc)

"""Read-only maps derived from saved tickets; never creates a second route record."""
import functools
import json
import re
import unicodedata
import map_data
import flet as ft
import flet.canvas as cv
import tile_map
import route_graphics as art
import route_style
import theme

@functools.lru_cache(maxsize=1)
def airports():
    with open(map_data._asset('assets/map/airports.json'),encoding='utf8') as f:return json.load(f)

@functools.lru_cache(maxsize=1)
def rail_stations():
    with open(map_data._asset("assets/map/rail-stations.json"),encoding="utf8") as f:return json.load(f)

@functools.lru_cache(maxsize=2048)
def endpoint(text,mode):
    name=unicodedata.normalize('NFKC',text or '').strip()
    if not name:return None
    if mode=='air':
        codes=re.findall(r'(?<![A-Za-z])[A-Za-z]{3}(?![A-Za-z])',name)
        for code in codes:
            if code.upper() in airports():return dict(airports()[code.upper()],name=name,approximate=False)
        def normal(s):
            s=re.sub(r'[（(]?\s*[Tt]\d+\s*(?:航站楼)?[)）]?$', '', s)
            return s.replace('国际','').replace('机场','').replace(' ','')
        matches=[p for p in airports().values() if normal(name)==normal(p['name'])]
        if not matches and len(normal(name))>=2:
            matches=[p for p in airports().values() if normal(name) in normal(p['name'])]
        if len(matches)==1:return dict(matches[0],name=name,approximate=False)
    if mode=="rail":
        station=re.sub(r"\s+", "", name).removesuffix("站")
        if station in rail_stations():
            return dict(rail_stations()[station],name=name,approximate=False)
    table=map_data.places()
    city=name.removesuffix('市')
    if city in table:return dict(name=name,lon=table[city][0],lat=table[city][1],approximate=True)
    if mode=='rail':
        from stations_data import STATIONS_12306
        station=name.removesuffix('站')
        if station in {s[0] for s in STATIONS_12306}:
            candidates=[n for n in table if len(n)>=2 and station.startswith(n.removesuffix('市'))]
            if candidates:
                city=max(candidates,key=len)
                return dict(name=name,lon=table[city][0],lat=table[city][1],approximate=True)
    return None


def from_tickets(tickets,mode):
    routes=[];unresolved=[]
    for t in tickets:
        if t.get('vehicle') not in (('飞机',) if mode=='air' else ('高铁','火车')):continue
        points=[endpoint(t.get(key),mode) for key in ('from_city','to_city')]
        if not all(points):
            unresolved.append(t);continue
        routes.append(dict(id=t['id'],title=f"{t.get('from_city','')} → {t.get('to_city','')}",
            points=points,date=t.get('depart_date',''),code=t.get('code','')))
    return routes,unresolved


def thumbnail(tickets):
    v=tile_map.fit_view(212,126,(73.5,18.2,135.1,53.6),pad=.85)
    shapes=[];markers=[]
    style=route_style.current();palette=route_style.PALETTES[style]
    for mode,color,icon in [('air','#346C85',ft.Icons.FLIGHT),('rail','#347762',ft.Icons.TRAIN)]:
        color=palette[mode]
        routes,_=from_tickets(tickets,mode)
        seen=set()
        for r in routes:
            a,b=[v(p['lon'],p['lat']) for p in r['points']]
            if (a,b) in seen:continue
            seen.add((a,b))
            shapes.extend(art.arc_shapes(a,b,mode,small=True))
            for x,y in (a,b):
                if 0<=x<=212 and 0<=y<=126:
                    markers.append(ft.Container(left=x-9,top=y-9,width=18,height=18,border_radius=9,bgcolor=palette['marker'],border=ft.Border.all(1,color),content=ft.Icon(icon,size=11,color=color)))
    return ft.Stack(width=212,height=126,clip_behavior=ft.ClipBehavior.HARD_EDGE,
        controls=[route_style.background(v,style),cv.Canvas(shapes=shapes,width=212,height=126)]+markers)

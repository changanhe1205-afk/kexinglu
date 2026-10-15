"""Two shared map styles, independent of the application's main theme."""
import config
import flet as ft
import map_data
import json
import functools
import math
import flet.canvas as cv

PALETTES={
 'day':dict(name='航空航线图',sea='#F5F7F5',panel='#FFFFFF',text='#243E43',muted='#728689',line='#DCE5E0',air='#3C8591',rail='#598875',marker='#FFFFFF'),
 'night':dict(name='夜航地图',sea='#101E30',panel='#16283C',text='#E5EFF5',muted='#8BA4BA',line='#2A4259',air='#89D8F3',rail='#95D8BD',marker='#1B344B'),
}

def current():
    value=config.get('ticket_map_style','day')
    return value if value in PALETTES else 'day'

def set_style(value):
    if value not in PALETTES:raise ValueError('未知地图风格')
    config.set('ticket_map_style',value)

@functools.lru_cache(maxsize=1)
def land_rings():
    with open(map_data._asset('assets/map/world-land.json'),encoding='utf8') as f:
        return json.load(f)


def background(view,style):
    p=PALETTES[style];night=style=='night'
    land='#344F65' if night else '#F6F3EA'
    sea='#101E30' if night else '#D5E5EF'
    coast='#91ABBC' if night else '#829DAA'
    province_line='#7390A3' if night else '#A2ADB0'
    shapes=[]
    def path(ring,fill=False):
        # Skip whole islands/provinces outside this viewport; thin vertices in
        # screen space so panning sends compact geometry, not a giant bitmap.
        lo=min(x[0] for x in ring);hi=max(x[0] for x in ring)
        bottom=min(x[1] for x in ring);top=max(x[1] for x in ring)
        x0,y1=view(lo,bottom);x1,y0=view(hi,top)
        if x1<0 or x0>view.width or y1<0 or y0>view.height:return
        pts=[]
        for lon,lat in ring:
            point=view(lon,lat)
            if not pts or math.dist(pts[-1],point)>.9:pts.append(point)
        if len(pts)<3:return
        elements=[cv.Path.MoveTo(*pts[0])]+[cv.Path.LineTo(*point) for point in pts[1:]]+[cv.Path.Close()]
        if fill:shapes.append(cv.Path(elements=elements,paint=ft.Paint(color=land,style=ft.PaintingStyle.FILL,anti_alias=True)))
        shapes.append(cv.Path(elements=elements,paint=ft.Paint(color=coast if fill else province_line,stroke_width=1.2 if fill else .8,style=ft.PaintingStyle.STROKE,anti_alias=True)))
    for ring in land_rings():path(ring,True)
    for province in map_data.china()['provinces']:
        for ring in province['rings']:path(ring)
    labels=[];occupied=[]
    if view.width>=300:
        if view.zoom<3.5:
            entries=[('亚洲',90,48,0),('欧洲',18,51,0),('非洲',18,4,0),
                     ('北美洲',-105,43,0),('南美洲',-62,-18,0),('大洋洲',135,-26,0)]
        else:
            if view.zoom>=5.5:
                entries=[entry for entry in geographic_labels() if entry[3]>0 or entry[0] in ('北京','天津','上海','重庆','香港','澳门')]
            else:
                entries=[entry for entry in geographic_labels() if entry[3]==0]
        for name,lon,lat,rank in entries:
            x,y=view(lon,lat);width=max(38,len(name)*13+12)
            box=(x-width/2,y-10,x+width/2,y+12)
            if box[0]<6 or box[2]>view.width-6 or box[1]<6 or box[3]>view.height-6:continue
            if any(box[0]<b[2]+10 and box[2]>b[0]-10 and box[1]<b[3]+8 and box[3]>b[1]-8 for b in occupied):continue
            occupied.append(box)
            labels.append(ft.Container(left=box[0],top=box[1],width=width,height=22,
                alignment=ft.Alignment.CENTER,ignore_interactions=True,
                content=ft.Text(name,size=12 if rank==0 else 11,
                    weight=ft.FontWeight.W_600 if rank==0 else ft.FontWeight.W_400,
                    color='#EDF5FC' if night else '#405A69')))
    return ft.Container(left=0,top=0,width=view.width,height=view.height,bgcolor=sea,
        content=ft.Stack(controls=[cv.Canvas(shapes=shapes,width=view.width,height=view.height)]+labels))


@functools.lru_cache(maxsize=1)
def geographic_labels():
    with open(map_data._asset('assets/map/labels.json'),encoding='utf8') as f:
        return json.load(f)


def selector(callback,compact=False):
    selected=current();p=PALETTES[selected]
    return ft.Row(spacing=4,controls=[ft.Container(expand=True,padding=8 if compact else 10,
        border_radius=10,bgcolor=p['line'] if key==selected else p['panel'],
        tooltip='地图风格：'+PALETTES[key]['name'],on_click=lambda e,key=key:callback(key),
        content=ft.Row(spacing=5,alignment=ft.MainAxisAlignment.CENTER,controls=[
            ft.Icon(ft.Icons.LIGHT_MODE_OUTLINED if key=='day' else ft.Icons.DARK_MODE_OUTLINED,size=14,color=p['text']),
            ft.Text(('航线图' if key=='day' else '夜航') if compact else PALETTES[key]['name'],size=11,color=p['text'])])) for key in PALETTES])

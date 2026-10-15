"""Shared curved route artwork for thumbnail and full atlas."""
import math
import flet as ft
import flet.canvas as cv
import theme
import route_style

COLORS={'air':'#347E9B','rail':'#318A73'}

def control_point(a,b):
    dx,dy=b[0]-a[0],b[1]-a[1]
    length=math.hypot(dx,dy)
    if length<.001:return a
    nx,ny=-dy/length,dx/length
    if ny>0 or (abs(ny)<.001 and nx<0):nx,ny=-nx,-ny
    bend=min(length*.42,180)
    return ((a[0]+b[0])/2+nx*bend,(a[1]+b[1])/2+ny*bend)

def arc_shapes(a,b,mode,active=False,small=False):
    style=route_style.current();palette=route_style.PALETTES[style]
    color=palette[mode];c=control_point(a,b)
    width=(1.7 if small else 3.0 if active else 2.2)
    result=[]
    for stroke,shade in [(width+7 if not small else width+3,theme.with_alpha(color,.18 if style=='night' else .08)),
                         (width+2,theme.with_alpha(color,.28) if style=='night' else '#F9FCFD'),(width,color)]:
        result.append(cv.Path(elements=[cv.Path.MoveTo(*a),cv.Path.QuadraticTo(*c,*b)],
            paint=ft.Paint(color=shade,stroke_width=stroke,style=ft.PaintingStyle.STROKE,
                stroke_cap=ft.StrokeCap.ROUND,stroke_join=ft.StrokeJoin.ROUND,anti_alias=True)))
    if math.dist(a,b)>(32 if small else 55):
        t=.58
        p=((1-t)**2*a[0]+2*(1-t)*t*c[0]+t*t*b[0],(1-t)**2*a[1]+2*(1-t)*t*c[1]+t*t*b[1])
        dx,dy=(1-t)*(c[0]-a[0])+t*(b[0]-c[0]),(1-t)*(c[1]-a[1])+t*(b[1]-c[1])
        angle=math.atan2(dy,dx);size=3 if small else 6
        arms=[(p[0]-size*math.cos(angle+s*.55),p[1]-size*math.sin(angle+s*.55)) for s in (-1,1)]
        result.append(cv.Path(elements=[cv.Path.MoveTo(*arms[0]),cv.Path.LineTo(*p),cv.Path.LineTo(*arms[1])],
            paint=ft.Paint(color=color,stroke_width=width,style=ft.PaintingStyle.STROKE,stroke_cap=ft.StrokeCap.ROUND,anti_alias=True)))
    return result

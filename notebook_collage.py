"""Portable scrapbook pages: fixed 420 x 580 design coordinates, native + HTML."""
import base64
from copy import deepcopy
from html import escape
import math
from io import BytesIO
from functools import lru_cache
from hashlib import sha256
from pathlib import Path
import tempfile
from PIL import Image, ImageOps
import flet as ft

_preview_cache = None

@lru_cache(maxsize=96)
def preview_image(encoded):
    """Stable local image URLs keep redraws from retransmitting megabytes."""
    global _preview_cache
    if _preview_cache is None:
        _preview_cache=tempfile.TemporaryDirectory(prefix='kexinglu-paper-preview-')
    raw=base64.b64decode(encoded)
    path=Path(_preview_cache.name)/(sha256(raw).hexdigest()+('.png' if raw.startswith(b'\x89PNG') else '.jpg'))
    if not path.exists():path.write_bytes(raw)
    return str(path)

FONTS = {'Microsoft YaHei':'现代黑体','SimSun':'书页宋体','KaiTi':'手写楷体','Georgia':'英文衬线','Consolas':'打字机'}
TEXT_PRESETS = {
    '正文':dict(text='写下今天的小事',size=18),
    '章节编号':dict(text='01',font='Georgia',size=72,w=140,h=125,color='#8D9C8B'),
    '日期标签':dict(text='DATE / 写下日期',font='Consolas',size=15,w=280,h=55,background='#ECEADF'),
    '照片图注':dict(text='沿途拾光 · 留下一帧',size=13,w=300,h=45,color='#84887D'),
    '英文扉页':dict(text='Little moments.',font='Georgia',italic=True,size=29,w=340,h=75),
    '下划线手记':dict(text='留给未来的自己',font='KaiTi',underline=True,size=25,w=320,h=70),
    '胶片标记':dict(text='FRAME  /  001',font='Consolas',size=18,w=260,h=60,background='#34413B',color='#F5F1E5'),
    '书页标题':dict(text='日常，值得珍藏',font='SimSun',size=30,bold=True,w=350,h=75),
    '手写句子':dict(text='慢慢走，也慢慢记。',font='KaiTi',size=25,w=340,h=90),
    '荧光标注':dict(text='TODAY IS A GOOD DAY',size=20,highlight='#F5E7A0',bold=True,w=340,h=65),
    '投影文字':dict(text='旅途中的小确幸',size=27,shadow=True,bold=True,w=340,h=75),
    '邮戳标签':dict(text='MEMORIES / 2026',font='Consolas',size=20,background='#EADCC4',rotation=-5,w=290,h=60),
}

def snapshot_sticker(path):
    """Embed imported pixels as PNG, retaining alpha and EXIF orientation."""
    try:
        with Image.open(path) as source:
            img=ImageOps.exif_transpose(source).convert('RGBA')
            img.thumbnail((1400,1400))
            buf=BytesIO();img.save(buf,'PNG',optimize=True)
            return {'image':base64.b64encode(buf.getvalue()).decode('ascii'),
                    'mime':'image/png','aspect':img.width/max(1,img.height)}
    except (OSError, ValueError, Image.DecompressionBombError):return None

PAPERS = {
    'grid': ('奶油方格', '#FAF7EF', '#DDDCCF'),
    'blue': ('蓝调日记', '#EFF5FB', '#CDDDEA'),
    'rose': ('草莓便笺', '#FFF1F2', '#E9CDD2'),
    'kraft': ('旧日车站', '#E9D8B8', '#CDBA99'),
    'sage': ('植物标本', '#F0F3E8', '#D3DBC6'),
    'plain': ('纯白影集', '#FFFEFA', '#E9E6DE'),
}
LAYOUTS = {'daily':'日记拼贴', 'postcard':'旅行明信片', 'film':'胶片故事',
           'garden':'植物手札', 'memo':'便利贴周记', 'blank':'自由空白'}
STICKERS = ['✦', '✿', '♡', '☀', '☁', '✈', '☕', '♫', '★', '❀', '→', '✓']

def element(kind='text', **values):
    return {**dict(kind=kind,x=45,y=90,w=220,h=90,rotation=0,color='#34465B',
                   background='',text='写下此刻的心情',size=18), **values}


def make_design(item, layout='daily', paper='grid'):
    """Explicit conversion only. Existing source text/photos remain in the page."""
    parts=[]
    title=item.get('title') or '今日手记'
    date=' · '.join(filter(None,[item.get('date'),item.get('place')]))
    if layout!='blank':
        parts=[element(text=title,x=30,y=28,w=355,h=50,size=27),
               element(text=date or 'A DAY TO REMEMBER',x=32,y=81,w=350,h=28,size=11),
               element('tape',x=260,y=115,w=120,h=25,rotation=7,background='#9BBBCB',text='')]
        photos=[p for p in item.get('photos',[]) if p.get('included',True)]
        if photos:
            parts.append(element('photo',image=photos[0]['image'],x=35,y=130,w=235,h=205,rotation=-4,text=''))
        else:
            parts.append(element('text',text='把风景留在这里\n添加一张自己的照片',x=35,y=130,w=235,h=185,
                                 background='#E0E9EF',rotation=-4,size=19))
        parts.extend([element(text=item.get('note') or '今天遇见的风景，\n想留下的小事，\n都值得慢慢记录。',
                              x=58,y=351,w=305,h=155,background='#FFF9DA',rotation=2,size=16),
                      element('sticker',text='✿',x=290,y=224,w=78,h=86,size=63,color='#577E90',rotation=12),
                      element('sticker',text='♡',x=320,y=469,w=50,h=50,size=38,color='#B66D77')])
        if layout=='postcard':
            parts[2]['background']='#C9B194';parts[3].update(x=32,y=125,w=350,h=240,rotation=-2)
            parts[4].update(x=38,y=390,w=340,h=140,background='',rotation=0)
        elif layout=='film':
            parts[3].update(x=45,y=125,w=205,h=200,rotation=-7)
            if len(photos)>1:
                parts.append(element('photo',image=photos[1]['image'],x=176,y=285,w=200,h=200,rotation=6,text=''))
            parts[4].update(x=32,y=370,w=140,h=165,size=13,rotation=-2)
        elif layout=='garden':
            parts[4].update(background='#E5EBD4');parts[5].update(text='❀',color='#718766',size=76)
        elif layout=='memo':
            parts[3].update(x=35,y=130,w=175,h=180,rotation=-3)
            parts[4].update(x=220,y=150,w=165,h=230,size=14,rotation=4)
            parts.append(element(text='今日清单\n☐ 慢慢走\n☐ 看一场日落',x=42,y=380,w=205,h=150,background='#DAE7EF',rotation=-3,size=16))
    return dict(paper=paper,layout=layout,elements=parts)

def native_element(obj, scale):
    kind=obj['kind'];w=obj['w']*scale;h=obj['h']*scale
    if kind in ('photo','image'):
        content=ft.Image(src=preview_image(obj['image']),fit=ft.BoxFit.COVER if kind=='photo' else ft.BoxFit.CONTAIN,
                         width=max(1,w-(14*scale if kind=='photo' else 0)),height=max(1,h-(28*scale if kind=='photo' else 0)))
    else:
        content=ft.Text(obj.get('text',''),size=obj.get('size',18)*scale,color=obj.get('color','#34465B'),
                        font_family=obj.get('font','Microsoft YaHei'),overflow=ft.TextOverflow.CLIP,
                        weight=ft.FontWeight.BOLD if obj.get('bold') else ft.FontWeight.NORMAL,
                        italic=obj.get('italic',False),text_align={'center':ft.TextAlign.CENTER,'right':ft.TextAlign.RIGHT}.get(obj.get('align'),ft.TextAlign.LEFT),
                        style=ft.TextStyle(bgcolor=obj.get('highlight') or None,
                            decoration=ft.TextDecoration.UNDERLINE if obj.get('underline') else None,
                            shadow=ft.BoxShadow(blur_radius=2*scale,offset=ft.Offset(2*scale,2*scale),color='#60414B55') if obj.get('shadow') else None))
    return ft.Container(width=w,height=h,content=content,
        padding=(ft.Padding.only(left=7*scale,right=7*scale,top=7*scale,bottom=21*scale) if kind=='photo' else (0 if kind=='image' else 7*scale)),
        opacity=obj.get('opacity',1),
        bgcolor='#FFFEFA' if kind=='photo' else obj.get('background') or None,
        rotate=math.radians(obj.get('rotation',0)),border_radius=2*scale,
        shadow=ft.BoxShadow(blur_radius=6*scale,offset=ft.Offset(1,3*scale),color='#26000000')
            if kind=='photo' or obj.get('background') else None)

def native_element_node(obj,i,scale,interactive=None,selected=-1):
    content=native_element(obj,scale)
    if interactive:
        if selected==i:content.border=ft.Border.all(1.5,'#668EA6')
        content=ft.GestureDetector(content=content,
            on_tap=lambda e,n=i:interactive('select',n,e),
            on_pan_start=lambda e,n=i:interactive('start',n,e),
            on_pan_update=lambda e,n=i:interactive('move',n,e),
            on_pan_end=lambda e,n=i:interactive('end',n,e),drag_interval=32)
    return ft.Container(left=obj['x']*scale,top=obj['y']*scale,
        width=obj['w']*scale,height=obj['h']*scale,content=content,
        ignore_interactions=bool(interactive and obj.get('locked')),data={'collage_element':i})


def native_canvas(design,width,height=None,interactive=None,selected=-1):
    scale=width/420;h=580*scale
    _,bg,line=PAPERS.get(design.get('paper'),PAPERS['grid'])
    layers=[ft.Container(left=0,top=0,width=width,height=h,bgcolor=bg,
        on_click=(lambda e:interactive('clear',-1,e)) if interactive else None)]
    if design.get('paper')!='plain':
        for y in range(20,580,20):
            layers.append(ft.Container(left=0,top=y*scale,width=width,height=.5,bgcolor=line,ignore_interactions=True))
        for x in range(20,420,20):
            layers.append(ft.Container(left=x*scale,top=0,width=.5,height=h,bgcolor=line,ignore_interactions=True))
    for i,obj in enumerate(design['elements']):
        if obj.get('hidden'):continue
        layers.append(native_element_node(obj,i,scale,interactive,selected))
    return ft.Container(width=width,height=height or h,clip_behavior=ft.ClipBehavior.HARD_EDGE,
        bgcolor=bg,content=ft.Stack(width=width,height=h,controls=layers),data={'collage_canvas':True})

def html_canvas(design):
    esc=lambda v:escape(str(v),quote=True)
    _,bg,line=PAPERS.get(design.get('paper'),PAPERS['grid'])
    grid='' if design.get('paper')=='plain' else f'background-image:linear-gradient({line} 1px,transparent 1px),linear-gradient(90deg,{line} 1px,transparent 1px);background-size:4.762% 3.448%;'
    result=[f'<div class="collage-sheet" style="background-color:{bg};{grid}">']
    for obj in design['elements']:
        if obj.get('hidden'):continue
        # Numeric geometry is never interpolated from untrusted strings.
        style=f'left:{float(obj["x"])/4.2}%;top:{float(obj["y"])/5.8}%;width:{float(obj["w"])/4.2}%;height:{float(obj["h"])/5.8}%;transform:rotate({float(obj.get("rotation",0))}deg);font-size:{float(obj.get("size",18))/4.2}cqw;'
        style+='color:'+esc(obj.get('color','#34465B'))+';background:'+esc(obj.get('background') or 'transparent')+';'
        font=obj.get('font','Microsoft YaHei');font=font if font in FONTS else 'Microsoft YaHei'
        style+=f'font-family:{font};opacity:{float(obj.get("opacity",1))};text-align:{obj.get("align","left") if obj.get("align","left") in ("left","center","right") else "left"};'
        if obj.get('bold'):style+='font-weight:700;'
        if obj.get('italic'):style+='font-style:italic;'
        if obj.get('underline'):style+='text-decoration:underline;'
        if obj.get('shadow'):style+='text-shadow:2px 2px 2px #414B5560;'
        mime='image/png' if obj.get('mime')=='image/png' else 'image/jpeg'
        content=('<img src="data:'+mime+';base64,'+esc(obj['image'])+'">') if obj['kind'] in ('photo','image') else esc(obj.get('text',''))
        if obj.get('highlight') and obj['kind'] not in ('photo','image'):
            content='<span style="background:'+esc(obj['highlight'])+'">'+content+'</span>'
        result.append(f'<div class="scrap scrap-{esc(obj["kind"])}" style="{style}">{content}</div>')
    return ''.join(result)+'</div>'

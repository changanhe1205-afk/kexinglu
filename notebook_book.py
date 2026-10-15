"""Native perspective page turner with an actual spine pivot and two-page spread."""
import asyncio
import base64
import math
import flet as ft
from collection_motion import motion_enabled
from travel_journal import STYLES, BINDINGS


def cover_thumbnail(style, title, width=64, height=86):
    spec=BINDINGS.get(style,BINDINGS['paper'])
    return ft.Container(width=width,height=height,padding=9,bgcolor=spec['cover'],
        border_radius=ft.BorderRadius.only(top_right=5,bottom_right=5),
        border=ft.Border.only(left=ft.BorderSide(6,'#33000000'),bottom=ft.BorderSide(3,'#D9CEB8')),
        shadow=ft.BoxShadow(blur_radius=8,offset=ft.Offset(3,4),color='#30000000'),
        content=ft.Text(title,size=11,color=spec['gold'],max_lines=3,font_family='SimSun'))


class NotebookBook(ft.Container):
    def __init__(self, book, width, height, on_turn):
        self.book=book;self.book_width=width;self.book_height=height
        self.index=-1;self.busy=False;self.on_turn=on_turn;self.drag_x=0
        self.stage=ft.Stack(width=width,height=height,clip_behavior=ft.ClipBehavior.NONE,
            animate_offset=ft.Animation(360,ft.AnimationCurve.EASE_IN_OUT))
        super().__init__(alignment=ft.Alignment.CENTER,padding=ft.Padding.all(16),
            content=ft.GestureDetector(content=self.stage,
                on_horizontal_drag_start=self.drag_start,
                on_horizontal_drag_update=self.drag_update,on_horizontal_drag_end=self.drag_end),
            data={'notebook_3d':True})
        self.render(-1)

    def drag_start(self,e):self.drag_x=0
    def drag_update(self,e):
        self.drag_x+=e.primary_delta if getattr(e,'primary_delta',None) is not None else (e.local_delta.x if e.local_delta else 0)
    async def drag_end(self,e):
        if abs(self.drag_x)>45:await self.on_turn(1 if self.drag_x<0 else -1)

    def sync(self):
        try:self.update();return True
        except RuntimeError:return False

    def resize_book(self,width,height):
        self.book_width=width;self.book_height=height
        self.stage.width=width;self.stage.height=height
        self.render(self.index)

    def page_face(self,index,side):
        key=self.book['style'];_,paper,ink,accent=STYLES[key];spec=BINDINGS[key]
        w=self.book_width/2;h=self.book_height
        if index is None:
            return ft.Container(width=w,height=h)
        cover=index==-1
        if cover:
            contents=[ft.Text('客行录  /  VOYAGE',size=9,color=spec['gold']),ft.Container(height=20),
                ft.Text(self.book['title'] or '我的旅行手账',font_family='SimSun',size=27,
                    color=spec['gold'],weight=ft.FontWeight.W_600),
                ft.Text(self.book.get('subtitle',''),size=12,color=spec['gold']),
                ft.Container(height=15),ft.Divider(color=spec['gold']),
                ft.Text(f"{len(self.book['pages']):02d} 篇手记  ·  私人珍藏",size=10,color=spec['gold']),
                ft.Text(spec['detail'],size=9,color=spec['gold'])]
        elif index>=len(self.book['pages']):
            contents=[ft.Container(height=60),ft.Text('旅途未完，\n故事待续。',font_family='SimSun',size=23,color=ink),
                      ft.Text('下一次出发，再写一页。',size=11,color=accent)]
        else:
            item=self.book['pages'][index]
            contents=[ft.Text(f'旅途手记 / {index+1:02d}',size=9,color=accent),
                ft.Text(item['title'] or '未命名页',size=20,font_family='SimSun',color=ink),
                ft.Text(' · '.join(filter(None,[item['place'],item['date']])),size=10,color=accent),
                ft.Text(item['note'] or '写下这一程，值得记住的小事。',size=12,color=ink)]
            for n,photo in enumerate(item['photos']):
                if not photo.get('included',True):continue
                image=ft.Image(src=base64.b64decode(photo['image']),fit=ft.BoxFit.CONTAIN)
                if spec['binding']=='album' or key in ('kraft','rose'):
                    image=ft.Container(content=image,padding=ft.Padding.only(left=7,right=7,top=7,bottom=20),
                        bgcolor='#FFFEFA',rotate=(-.022 if n%2==0 else .018),
                        shadow=ft.BoxShadow(blur_radius=6,offset=ft.Offset(1,3),color='#30000000'))
                contents.append(image)
                if photo.get('caption'):contents.append(ft.Text(photo['caption'],size=10,color=accent))
            contents.extend([ft.Divider(color=accent),ft.Text(f'客行录 · {index+1:02d}',size=9,color=accent)])
        material=ft.Container(width=w,height=h,bgcolor=spec['cover'] if cover else paper,
            border_radius=ft.BorderRadius.only(top_left=5 if side=='left' else 1,top_right=5 if side=='right' else 1,
                                               bottom_left=5 if side=='left' else 1,bottom_right=5 if side=='right' else 1))
        layers=[material]
        if cover:
            layers.append(ft.Container(left=0,right=0,top=0,bottom=0,ignore_interactions=True,
                gradient=ft.LinearGradient(begin=ft.Alignment.TOP_LEFT,end=ft.Alignment.BOTTOM_RIGHT,
                    colors=['#20FFFFFF','#00FFFFFF','#28000000'])))
        # Real layers, woven cover strokes and paper ruling stay behind the text.
        if cover and spec['texture'] in ('cloth','grain'):
            layers.extend(ft.Container(left=0,right=0,top=y,height=1,bgcolor='#0DFFFFFF',ignore_interactions=True)
                          for y in range(4,int(h),5 if spec['texture']=='cloth' else 9))
            if spec['texture']=='cloth':
                layers.extend(ft.Container(top=0,bottom=0,left=x,width=1,bgcolor='#08000000',ignore_interactions=True)
                              for x in range(4,int(w),7))
        if not cover and key in ('kraft','ocean','linen'):
            layers.extend(ft.Container(left=18,right=18,top=y,height=1,bgcolor='#126E685B',ignore_interactions=True)
                          for y in range(38,int(h)-15,24))
        if cover:
            layers.append(ft.Container(left=16,right=16,top=16,bottom=16,
                border=ft.Border.all(1,'#448F8066'),
                border_radius=14 if key=='rose' else 2,ignore_interactions=True))
        if not cover and index<len(self.book['pages']) and self.book['pages'][index].get('design'):
            from notebook_collage import native_canvas
            design=self.book['pages'][index]['design']
            # Fixed-ratio paper: the complete composition is visible without reflow.
            cw=min(w,h*420/580)
            layers.append(ft.Container(left=(w-cw)/2,top=(h-cw*580/420)/2,content=native_canvas(design,cw)))
        else:
            layers.append(ft.Container(left=24,right=24,top=32 if cover else 22,bottom=22,
                content=ft.ListView(controls=contents,spacing=16 if cover else 12)))
        layers.append(ft.Container(left=0 if side=='right' else None,right=0 if side=='left' else None,
            top=0,bottom=0,width=26,ignore_interactions=True,
            gradient=ft.LinearGradient(begin=ft.Alignment.CENTER_LEFT,end=ft.Alignment.CENTER_RIGHT,
                colors=['#43000000','#08000000','#00FFFFFF'] if side=='right' else ['#00FFFFFF','#09000000','#35000000'])))
        return ft.Stack(width=w,height=h,controls=layers)

    def indices(self,index):
        return (None,-1) if index<0 else ((index//2)*2,(index//2)*2+1)

    def render(self,index):
        self.index=index
        if any(p.get('design') for p in self.book['pages']):
            self.book_width=min(self.book_width,self.book_height*840/580)
            self.stage.width=self.book_width
        self.stage.offset=ft.Offset(-.25 if index<0 else 0,0)
        w=self.book_width;h=self.book_height
        left,right=self.indices(index)
        base=[]
        # Exposed paper edges and hardcover underneath the leaves.
        for offset in (8,6,4,2):
            base.append(ft.Container(left=w/2 if index<0 else 0,top=offset,right=-offset,bottom=-offset,
                bgcolor='#D9CDB8' if offset%4 else '#F8F2E6',border_radius=5,
                border=ft.Border.all(.6,'#BEB39F'),
                shadow=ft.BoxShadow(blur_radius=28,offset=ft.Offset(4,12),color='#22000000') if offset==8 else None))
        if index>=0:
            for depth in (3,2,1):
                for side,leaf in (('left',left-depth*2),('right',right+depth*2)):
                    if 0<=leaf<len(self.book['pages']):
                        base.append(ft.Container(left=(-depth*15 if side=='left' else w/2+depth*15),top=depth*7,
                            width=w/2,height=h-depth*8,rotate=(-depth*.035 if side=='left' else depth*.035),
                            content=self.page_face(leaf,side),ignore_interactions=True))
        self.left_leaf=ft.Container(left=0,top=0,width=w/2,height=h,content=self.page_face(left,'left'))
        self.right_leaf=ft.Container(left=w/2,top=0,width=w/2,height=h,content=self.page_face(right,'right'))
        self.stage.controls=base+[self.left_leaf,self.right_leaf]
        if index>=0:
            binding=BINDINGS[self.book['style']]['binding']
            if binding in ('rings','sewn'):
                for y in range(36,int(h)-20,54 if binding=='rings' else 35):
                    self.stage.controls.append(ft.Container(left=w/2-9,top=y,width=18,height=7 if binding=='rings' else 2,
                        border_radius=5,bgcolor='#ADAFB1' if binding=='rings' else '#A9987B',
                        border=ft.Border.all(1,'#E4E0D7'),ignore_interactions=True))
            self.stage.controls.append(ft.Container(left=w/2+13,top=-5,width=9,height=37,
                bgcolor=BINDINGS[self.book['style']]['cover'],border_radius=2,ignore_interactions=True))

    async def turn_to(self,index):
        if self.busy:return False
        old=self.index
        if self.indices(old)==self.indices(index) or not motion_enabled():
            self.render(index);self.sync();return True
        self.busy=True
        try:
            forward=index>old;half=self.book_width/2
            self.stage.offset=ft.Offset(0,0)
            old_left,old_right=self.indices(old);new_left,new_right=self.indices(index)
            self.right_leaf.content=self.page_face(new_right,'right') if forward else self.page_face(old_right,'right')
            self.left_leaf.content=self.page_face(old_left,'left') if forward else self.page_face(new_left,'left')
            overlay=ft.Container(left=half if forward else 0,top=0,width=half,height=self.book_height,
                content=self.page_face(old_right if forward else old_left,'right' if forward else 'left'),
                ignore_interactions=True)
            self.stage.controls.append(overlay)
            for frame in range(25):
                progress=frame/24
                angle=math.pi*(.5-.5*math.cos(math.pi*progress))
                if angle<=math.pi/2:
                    actual=-angle if forward else angle
                    pivot=ft.Alignment.CENTER_LEFT if forward else ft.Alignment.CENTER_RIGHT
                else:
                    if frame==13:
                        overlay.left=0 if forward else half
                        overlay.content=self.page_face(new_left if forward else new_right,'left' if forward else 'right')
                    actual=math.pi-angle if forward else angle-math.pi
                    pivot=ft.Alignment.CENTER_RIGHT if forward else ft.Alignment.CENTER_LEFT
                overlay.transform=ft.Transform(matrix=ft.Matrix4.identity().set_entry(3,2,.0014).rotate_y(actual),alignment=pivot)
                overlay.shadow=ft.BoxShadow(blur_radius=10+24*math.sin(angle),offset=ft.Offset(6 if forward else -6,4),color='#45000000')
                if not self.sync():return False
                await asyncio.sleep(.022)
            return True
        finally:
            self.render(index);self.busy=False;self.sync()

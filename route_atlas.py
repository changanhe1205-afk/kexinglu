"""Flight and high-speed rail atlas, opened from the travel log."""
from i18n import tr
import asyncio
import math
import sqlite3
import flet as ft
import flet.canvas as cv
import map_data
import theme
import tile_map
import travel_routes as db
import route_graphics as art
import route_style


class RouteAtlas:
    def __init__(self, page, mode='air', automatic=False, on_close=None, embedded=False):
        self.page, self.mode = page, mode
        self.embedded = embedded
        self.embedded_size = None
        self.automatic=automatic
        self.on_close=on_close
        self.style_key=route_style.current()
        self.selected = None
        self.preview = None
        self.alive = True
        self.pending = False
        self.pool = {}
        self.pick_target = None
        self.old_resize = page.on_resize
        self.old_keyboard = page.on_keyboard_event
        self.map = ft.Stack(clip_behavior=ft.ClipBehavior.HARD_EDGE)
        self.gesture = ft.GestureDetector(content=self.map, on_scroll=self.scroll,
            on_scale_start=self.scale_start, on_scale_update=self.scale_update,
            on_tap_up=self.pick_point, drag_interval=32)
        self.title = ft.TextField(label='线路名称（选填）', text_size=13)
        self.start = ft.TextField(label='起点', hint_text='输入城市，或 名称 | 经度,纬度', text_size=13)
        self.end = ft.TextField(label='终点', hint_text='输入城市，或 名称 | 经度,纬度', text_size=13)
        self.via = ft.TextField(label='途经地点（选填，每行一个）', multiline=True, min_lines=2, max_lines=4, text_size=12)
        self.suggestions = ft.Column(spacing=0)
        self.start.on_change = lambda e:self.suggest(self.start)
        self.end.on_change = lambda e:self.suggest(self.end)
        self.status = ft.Text('从中国出发，把每一次抵达留在地图上。', size=12, color=theme.TEXT_SUB)
        self.heading = ft.Text(size=24, weight=ft.FontWeight.W_600, color=theme.TEXT_MAIN)
        self.count = ft.Text(size=12, color=theme.TEXT_SUB)
        self.saved = ft.Column(spacing=6)
        self.save_button = ft.FilledButton('保存新线路', icon=ft.Icons.ADD, on_click=self.save)
        self.remove_button = ft.TextButton('删除这条线路', on_click=self.remove, visible=False)
        self.sidebar = ft.Container(width=302, padding=18, bgcolor=theme.CARD_BG,
            border_radius=18, content=ft.ListView(spacing=12, controls=[
                ft.Text('记录一段旅程', size=18, color=theme.TEXT_MAIN), self.title,
                self.start, self.end, self.suggestions, self.via,
                ft.Row(spacing=0, controls=[
                    ft.TextButton('地图选起点', on_click=lambda e:self.begin_pick(self.start)),
                    ft.TextButton('地图选终点', on_click=lambda e:self.begin_pick(self.end))]),
                ft.Text('国内城市可直接输入并选择候选；机场、车站或海外地点可填“名称 | 经度, 纬度”。城市候选为近似中心点。', size=11, color=theme.TEXT_SUB),
                ft.Row(controls=[ft.TextButton('预览轨迹', on_click=self.show_preview), ft.TextButton('新建线路', on_click=self.new)]),
                self.save_button, self.remove_button, self.status,
                ft.Divider(color=theme.LINE), self.count, self.saved]))
        self.map_frame=ft.Container(content=self.gesture,expand=True,border_radius=18,
            clip_behavior=ft.ClipBehavior.HARD_EDGE,bgcolor=route_style.PALETTES[self.style_key]['sea'])
        self.view = ft.View(route='/travel-routes', bgcolor=theme.PAGE_BG if hasattr(theme,'PAGE_BG') else theme.CARD_BG_SOFT,
            padding=22, controls=[ft.Row(controls=[
                ft.TextButton('返回旅行日志', icon=ft.Icons.ARROW_BACK, on_click=self.close),
                self.heading, ft.Container(expand=True),
                ft.TextButton('飞机轨迹', icon=ft.Icons.FLIGHT, on_click=lambda e:self.switch('air')),
                ft.TextButton('高铁轨迹', icon=ft.Icons.TRAIN, on_click=lambda e:self.switch('rail'))]),
                ft.Row(expand=True, spacing=16, controls=[self.sidebar,
                    ft.Column(expand=True, controls=[ft.Row(controls=[
                        ft.TextButton('回到中国', on_click=lambda e:self.home()),
                        ft.TextButton('世界视野', on_click=lambda e:self.world()),
                        ft.TextButton('查看全部线路', on_click=lambda e:self.fit()),
                        ft.Container(expand=True),
                        ft.IconButton(ft.Icons.REMOVE, tooltip='缩小轨迹地图', on_click=lambda e:self.zoom(-1)),
                        ft.IconButton(ft.Icons.ADD, tooltip='放大轨迹地图', on_click=lambda e:self.zoom(1))]),
                        self.map_frame,
                        ft.Text('拖动 / 双指移动 · 双指捏合缩放 · 简化地图 · Natural Earth\n'+('轨迹自动来自已保存票根。' if automatic else '轨迹为所填地点的示意连线。')+'不代表实际航道或铁路走向。底图与轨迹可离线查看。', size=11, color=theme.TEXT_SUB)])])])
        self.view.data={'route_atlas':self}
        if automatic:
            self.view.route='/ticket-routes'
            self.view.controls[0].controls[0].content='返回旅程票根'
            self.sidebar.content=ft.ListView(spacing=12,controls=[
                ft.Text('票根串起的旅程',size=18,color=theme.TEXT_MAIN),
                ft.Text('保存票根后自动生成；修改或删除票根，轨迹随之更新。无需另外创建线路。',size=12,color=theme.TEXT_SUB),
                self.count,self.status,ft.Divider(color=theme.LINE),self.saved])
        self.v = tile_map.fit_view(*self.dimensions(), (73.5,18.2,135.1,53.6))
        self.style_box=ft.Container(content=route_style.selector(self.change_style))
        self.sidebar.content.controls.insert(0,self.style_box)
        self.reload()
        self.apply_palette()

    def change_style(self,key):
        route_style.set_style(key);self.style_key=key
        self.style_box.content=route_style.selector(self.change_style)
        self.apply_palette();self.draw();self.page.update()

    def apply_palette(self):
        from dataclasses import fields
        from flet.controls.base_control import BaseControl
        p=route_style.PALETTES[self.style_key]
        self.view.bgcolor=p['sea'];self.sidebar.bgcolor=p['panel'];self.map_frame.bgcolor=p['sea']
        seen=set()
        def visit(c):
            if isinstance(c,BaseControl):
                if id(c) in seen:return
                seen.add(id(c))
                if isinstance(c,ft.Text):c.color=p['muted'] if (c.size or 14)<=12 else p['text']
                elif isinstance(c,ft.TextButton):c.style=ft.ButtonStyle(color=p['text'])
                elif isinstance(c,ft.IconButton):c.icon_color=p['text']
                elif isinstance(c,ft.Divider):c.color=p['line']
                for f in fields(c):
                    if f.name!='data':visit(getattr(c,f.name))
            elif isinstance(c,(list,tuple)):
                for item in c:visit(item)
        visit(self.view)

    def dimensions(self):
        if self.embedded:
            return self.embedded_size or (max(300,(self.page.width or 1320)-360),max(250,(self.page.height or 900)-345))
        return max(300,(self.page.width or 1280)-380), max(250,(self.page.height or 850)-190)

    def open(self):
        self.page.views.append(self.view)
        self.page.on_resize=self.resize
        self.page.on_keyboard_event=self.keyboard
        self.draw();self.page.update()
        return self

    def keyboard(self,e):
        if e.key=='Escape':self.close()

    def close(self,e=None):
        if not self.alive:return
        self.alive=False
        self.page.on_resize=self.old_resize;self.page.on_keyboard_event=self.old_keyboard
        if self.view in self.page.views:self.page.views.remove(self.view)
        self.page.update()
        if self.old_resize:self.old_resize(e)
        if self.on_close:self.on_close()

    def switch(self,mode):
        if self.mode==mode:return
        self.mode=mode
        if self.automatic:
            self.selected=None;self.preview=None
        else:self.new()
        self.reload();self.apply_palette()
        if self.automatic and self.routes:self.fit(update=False)
        self.draw();self.page.update()

    def reload(self,tickets=None):
        if self.automatic:
            import ticket_db
            from ticket_routes import from_tickets
            self.routes,missing=from_tickets(ticket_db.list_tickets() if tickets is None else tickets,self.mode)
            self.heading.value='飞机轨迹' if self.mode=='air' else '高铁轨迹'
            self.count.value=f'已自动生成 {len(self.routes)} 条 · 待定位 {len(missing)} 张'
            self.status.value='机场按内置坐标定位；铁路优先使用站点坐标，缺少时按城市近似显示。线路为示意，不代表实际航路或铁路。'
            self.saved.controls=[ft.TextButton(r['title']+'\n'+r['date']+' '+r['code'],icon=self.icon(),on_click=lambda e,r=r:self.load(r)) for r in self.routes]
            if missing:
                self.saved.controls.append(ft.Text('以下票根地点暂未识别，未绘制轨迹：',size=12,color=theme.TEXT_SUB))
                self.saved.controls.extend(ft.Text(f"{t.get('from_city','')} → {t.get('to_city','')}",size=12,color=theme.TEXT_SUB) for t in missing)
            if not self.routes and not missing:self.saved.controls=[ft.Text('保存一张'+('飞机' if self.mode=='air' else '高铁')+'票根后，这里就会自动出现轨迹。',size=13,color=theme.TEXT_SUB)]
            return
        self.routes=db.list_routes(self.mode)
        self.heading.value='飞机轨迹' if self.mode=='air' else '高铁轨迹'
        self.count.value=f'我的线路 · {len(self.routes)} 条'
        self.saved.controls=[ft.TextButton(r['title'], icon=self.icon(), on_click=lambda e,r=r:self.load(r)) for r in self.routes]
        if not self.routes:self.saved.controls=[ft.Text('还没有线路，填写起终点开始记录。',size=12,color=theme.TEXT_SUB)]

    def icon(self):return ft.Icons.FLIGHT if self.mode=='air' else ft.Icons.TRAIN

    def suggest(self,field):
        query=(field.value or '').strip()
        names=[n for n in map_data.places() if query and query in n][:5]
        def choose(name):
            field.value=name;self.suggestions.controls=[];self.page.update()
        self.suggestions.controls=[ft.TextButton(n+' · 城市/地点',on_click=lambda e,n=n:choose(n)) for n in names]
        self.page.update()

    def points(self):
        lines=[self.start.value or '']+[s for s in (self.via.value or '').splitlines() if s.strip()]+[self.end.value or '']
        return db.validate_points([db.parse_line(s) for s in lines])

    def show_preview(self,e=None):
        try:
            self.preview=self.points();self.fit(self.preview)
            self.status.value='轨迹预览 · 点击保存后才会收录。'
        except ValueError as err:self.status.value=str(err)
        self.page.update()

    def save(self,e=None):
        try:
            self.selected=db.save_route(self.mode,self.title.value or '',self.points(),self.selected)
            self.preview=None;self.reload();self.edit_state();self.fit()
            self.status.value='线路已保存到本机。'
        except (ValueError,OSError,sqlite3.Error) as err:self.status.value='保存失败：'+str(err)
        self.page.update()

    def edit_state(self):
        self.save_button.content='保存修改' if self.selected else '保存新线路'
        self.save_button.icon=ft.Icons.SAVE_OUTLINED if self.selected else ft.Icons.ADD
        self.remove_button.visible=self.selected is not None

    def begin_pick(self,field):
        self.pick_target=field
        self.status.value='请点击地图选取'+field.label+'，之后可修改坐标前的地点名称。'
        self.page.update()

    def pick_point(self,e):
        if self.pick_target is None:return
        lon,lat=self.v.lonlat_at(e.local_position.x,e.local_position.y)
        lon=(lon+180)%360-180
        field=self.pick_target
        name=(field.value or field.label).split('|')[0].strip()
        field.value=f'{name} | {lon:.6f}, {max(-85,min(85,lat)):.6f}'
        self.pick_target=None
        self.status.value='地点已选取，填好另一端后即可预览轨迹。'
        self.page.update()

    def new(self,e=None):
        self.selected=None;self.preview=None
        self.pick_target=None
        for f in (self.title,self.start,self.end,self.via):f.value=''
        self.suggestions.controls=[];self.edit_state()
        self.status.value='正在新建线路，已保存的线路不会被覆盖。'
        self.draw();self.page.update()

    def load(self,route):
        if self.automatic:
            self.selected=route['id'];self.fit(route['points']);return
        self.selected=route['id'];self.preview=None;self.title.value=route['title']
        lines=[f"{p['name']} | {p['lon']}, {p['lat']}" for p in route['points']]
        self.start.value=lines[0];self.end.value=lines[-1];self.via.value='\n'.join(lines[1:-1])
        self.edit_state();self.fit(route['points']);self.page.update()

    def remove(self,e=None):
        from notebook_navigation import after_dialog_closed
        route_id=self.selected
        def confirm():
            db.delete_route(self.mode,route_id);self.reload();self.new()
        self.page.show_dialog(ft.AlertDialog(modal=True,title=ft.Text('删除这条轨迹？'),
            content=ft.Text('只删除线路，不影响旅行日志和票根。'),actions=[
                ft.TextButton(tr('取消'),on_click=lambda e:self.page.pop_dialog()),
                ft.FilledButton(tr('删除'),on_click=lambda e:after_dialog_closed(self.page,confirm))]))

    def resize(self,e=None):
        self.v=tile_map.View(*self.dimensions(),self.v.lon,self.v.lat,self.v.zoom)
        self.draw();self.page.update()

    def home(self):
        self.v=tile_map.fit_view(*self.dimensions(),(73.5,18.2,135.1,53.6));self.draw();self.page.update()

    def world(self):
        self.v=tile_map.fit_view(*self.dimensions(),(-180,-65,180,80));self.draw();self.page.update()

    def fit(self,points=None,update=True):
        points=points or [p for r in self.routes for p in r['points']]
        if not points:self.home();return
        xs=[p['lon'] for p in points];ys=[p['lat'] for p in points]
        # Routes crossing the date line are drawn at both world edges. Keep those
        # edges visible instead of fitting a box that clips the actual curve.
        bounds=(-180,-65,180,80) if max(xs)-min(xs)>180 else (min(xs)-1,min(ys)-1,max(xs)+1,max(ys)+1)
        self.v=tile_map.fit_view(*self.dimensions(),bounds,pad=.72)
        if update:self.draw();self.page.update()

    def zoom(self,step):
        self.v=self.v.zoomed(self.v.zoom+step);self.draw();self.page.update()

    def scroll(self,e):
        self.v=self.v.shifted(-e.scroll_delta.x,-e.scroll_delta.y);self.schedule()

    def scale_start(self,e):self.base=self.v;self.anchor=e.local_focal_point

    def scale_update(self,e):
        self.v=self.base.zoomed(self.base.zoom+math.log2(max(.01,e.scale)),(self.anchor.x,self.anchor.y)).shifted(e.local_focal_point.x-self.anchor.x,e.local_focal_point.y-self.anchor.y)
        self.schedule()

    def schedule(self):
        ft.context.disable_auto_update()
        if self.pending:return
        self.pending=True
        async def flush():
            try:
                await asyncio.sleep(.032)
                if self.alive:self.draw();self.map.update()
            finally:self.pending=False
        self.page.run_task(flush)

    def draw(self):
        self.map.width=self.v.width;self.map.height=self.v.height
        palette=route_style.PALETTES[self.style_key]
        bg_key=(self.v.width,self.v.height,self.v.lon,self.v.lat,self.v.zoom,self.style_key)
        if getattr(self,'background_key',None)!=bg_key:
            self.background_layer=route_style.background(self.v,self.style_key)
            self.background_key=bg_key
        controls=[self.background_layer]
        color=palette[self.mode]
        shapes=[];markers=[];label_boxes=[]
        records=[(r['points'],r['id']==self.selected) for r in getattr(self,'routes',[])]
        if self.preview:records.append((self.preview,True))
        # Repeated trips share one visible curve, with the selected trip on top.
        unique={}
        for points,active in records:
            key=tuple((p['lon'],p['lat']) for p in points)
            if key not in unique or active:unique[key]=(points,active)
        records=sorted(unique.values(),key=lambda r:not r[1])
        seen_markers=set()
        for points,active in records:
            xy=[self.v(p['lon'],p['lat']) for p in points]
            # Wrap each segment at the antimeridian instead of crossing the whole map.
            world=256*2**self.v.zoom
            for (x,y),(xx,yy) in zip(xy,xy[1:]):
                if xx-x>world/2:xx-=world
                elif xx-x < -world/2:xx+=world
                for offset in (-world,0,world):
                    shapes.extend(art.arc_shapes((x+offset,y),(xx+offset,yy),self.mode,active))
            for i,(p,(x,y)) in enumerate(zip(points,xy)):
                endpoint=i in (0,len(points)-1)
                if -40<x<self.v.width+40 and -40<y<self.v.height+40:
                    marker_key=(p['lon'],p['lat'])
                    if marker_key in seen_markers:continue
                    seen_markers.add(marker_key)
                    caption=('起点' if i==0 else '终点' if i==len(points)-1 else '途经')+' · '+p['name']
                    markers.append(ft.Container(left=x-17,top=y-17,width=34,height=34,border_radius=17,
                        bgcolor=palette['marker'],border=ft.Border.all(2,theme.with_alpha(color,.55)),tooltip=caption,
                        shadow=ft.BoxShadow(blur_radius=12,spread_radius=2,color=theme.with_alpha(color,.18)),
                        data={'route_endpoint':caption,'mode':self.mode},
                        content=ft.Icon(self.icon() if endpoint else ft.Icons.CIRCLE,size=18 if endpoint else 8,color=color)))
                    if active or (self.automatic and self.selected is None and len(records)<=6):
                        label=caption.replace('国际机场','').replace('机场','').replace('起点 · ','起 · ').replace('终点 · ','终 · ')
                        width=min(220,max(90,len(label)*11+20));height=30
                        for lx,ly in [(x-width/2,y+22),(x+25,y-15),(x-width-25,y-15),(x-width/2,y-54)]:
                            lx=max(4,min(self.v.width-width-4,lx));ly=max(4,min(self.v.height-height-4,ly))
                            box=(lx,ly,lx+width,ly+height)
                            if any(box[0]<b[2]+4 and box[2]>b[0]-4 and box[1]<b[3]+4 and box[3]>b[1]-4 for b in label_boxes):continue
                            label_boxes.append(box)
                            markers.append(ft.Container(left=lx,top=ly,width=width,height=height,
                                alignment=ft.Alignment.CENTER,tooltip=caption,
                                bgcolor=palette['panel'],border_radius=12,
                                content=ft.Text(label,size=11,color=color,max_lines=1,overflow=ft.TextOverflow.ELLIPSIS)))
                            break
        controls.append(cv.Canvas(shapes=shapes,width=self.v.width,height=self.v.height))
        controls.extend(markers);self.map.controls=controls


def open_atlas(page,mode='air'):
    return RouteAtlas(page,mode).open()


def open_ticket_atlas(page,mode='air',on_close=None):
    return RouteAtlas(page,mode,automatic=True,on_close=on_close).open()


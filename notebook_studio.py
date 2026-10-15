"""A full-window, multi-page scrapbook studio with independent document state."""
import asyncio
from copy import deepcopy
from pathlib import Path
import re
import time
import uuid
import flet as ft
import theme
from notebook_materials import catalog
import travel_journal as journal
from notebook_book import NotebookBook
from notebook_navigation import after_dialog_closed
from notebook_collage import (PAPERS, LAYOUTS, STICKERS, FONTS, TEXT_PRESETS,
                              element, make_design, native_canvas, snapshot_sticker, preview_image)


class NotebookStudio:
    def __init__(self,page,book,on_close,index=0):
        self.page=page;self.book=deepcopy(book);self.book['editor']='studio';self.on_close=on_close
        self.surface=theme.CARD_BG if theme.DARK else '#FAF9F5'
        self.soft=theme.CARD_BG_SOFT if theme.DARK else '#EFEEE7'
        self.ink=theme.TEXT_MAIN if theme.DARK else '#343C35'
        self.muted=theme.TEXT_SUB if theme.DARK else '#84887D'
        self.accent=theme.ACCENT if theme.DARK else '#64765E'
        self.index=max(0,min(index,len(book['pages'])-1));self.selected=-1
        self.saved=journal.get_book(book['id']) if book.get('id') else None
        self.undo_stack=[];self.redo_stack=[];self.zoom=1;self.width=320;self.importing=False
        self.group=None;self.group_time=0;self.alive=True
        self.material_page=0;self.material_signature=None
        self.old_resize=page.on_resize;self.old_keyboard=page.on_keyboard_event
        self.old_full=page.window.full_screen;self.old_close=page.window.prevent_close
        self.old_window_event=page.window.on_event
        self.picker=ft.FilePicker();page.services.append(self.picker)
        self.canvas=ft.Container();self.properties=ft.ListView(expand=True,spacing=12)
        self.layers=ft.ListView(height=120,spacing=0)
        self.materials=ft.ListView(expand=True,spacing=14)
        self.page_strip=ft.Row(spacing=6,scroll=ft.ScrollMode.AUTO,expand=True)
        self.status=ft.Text('已载入本机手账' if self.saved else '还未保存 · 你的创作只保存在这份草稿中',size=11,color=self.muted)
        self.selection=ft.Text('选择元素',size=15,weight=ft.FontWeight.W_600,color=self.ink)
        self.name=ft.TextField(value=self.book['title'],label='手账名称',dense=True,text_size=13,width=210,
                              on_change=self.rename)
        self.category=ft.Dropdown(value='sticker',label='素材分类',dense=True,
            options=[ft.dropdown.Option(k,v) for k,v in [('text','文字与效果'),('sticker','贴纸与胶带'),('import','我的素材'),('paper','纸张与版式')]],
            on_select=lambda e:self.paint_materials())
        self.tabs=ft.Row(wrap=True,spacing=2,run_spacing=2)
        self.search=ft.TextField(hint_text='搜索素材',dense=True,text_size=12,prefix_icon=ft.Icons.SEARCH,border_radius=10,
            border_color=theme.LINE,on_change=self.search_materials)
        self.full_button=ft.TextButton('全屏创作',icon=ft.Icons.FULLSCREEN,on_click=self.fullscreen)
        self.undo_button=ft.IconButton(ft.Icons.UNDO,tooltip='撤销',on_click=lambda e:self.undo())
        self.redo_button=ft.IconButton(ft.Icons.REDO,tooltip='重做',on_click=lambda e:self.undo(True))
        self.zoom_label=ft.Text('',size=11,color=self.muted)
        toolbar=ft.Container(padding=ft.Padding.symmetric(horizontal=16,vertical=10),bgcolor=self.surface,
            content=ft.Row(wrap=True,controls=[ft.TextButton('返回书架',icon=ft.Icons.ARROW_BACK,on_click=lambda e:self.request_close()),
                self.name,self.undo_button,self.redo_button,self.full_button,
                ft.TextButton('翻页预览',icon=ft.Icons.AUTO_STORIES_OUTLINED,on_click=self.preview),
                ft.TextButton('导出电子版',on_click=self.export),ft.FilledButton('保存手账',icon=ft.Icons.SAVE_OUTLINED,on_click=lambda e:self.save())]))
        self.left=ft.Container(width=230,padding=16,bgcolor=self.surface,content=ft.Column(controls=[
            ft.Text('纸间素材',size=17,weight=ft.FontWeight.W_600,color=self.ink),ft.Text('拖入纸页，即刻开始',size=11,color=self.muted),self.tabs,self.search,self.materials]))
        self.right=ft.Container(width=258,padding=16,bgcolor=self.surface,content=ft.Column(controls=[
            ft.Row(controls=[ft.Container(expand=True,content=self.selection),ft.IconButton(ft.Icons.TUNE,tooltip='纸页设置',on_click=lambda e:self.select(-1))]),self.properties,ft.Divider(height=1),ft.Text('图层 · 上方在最前',size=11,color=self.muted),self.layers]))
        self.drop_target=ft.DragTarget(group='notebook-material',content=self.canvas,on_accept=self.accept_material)
        self.paper_host=ft.Container(content=self.drop_target,alignment=ft.Alignment.CENTER,padding=40)
        scroll_row=ft.Row(controls=[self.paper_host],scroll=ft.ScrollMode.AUTO,alignment=ft.MainAxisAlignment.CENTER)
        desk=ft.Container(expand=True,bgcolor='#252A2A' if theme.DARK else '#E6E5DF',content=ft.ListView(expand=True,controls=[scroll_row]))
        zoom_tools=ft.Container(padding=8,content=ft.Row(alignment=ft.MainAxisAlignment.CENTER,controls=[
            ft.IconButton(ft.Icons.REMOVE,tooltip='缩小画布',on_click=lambda e:self.set_zoom(self.zoom-.2)),self.zoom_label,
            ft.IconButton(ft.Icons.ADD,tooltip='放大画布',on_click=lambda e:self.set_zoom(self.zoom+.2)),
            ft.TextButton('适合窗口',on_click=lambda e:self.set_zoom(1)),
            ft.Text('拖动摆放 · 右下角拖动缩放',size=11,color=self.muted)]))
        center=ft.Column(expand=True,spacing=0,controls=[desk,zoom_tools])
        pagebar=ft.Container(padding=10,bgcolor=self.surface,content=ft.Row(controls=[self.page_strip,
            ft.TextButton('新增纸页',icon=ft.Icons.ADD,on_click=self.add_page)]))
        self.chrome=ft.Container(height=32,bgcolor=self.surface,content=ft.Row(spacing=2,controls=[
            ft.WindowDragArea(expand=True,content=ft.Container(padding=ft.Padding.only(left=18),content=ft.Text('客行录  /  手账工作台',size=11,color=self.muted))),
            ft.IconButton(ft.Icons.REMOVE,icon_size=15,tooltip='最小化',on_click=self.minimize),
            ft.IconButton(ft.Icons.CROP_SQUARE,icon_size=14,tooltip='最大化 / 还原',on_click=self.maximize),
            ft.IconButton(ft.Icons.CLOSE,icon_size=15,tooltip='关闭窗口',on_click=lambda e:self.request_close(close_window=True))]))
        self.view=ft.View(horizontal_alignment=ft.CrossAxisAlignment.STRETCH,route='/notebook-studio',padding=0,spacing=1,bgcolor=theme.LINE,can_pop=False,
            on_confirm_pop=lambda e:self.request_close(),data={'notebook_studio':self},controls=[self.chrome,toolbar,
            ft.Row(expand=True,spacing=1,vertical_alignment=ft.CrossAxisAlignment.STRETCH,controls=[self.left,center,self.right]),
            pagebar,ft.Container(padding=ft.Padding.only(left=16,right=16,bottom=6),bgcolor=self.surface,content=self.status)])

    def open(self,fullscreen=False):
        if fullscreen:self.page.window.full_screen=True
        self.chrome.visible=not self.page.window.full_screen
        self.full_button.content='退出全屏' if self.page.window.full_screen else '全屏创作'
        if not getattr(self,'styled',False):
            self.styled=True
            self.view.controls=[ft.Container(expand=True,theme=ft.Theme(color_scheme_seed=self.accent,
                text_button_theme=ft.TextButtonTheme(style=ft.ButtonStyle(color=self.accent)),
                outlined_button_theme=ft.OutlinedButtonTheme(style=ft.ButtonStyle(color=self.accent)),
                filled_button_theme=ft.FilledButtonTheme(style=ft.ButtonStyle(bgcolor=self.accent,color='#FFFFFF')),
                icon_button_theme=ft.IconButtonTheme(style=ft.ButtonStyle(color=self.accent))),
                content=ft.Column(expand=True,spacing=1,horizontal_alignment=ft.CrossAxisAlignment.STRETCH,controls=self.view.controls))]
        self.page.views.append(self.view)
        self.page.on_resize=self.resize;self.page.on_keyboard_event=self.keyboard
        self.page.window.prevent_close=True;self.page.window.on_event=self.window_event
        self.resize(update=False);self.refresh();return self

    @property
    def item(self):return self.book['pages'][self.index]

    @property
    def design(self):
        if 'design' not in self.item:self.item['design']=make_design(self.item)
        return self.item['design']

    def current(self):
        return self.design['elements'][self.selected] if 0<=self.selected<len(self.design['elements']) else None

    def checkpoint(self,group=None):
        now=time.monotonic()
        if not group or group!=self.group or now-self.group_time>.6:
            self.undo_stack.append((deepcopy(self.book),self.index))
            self.undo_stack=self.undo_stack[-40:]
        self.group=group;self.group_time=now;self.redo_stack.clear()

    def changed(self,message='有未保存的修改'):
        self.status.value=message
        self.undo_button.disabled=not self.undo_stack;self.redo_button.disabled=not self.redo_stack

    def refresh(self):
        self.draw();self.inspect();self.paint_layers();self.paint_pages();self.paint_materials()
        self.undo_button.disabled=not self.undo_stack;self.redo_button.disabled=not self.redo_stack
        self.page.update()

    def draw(self):
        self.canvas.shadow=ft.BoxShadow(blur_radius=28,offset=ft.Offset(0,9),color='#20000000')
        self.canvas.width=self.width;self.canvas.height=self.width*580/420
        self.canvas.content=native_canvas(self.design,self.width,interactive=self.interact,selected=self.selected)
        self.add_handle()
        self.paper_host.width=max(self.width+80,(self.page.width or 1200)-self.left.width-self.right.width-6)
        self.paper_host.height=self.canvas.height+80

    def add_handle(self):
        stack=self.canvas.content.content
        handle=next((c for c in stack.controls if c.data=='resize_handle'),None)
        obj=self.current()
        if obj and not obj.get('locked') and not obj.get('hidden'):
            k=self.width/420
            if handle:
                handle.left=(obj['x']+obj['w'])*k-8;handle.top=(obj['y']+obj['h'])*k-8
                return
            stack.controls.append(ft.GestureDetector(left=(obj['x']+obj['w'])*k-8,
                top=(obj['y']+obj['h'])*k-8,width=16,height=16,data='resize_handle',
                content=ft.Container(bgcolor='#527B9B',border=ft.Border.all(2,'#FFFFFF'),border_radius=3),
                drag_interval=32,on_pan_start=lambda e:self.checkpoint(),on_pan_update=self.drag_resize,
                on_pan_end=lambda e:(self.inspect(),self.page.update())))
        elif handle:stack.controls.remove(handle)

    def interact(self,action,index,event):
        if not self.alive:return
        if action=='clear':self.select(-1);return
        if action=='end':
            self.inspect();self.page.update();return
        if action in ('select','start'):
            if action=='start':self.checkpoint()
            if action=='start' and self.selected==index:
                ft.context.disable_auto_update();return
            self.selected=index
            for c in self.canvas.content.content.controls:
                if isinstance(c.data,dict) and 'collage_element' in c.data:
                    c.content.content.border=ft.Border.all(1.5,'#668EA6') if c.data['collage_element']==index else None
            self.add_handle();self.inspect();self.paint_layers();self.page.update()
        elif self.selected==index and self.current() and not self.current().get('locked') and event.local_delta:
            obj=self.design['elements'][index];delta=event.local_delta;k=self.width/420
            obj['x']=max(0,min(420-obj['w'],obj['x']+delta.x/k))
            obj['y']=max(0,min(580-obj['h'],obj['y']+delta.y/k))
            node=next(c for c in self.canvas.content.content.controls if c.data=={'collage_element':index})
            node.left=obj['x']*k;node.top=obj['y']*k
            self.add_handle();self.changed()
            node.update()
            handle=next((c for c in self.canvas.content.content.controls if c.data=='resize_handle'),None)
            if handle:handle.update()

    def drag_resize(self,e):
        obj=self.current()
        if not obj or obj.get('locked') or not e.local_delta:return
        k=self.width/420
        obj['w']=max(25,min(420-obj['x'],obj['w']+e.local_delta.x/k))
        obj['h']=max(25,min(580-obj['y'],obj['h']+e.local_delta.y/k))
        # Update the existing handle and element so Flutter keeps the gesture.
        for c in self.canvas.content.content.controls:
            if c.data=={'collage_element':self.selected}:
                c.width=obj['w']*k;c.height=obj['h']*k
                c.content.content.width=c.width;c.content.content.height=c.height
                if obj['kind'] in ('image','photo'):
                    c.content.content.content.width=max(1,c.width-(14*k if obj['kind']=='photo' else 0))
                    c.content.content.content.height=max(1,c.height-(28*k if obj['kind']=='photo' else 0))
            elif c.data=='resize_handle':
                c.left=(obj['x']+obj['w'])*k-8;c.top=(obj['y']+obj['h'])*k-8
        self.changed();self.canvas.update();self.status.update()

    def select(self,index):
        self.selected=index;self.draw();self.inspect();self.paint_layers();self.page.update()

    def change(self,key,value):
        obj=self.current()
        if obj is None or (obj.get('locked') and key!='locked'):return
        self.checkpoint((self.index,self.selected,key));obj[key]=value
        obj['x']=max(0,min(obj['x'],420-obj['w']));obj['y']=max(0,min(obj['y'],580-obj['h']))
        self.changed()
        from notebook_collage import native_element
        node=next((c for c in self.canvas.content.content.controls if c.data=={'collage_element':self.selected}),None)
        if node:
            k=self.width/420
            node.left=obj['x']*k;node.top=obj['y']*k;node.width=obj['w']*k;node.height=obj['h']*k
            node.ignore_interactions=obj.get('locked',False)
            node.content.content=native_element(obj,k);node.content.content.border=ft.Border.all(1.5,'#668EA6')
            self.add_handle();self.canvas.update()
        self.paint_layers();self.layers.update();self.status.update();self.undo_button.update();self.redo_button.update()

    def field(self,label,value,callback,**kw):
        return ft.TextField(label=label,value=value,dense=True,text_size=12,color=self.ink,
            border_color=theme.LINE,on_change=callback,**kw)

    def dropdown(self,label,value,options,callback):
        return ft.Dropdown(label=label,value=value,dense=True,text_size=12,
            options=[ft.dropdown.Option(k,v) for k,v in options],on_select=callback)

    def slider(self,label,key,low,high):
        return ft.Column(spacing=0,controls=[ft.Text(label,size=11,color=self.muted),
            ft.Slider(min=low,max=high,value=max(low,min(high,self.current().get(key,1 if key=='opacity' else low))),
                divisions=100 if key=='opacity' else int(high-low),label='{value}',
                on_change=lambda e:self.change(key,e.control.value))])

    def toggle_text_style(self,key):
        self.change(key,not self.current().get(key,False));self.inspect();self.page.update()

    def inspect(self):
        obj=self.current();self.selection.value='元素样式' if obj else '纸页设置'
        if obj is None:
            self.properties.controls=[self.field('本页标题',self.item['title'],self.page_title),
                ft.Text('从左侧挑选素材，或点击纸页上的元素。\n右侧可编辑文字、样式、尺寸与图层。',size=12,color=self.muted),
                ft.TextButton('前移纸页',disabled=self.index==0,on_click=lambda e:self.move_page(-1)),
                ft.TextButton('后移纸页',disabled=self.index==len(self.book['pages'])-1,on_click=lambda e:self.move_page(1)),
                ft.TextButton('复制纸页',on_click=self.copy_page),
                ft.TextButton('删除纸页',disabled=len(self.book['pages'])<=1,on_click=self.remove_page)]
            return
        controls=[ft.Switch(label='锁定元素',value=obj.get('locked',False),on_change=lambda e:(self.change('locked',e.control.value),self.inspect(),self.page.update()))]
        if obj['kind'] in ('image','photo'):
            controls.append(ft.Switch(label='白边相纸',value=obj['kind']=='photo',on_change=lambda e:self.change('kind','photo' if e.control.value else 'image')))
        if obj['kind'] not in ('photo','image','tape'):
            controls.extend([self.field('文字内容',obj.get('text',''),lambda e:self.change('text',e.control.value),multiline=True,min_lines=2,max_lines=5),
                self.dropdown('字体',obj.get('font','Microsoft YaHei'),FONTS.items(),lambda e:self.change('font',e.control.value)),
                self.slider('字号','size',10,90),
                ft.Row(spacing=1,controls=[ft.IconButton(icon,tooltip=label,icon_size=18,
                    style=ft.ButtonStyle(bgcolor=self.soft if obj.get(key) else None),
                    on_click=lambda e,k=key:self.toggle_text_style(k))
                    for key,label,icon in [('bold','粗体',ft.Icons.FORMAT_BOLD),('italic','斜体',ft.Icons.FORMAT_ITALIC),('underline','下划线',ft.Icons.FORMAT_UNDERLINED),('shadow','投影',ft.Icons.TEXT_FIELDS)]]),
                self.dropdown('文字对齐',obj.get('align','left'),[('left','左对齐'),('center','居中'),('right','右对齐')],lambda e:self.change('align',e.control.value))])
        controls.append(ft.ExpansionTile(title=ft.Text('尺寸、角度与透明度',size=12,color=self.muted),
            controls=[self.slider('宽度','w',25,420),self.slider('高度','h',25,580),self.slider('旋转角度','rotation',-180,180),self.slider('不透明度','opacity',.1,1)]))
        for key,label in [('color','文字颜色'),('background','底色'),('highlight','文字荧光底色')]:
            if key!='background' and obj['kind'] in ('photo','image','tape'):continue
            controls.extend([ft.Text(label,size=11,color=self.muted),ft.Row(wrap=True,spacing=6,controls=[
                ft.Container(width=23,height=23,bgcolor=color or self.surface,border=ft.Border.all(1,theme.LINE),border_radius=5,
                    tooltip='无底色' if not color else color,on_click=lambda e,k=key,c=color:self.change(k,c))
                for color in ([''] if key!='color' else [])+['#34465B','#FFFFFF','#C17986','#67836B','#82AFC3','#EEDDAA','#DFD5EB']])])
        controls.append(ft.Row(wrap=True,controls=[ft.TextButton('上移一层',on_click=lambda e:self.layer(1)),
            ft.TextButton('下移一层',on_click=lambda e:self.layer(-1)),ft.TextButton('复制元素',on_click=self.duplicate),
            ft.TextButton('删除元素',on_click=self.remove)]))
        for control in controls[1:]:control.disabled=obj.get('locked',False)
        self.properties.controls=controls

    def paint_layers(self):
        self.layers.controls=[]
        for i,obj in reversed(list(enumerate(self.design['elements']))):
            label=obj.get('name') or obj.get('text') or {'photo':'相片','image':'导入贴图','tape':'胶带'}.get(obj['kind'],'元素')
            self.layers.controls.append(ft.Container(bgcolor=self.soft if i==self.selected else None,padding=3,
                content=ft.Row(controls=[ft.TextButton(('🔒 ' if obj.get('locked') else '')+str(label).replace('\n',' ')[:14],expand=True,
                    on_click=lambda e,n=i:self.select(n)),ft.IconButton(ft.Icons.VISIBILITY_OFF if obj.get('hidden') else ft.Icons.VISIBILITY,
                    icon_size=15,tooltip='显示或隐藏图层',on_click=lambda e,n=i:self.hide_layer(n))])))

    def paint_pages(self):
        self.page_strip.controls=[ft.OutlinedButton(f'{i+1:02d}  {p["title"][:10] or "空白页"}',
            disabled=i==self.index,on_click=lambda e,n=i:self.goto(n)) for i,p in enumerate(self.book['pages'])]

    def material_card(self,name,obj):
        from notebook_collage import native_element
        image_kind=obj['kind'] in ('image','photo')
        thumb=(ft.Image(src=preview_image(obj['image']),width=76,height=76,fit=ft.BoxFit.CONTAIN) if image_kind else
            ft.Container(width=76,height=76,alignment=ft.Alignment.CENTER,
                content=native_element(obj,min(76/obj['w'],76/obj['h']))))
        face=ft.Container(width=91,height=112,padding=7,bgcolor=self.surface,border_radius=9,
            border=ft.Border.all(1,theme.LINE),on_click=lambda e:self.append(deepcopy(obj)),
            content=ft.Column(spacing=5,horizontal_alignment=ft.CrossAxisAlignment.CENTER,controls=[thumb,
                ft.Text(name,size=10,color=self.muted,max_lines=1,overflow=ft.TextOverflow.ELLIPSIS)]))
        payload={'material_element':obj,'drag_anchor':ft.Offset(45.5,56)}
        def anchor(e):
            payload['drag_anchor']=e.local_position
            # Coordinates are Python-only state; never reconcile the view on hover.
            ft.context.disable_auto_update()
        return ft.Draggable(group='notebook-material',data=payload,
            content=ft.GestureDetector(content=face,on_enter=anchor,on_hover=anchor,on_tap_down=anchor,hover_interval=48),
            max_simultaneous_drags=1,content_when_dragging=ft.Container(width=91,height=112,bgcolor=self.soft,border_radius=9),
            content_feedback=ft.Container(width=95,height=95,padding=8,bgcolor=self.surface,border_radius=10,
                shadow=ft.BoxShadow(blur_radius=14,color='#30000000'),
                content=native_element(obj,min(79/obj['w'],79/obj['h']))))

    def accept_material(self,e):
        source=getattr(e,'src',None)
        if not source or not isinstance(source.data,dict) or 'material_element' not in source.data:return
        obj=deepcopy(source.data['material_element']);point=e.local_position
        if point is None:return
        # Pointer coordinates are relative to the paper itself, including scrolling.
        # Desktop runtime reports feedback origin; retain the source grab offset.
        anchor=source.data.get('drag_anchor',ft.Offset(0,0))
        x=(point.x+anchor.x)*420/self.width;y=(point.y+anchor.y)*420/self.width
        if not (0<=x<=420 and 0<=y<=580):return
        obj['x']=max(0,min(420-obj['w'],x-obj['w']/2))
        obj['y']=max(0,min(580-obj['h'],y-obj['h']/2))
        self.append(obj)
        self.status.value='已放入纸页 · 可继续拖动或调整样式';self.status.update()

    def choose_category(self,key):
        self.category.value=key;self.search.value='';self.material_page=0;self.paint_materials();self.search.update()

    def search_materials(self,e):
        self.material_page=0;self.paint_materials()

    def browse_materials(self,delta):
        self.material_page+=delta;self.paint_materials()

    def paint_materials(self):
        key=self.category.value;controls=[]
        signature=(key,self.search.value,self.material_page,self.importing,
            tuple(m['id'] for m in self.book.get('materials',[])),
            (self.index,self.design['paper'],self.book['style'],self.book.get('subtitle')) if key=='paper' else None)
        if signature==self.material_signature:return
        self.material_signature=signature
        self.tabs.controls=[ft.TextButton(label,on_click=lambda e,k=k:self.choose_category(k),
            style=ft.ButtonStyle(bgcolor=self.soft if k==key else None,color=self.ink if k==key else self.muted))
            for k,label in [('sticker','插画'),('travel','旅行'),('daily','生活'),('frame','边框'),('tape','胶带'),('note','便笺'),('text','文字'),('import','我的'),('paper','纸页')]]
        items=[]
        if key=='text':items=[(name,element(**values)) for name,values in TEXT_PRESETS.items()]
        elif key in ('sticker','travel','daily','frame','tape','note'):items=catalog(key)
        elif key=='import':
            controls=[ft.OutlinedButton('导入自己的贴图',icon=ft.Icons.ADD,disabled=self.importing,on_click=self.import_materials),
                ft.Text('透明 PNG / JPG / WebP / BMP\n导入后可拖动，素材随本册保存。',size=11,color=self.muted)]
            for m in self.book.get('materials',[]):
                aspect=m['aspect'];w=min(220,200*aspect)
                items.append((m['name'],element('image',image=m['image'],mime='image/png',name=m['name'],text='',w=w,h=w/aspect)))
            if self.book.get('materials'):
                controls.append(ft.TextButton('整理我的素材',on_click=self.manage_materials))
        else:
            controls=[self.dropdown('本页纸张',self.design['paper'],[(k,v[0]) for k,v in PAPERS.items()],self.set_paper),
                ft.Text('选择版式作为起点，可撤销',size=11,color=self.muted)]
            controls.extend(ft.OutlinedButton(label,on_click=lambda e,k=k:self.apply_layout(k)) for k,label in LAYOUTS.items())
            controls.extend([ft.Divider(),self.dropdown('封面装帧',self.book['style'],[(k,v[0]) for k,v in journal.STYLES.items()],self.set_cover),
                self.field('封面寄语',self.book.get('subtitle',''),self.subtitle,multiline=True,min_lines=2,max_lines=4)])
        if key!='paper':
            query=(self.search.value or '').strip().lower()
            found=[(name,obj) for name,obj in items if not query or query in name.lower()]
            controls.append(ft.Text(f'{len(found)} 款素材 · 拖入或点选',size=10,color=self.muted))
            pages=max(1,(len(found)+11)//12);self.material_page=max(0,min(self.material_page,pages-1))
            controls.append(ft.Row(wrap=True,spacing=8,run_spacing=8,controls=[self.material_card(name,obj) for name,obj in found[self.material_page*12:(self.material_page+1)*12]]))
            if pages>1:
                controls.insert(len(controls)-1,ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN,controls=[
                    ft.IconButton(ft.Icons.CHEVRON_LEFT,tooltip='上一组素材',disabled=self.material_page==0,on_click=lambda e:self.browse_materials(-1)),
                    ft.Text(f'{self.material_page+1} / {pages}',size=11,color=self.muted),
                    ft.IconButton(ft.Icons.CHEVRON_RIGHT,tooltip='下一组素材',disabled=self.material_page==pages-1,on_click=lambda e:self.browse_materials(1))]))
            if not found:controls.append(ft.Text('没有匹配的素材，试试其他名称。' if query else '导入你喜欢的照片和贴纸。',size=12,color=self.muted))
        self.materials.controls=controls
        try:self.materials.update();self.tabs.update()
        except RuntimeError:pass

    def manage_materials(self,e):
        listing=ft.ListView(width=360,height=330,spacing=8)
        def refresh():
            listing.controls=[ft.Row(controls=[ft.Text(m['name'],expand=True,max_lines=1),
                ft.TextButton('移除',on_click=lambda e,m=m:remove(m))]) for m in self.book.get('materials',[])]
        def remove(m):self.remove_material(m);refresh();self.page.update()
        refresh()
        self.page.show_dialog(ft.AlertDialog(title=ft.Text('我的素材'),content=listing,
            actions=[ft.TextButton('完成',on_click=lambda e:self.page.pop_dialog())]))

    def append(self,obj):
        self.checkpoint();self.design['elements'].append(obj);self.selected=len(self.design['elements'])-1
        self.changed()
        # Keep the mounted paper and material controls; insert only the new layer.
        from notebook_collage import native_element_node
        stack=self.canvas.content.content
        for c in stack.controls:
            if isinstance(c.data,dict) and 'collage_element' in c.data:c.content.content.border=None
        stack.controls.append(native_element_node(obj,self.selected,self.width/420,self.interact,self.selected))
        self.add_handle();self.inspect();self.paint_layers()
        self.canvas.update();self.right.update();self.status.update();self.undo_button.update();self.redo_button.update()

    async def import_materials(self,e):
        if self.importing:return
        self.importing=True;self.paint_materials()
        try:
            files=await self.picker.pick_files(allow_multiple=True,file_type=ft.FilePickerFileType.CUSTOM,
                allowed_extensions=['png','jpg','jpeg','webp','bmp'])
            materials=[];failed=0
            for file in files or []:
                result=await asyncio.to_thread(snapshot_sticker,file.path)
                if result:materials.append(dict(result,name=Path(file.path).name,id=uuid.uuid4().hex))
                else:failed+=1
            if not self.alive:return
            if materials:
                self.checkpoint();self.book.setdefault('materials',[]).extend(materials)
                self.changed(f'已导入 {len(materials)} 个素材'+(f'，{failed} 个读取失败' if failed else '')+' · 记得保存手账')
            elif failed:self.status.value='所选图片无法读取，请选择其他文件。'
        except Exception as error:self.status.value='导入失败：'+str(error)
        finally:
            self.importing=False
            if self.alive:self.paint_materials();self.page.update()

    def add_material(self,m):
        aspect=m['aspect'];w=min(220,200*aspect);h=w/aspect
        self.append(element('image',image=m['image'],mime='image/png',name=m['name'],text='',w=w,h=h,x=65,y=135))

    def remove_material(self,m):
        self.checkpoint();self.book['materials']=[v for v in self.book['materials'] if v['id']!=m['id']]
        self.changed();self.paint_materials();self.page.update()

    def layer(self,direction):
        i=self.selected;j=i+direction
        if i>=0 and 0<=j<len(self.design['elements']) and not self.current().get('locked'):
            self.checkpoint();a=self.design['elements'];a[i],a[j]=a[j],a[i];self.selected=j;self.changed();self.refresh()

    def hide_layer(self,index):
        self.checkpoint();obj=self.design['elements'][index];obj['hidden']=not obj.get('hidden',False)
        self.changed();self.refresh()

    def duplicate(self,e=None):
        if self.current():
            obj=deepcopy(self.current());obj['locked']=False
            obj['x']=min(420-obj['w'],obj['x']+12);obj['y']=min(580-obj['h'],obj['y']+12);self.append(obj)

    def remove(self,e=None):
        if self.current() and not self.current().get('locked'):
            self.checkpoint();self.design['elements'].pop(self.selected);self.selected=-1;self.changed();self.refresh()

    def rename(self,e):
        self.checkpoint('book-title');self.book['title']=e.control.value;self.changed();self.status.update()

    def page_title(self,e):
        self.checkpoint(('page-title',self.index));self.item['title']=e.control.value
        self.changed();self.paint_pages();self.page.update()

    def goto(self,index):self.index=index;self.selected=-1;self.group=None;self.refresh()

    def add_page(self,e=None):
        self.checkpoint();self.book['pages'].append(dict(title='空白页',place='',date='',note='',photos=[],design=make_design({},'blank')))
        self.changed();self.goto(len(self.book['pages'])-1)

    def copy_page(self,e):
        self.checkpoint();self.book['pages'].insert(self.index+1,deepcopy(self.item));self.changed();self.goto(self.index+1)

    def move_page(self,delta):
        other=self.index+delta
        if 0<=other<len(self.book['pages']):
            self.checkpoint();a=self.book['pages'];a[self.index],a[other]=a[other],a[self.index];self.changed();self.goto(other)

    def remove_page(self,e):
        def remove(e):
            self.page.pop_dialog();self.checkpoint();self.book['pages'].pop(self.index)
            self.changed();self.goto(min(self.index,len(self.book['pages'])-1))
        self.page.show_dialog(ft.AlertDialog(modal=True,title=ft.Text('删除这一页？'),content=ft.Text('只删除手账纸页，原旅行日志不变。'),
            actions=[ft.TextButton('取消',on_click=lambda e:self.page.pop_dialog()),ft.TextButton('删除',on_click=remove)]))

    def set_paper(self,e):
        self.checkpoint();self.design['paper']=e.control.value;self.changed();self.draw();self.page.update()

    def subtitle(self,e):
        self.checkpoint('subtitle');self.book['subtitle']=e.control.value;self.changed();self.page.update()

    def set_cover(self,e):self.checkpoint();self.book['style']=e.control.value;self.changed();self.page.update()

    def apply_layout(self,key):
        self.checkpoint();self.item['design']=make_design(self.item,key,self.design['paper']);self.selected=-1
        self.changed('已套用版式 · 可撤销');self.refresh()

    def undo(self,redo=False):
        source=self.redo_stack if redo else self.undo_stack;target=self.undo_stack if redo else self.redo_stack
        if not source:return
        target.append((deepcopy(self.book),self.index));book,index=source.pop();book_id=self.book.get('id')
        self.book=book
        if book_id:self.book['id']=book_id
        self.index=index;self.selected=-1;self.group=None;self.name.value=self.book['title']
        self.changed('已重做' if redo else '已撤销');self.refresh()

    def set_zoom(self,value):self.zoom=max(.5,min(2.4,value));self.resize()

    def resize(self,e=None,update=True):
        available=self.page.width or 1200
        self.left.width=220 if available<1150 else 246;self.right.width=220 if available<1150 else 258
        fit=max(140,min(460,available-self.left.width-self.right.width-100,((self.page.height or 850)-282)*420/580))
        self.width=fit*self.zoom;self.zoom_label.value=f'{round(self.width/420*100)}%'
        if update:self.draw();self.page.update()

    def minimize(self,e):self.page.window.minimized=True;self.page.update()

    def maximize(self,e):self.page.window.maximized=not self.page.window.maximized;self.page.update()

    def fullscreen(self,e=None):
        self.page.window.full_screen=not self.page.window.full_screen
        self.chrome.visible=not self.page.window.full_screen
        self.full_button.content='退出全屏' if self.page.window.full_screen else '全屏创作';self.page.update()

    def keyboard(self,e):
        # Native text fields retain their own undo and deletion behavior.
        if e.key=='F11':self.fullscreen()
        elif e.key=='Escape' and self.page.window.full_screen:self.fullscreen()
        elif (e.ctrl or e.meta) and e.key.lower()=='s':self.save()

    def window_event(self,e):
        if str(e.type).lower().endswith('close'):self.request_close(close_window=True)

    def save(self):
        try:
            journal.save_book(self.book);self.saved=deepcopy(self.book)
            self.status.value='已保存 · 纸页与导入素材均已保存在本机';self.page.update();return True
        except Exception as error:
            self.status.value='保存失败：'+str(error);self.page.update();return False

    async def export(self,e):
        try:
            name=re.sub(r'[<>:"/\\|?*\x00-\x1f]','_',self.book['title']).strip('. ') or '旅行手账'
            path=await self.picker.save_file(file_name=name+'.html',file_type=ft.FilePickerFileType.CUSTOM,allowed_extensions=['html'])
            if path:
                await asyncio.to_thread(journal.export_html,deepcopy(self.book),path)
                self.status.value='已导出离线电子手账';self.page.update()
        except Exception as error:self.status.value='导出失败：'+str(error);self.page.update()

    def preview(self,e):
        async def turn(direction):
            old=viewer.index;target=(0 if old<0 else old//2*2+2) if direction>0 else (old//2*2-2 if old>=2 else -1)
            if -1<=target<len(self.book['pages']):await viewer.turn_to(target)
        viewer=NotebookBook(self.book,min(920,(self.page.width or 1200)-140),max(280,min(580,(self.page.height or 850)-200)),turn)
        self.page.show_dialog(ft.AlertDialog(modal=True,title=ft.Text('翻页预览'),content=viewer,actions=[
            ft.TextButton('上一页',on_click=lambda e:self.page.run_task(turn,-1)),
            ft.TextButton('下一页',on_click=lambda e:self.page.run_task(turn,1)),
            ft.FilledButton('继续创作',on_click=lambda e:self.page.pop_dialog())]))

    def request_close(self,close_window=False):
        if not self.alive or getattr(self,'exit_dialog',None):return
        if self.importing:
            self.status.value='正在导入素材，请稍候再退出';self.page.update();return
        if self.saved==self.book:self.close(close_window);return
        def save_close(e):
            if self.save():after_dialog_closed(self.page,lambda:self.close(close_window))
        def discard(e):after_dialog_closed(self.page,lambda:self.close(close_window))
        def reset(e):self.exit_dialog=None
        def continue_editing(e):after_dialog_closed(self.page,lambda:reset(None))
        self.exit_dialog=ft.AlertDialog(modal=True,title=ft.Text('保存这次创作？'),content=ft.Text('未保存的纸页修改和新导入素材会丢失。'),
            on_dismiss=reset,actions=[
            ft.TextButton('继续编辑',on_click=continue_editing),ft.TextButton('放弃修改',on_click=discard),
            ft.FilledButton('保存并退出',on_click=save_close)])
        self.page.show_dialog(self.exit_dialog)

    def close(self,close_window=False):
        if not self.alive:return
        self.alive=False
        self.page.on_resize=self.old_resize;self.page.on_keyboard_event=self.old_keyboard
        self.page.window.full_screen=self.old_full;self.page.window.prevent_close=self.old_close
        self.page.window.on_event=self.old_window_event
        if self.picker in self.page.services:self.page.services.remove(self.picker)
        if self.view in self.page.views:self.page.views.remove(self.view)
        self.page.update();self.on_close();self.page.update()
        if close_window:self.page.run_task(self.page.window.destroy)


def open_studio(page,book,on_close,index=0,fullscreen=False):
    return NotebookStudio(page,book,on_close,index).open(fullscreen=fullscreen)

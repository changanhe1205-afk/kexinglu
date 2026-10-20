"""A draft-only, per-page scrapbook canvas; applying is an explicit action."""
from i18n import tr
import asyncio
from copy import deepcopy
import flet as ft
import theme
import travel_journal as journal
from notebook_collage import PAPERS, LAYOUTS, STICKERS, element, make_design, native_canvas


def open_designer(page,item,on_apply):
    draft=deepcopy(item.get('design') or make_design(item))
    selected={'index':-1};history=[]
    width=max(240,min(420,(page.width or 1200)-480,(page.height or 900)*.63*420/580))
    canvas=ft.Container(width=width,height=width*580/420)
    properties=ft.Column(spacing=10)
    notice=ft.Text('点击选择，拖动摆放；每一页都可以有自己的样子。',size=12,color=theme.TEXT_SUB)
    picker=ft.FilePicker();page.services.append(picker)

    def checkpoint():
        history.append(deepcopy(draft))
        if len(history)>30:history.pop(0)

    def draw():
        canvas.content=native_canvas(draft,width,interactive=interact,selected=selected['index'])

    def current():
        i=selected['index']
        return draft['elements'][i] if 0<=i<len(draft['elements']) else None

    def interact(action,index,event):
        if action=='clear':
            selected['index']=-1;draw();inspect();page.update();return
        if action=='end':return
        if action in ('select','start'):
            checkpoint();selected['index']=index
            for node in canvas.content.content.controls:
                if isinstance(node.data,dict) and 'collage_element' in node.data:
                    node.content.content.border=ft.Border.all(1.5,'#668EA6') if node.data['collage_element']==index else None
            inspect();page.update()
        else:
            obj=draft['elements'][index];delta=event.local_delta
            if delta:
                obj['x']=max(0,min(420-obj['w'],obj['x']+delta.x*420/width))
                obj['y']=max(0,min(580-obj['h'],obj['y']+delta.y*420/width))
                # Keep the active gesture control alive throughout a drag.
                node=next(c for c in canvas.content.content.controls if c.data=={'collage_element':index})
                node.left=obj['x']*width/420;node.top=obj['y']*width/420;node.update()

    def change(key,value):
        obj=current()
        if obj is None:return
        checkpoint();obj[key]=value
        obj['x']=min(obj['x'],420-obj['w']);obj['y']=min(obj['y'],580-obj['h'])
        draw();page.update()

    def slider(label,key,low,high):
        return ft.Column(spacing=0,controls=[ft.Text(label,size=11,color=theme.TEXT_SUB),
            ft.Slider(min=low,max=high,value=current().get(key,low),divisions=int(high-low),
                label='{value}',on_change=lambda e:change(key,e.control.value))])

    def inspect():
        obj=current()
        if obj is None:
            properties.controls=[ft.Text('选中纸页上的内容\n编辑文字、大小与角度',size=13,color=theme.TEXT_SUB)]
            return
        properties.controls=[]
        if obj['kind'] not in ('photo','image','tape'):
            properties.controls.append(ft.TextField(label='文字内容',value=obj.get('text',''),multiline=True,
                min_lines=2,max_lines=5,on_change=lambda e:change('text',e.control.value)))
            properties.controls.append(slider('字号','size',10,90))
        properties.controls.extend([slider('宽度','w',35,390),slider('高度','h',25,520),slider('旋转角度','rotation',-30,30)])
        properties.controls.append(ft.Row(wrap=True,controls=[ft.Container(width=23,height=23,bgcolor=color,
            border_radius=12,tooltip=color,on_click=lambda e,c=color:change('background' if obj['kind']=='tape' else 'color',c))
            for color in ['#34465B','#718766','#B66D77','#658FAA','#A98358','#FFFFFF']]))
        properties.controls.append(ft.Row(wrap=True,controls=[ft.TextButton('上移一层',on_click=lambda e:layer(1)),
            ft.TextButton('下移一层',on_click=lambda e:layer(-1)),ft.TextButton('复制',on_click=duplicate),
            ft.TextButton('删除元素',on_click=remove)]))

    def layer(direction):
        i=selected['index'];j=i+direction
        if 0<=j<len(draft['elements']):
            checkpoint();draft['elements'][i],draft['elements'][j]=draft['elements'][j],draft['elements'][i]
            selected['index']=j;draw();page.update()

    def append(obj):
        checkpoint();draft['elements'].append(obj);selected['index']=len(draft['elements'])-1
        draw();inspect();page.update()

    def duplicate(e):
        obj=deepcopy(current());obj['x']=min(420-obj['w'],obj['x']+12);obj['y']=min(580-obj['h'],obj['y']+12);append(obj)

    def remove(e):
        checkpoint();draft['elements'].pop(selected['index']);selected['index']=-1;draw();inspect();page.update()

    async def photo(e):
        files=await picker.pick_files(allow_multiple=False,file_type=ft.FilePickerFileType.CUSTOM,
                                     allowed_extensions=['jpg','jpeg','png','webp','bmp'])
        if files:
            image=await asyncio.to_thread(journal.snapshot_photo,files[0].path)
            if image:append(element('photo',image=image,text='',w=220,h=200))
            else:notice.value='这张图片无法读取，请换一张。';page.update()

    def apply_layout(e):
        checkpoint();replacement=make_design(item,e.control.value,draft['paper'])
        draft.clear();draft.update(replacement);selected['index']=-1;draw();inspect();page.update()

    def paper_changed(e):
        checkpoint();draft['paper']=e.control.value;draw();page.update()

    def undo(e):
        if history:
            draft.clear();draft.update(history.pop());selected['index']=-1
            paper.value=draft['paper'];layout.value=draft['layout'];draw();inspect();page.update()

    def close(apply):
        if apply:on_apply(deepcopy(draft))
        page.pop_dialog()
        if picker in page.services:page.services.remove(picker)
        page.update()

    paper=ft.Dropdown(label='本页纸张',value=draft['paper'],options=[ft.dropdown.Option(k,v[0]) for k,v in PAPERS.items()],on_select=paper_changed)
    layout=ft.Dropdown(label='套用版式（可撤销）',value=draft['layout'],options=[ft.dropdown.Option(k,v) for k,v in LAYOUTS.items()],on_select=apply_layout)
    tools=ft.ListView(width=270,spacing=12,controls=[paper,layout,
        ft.Row(wrap=True,controls=[ft.TextButton('添加文字',on_click=lambda e:append(element())),
            ft.TextButton('添加相片',on_click=photo),ft.TextButton('添加胶带',on_click=lambda e:append(element('tape',text='',w=140,h=28,background='#9BBBCB'))),
            ft.TextButton('添加便笺',on_click=lambda e:append(element(background='#FFF2C5',w=190,h=170)))]),
        ft.Text('贴纸小物',size=12,color=theme.TEXT_SUB),
        ft.Row(wrap=True,controls=[ft.TextButton(s,on_click=lambda e,t=s:append(element('sticker',text=t,size=55,w=90,h=90))) for s in STICKERS]),
        ft.Divider(),properties])
    draw();inspect()
    page.show_dialog(ft.AlertDialog(modal=True,bgcolor=theme.CARD_BG,title=ft.Text('设计这一页 · 自由拼贴'),
        content=ft.Container(width=width+310,height=width*580/420+42,content=ft.Column(controls=[
            ft.Row(expand=True,vertical_alignment=ft.CrossAxisAlignment.START,spacing=24,controls=[tools,canvas]),notice])),
        actions=[ft.TextButton(tr('撤销'),on_click=undo),ft.TextButton(tr('取消'),on_click=lambda e:close(False)),
                 ft.FilledButton('应用到这一页',on_click=lambda e:close(True))]))

"""Optional notebook shelf, composer and reader inside the travel page."""
from __future__ import annotations
from i18n import tr
import asyncio
import base64
from copy import deepcopy
import json
import re

import flet as ft
import theme
import travel_db
import travel_journal as journal
from notebook_book import NotebookBook, cover_thumbnail
from notebook_navigation import after_dialog_closed


def open_shelf(page, groups, selected=None):
    """Called only by the explicit notebook entry; never generates on navigation."""
    width = max(300, min(1040, (page.width or 1320) - 110))
    height = max(300, min(660, (page.height or 900) - 190))

    def dialog(title, content, actions):
        return ft.AlertDialog(modal=True, bgcolor=theme.CARD_BG,
            title=ft.Text(title, color=theme.TEXT_MAIN, size=20, weight=ft.FontWeight.W_600),
            content=ft.Container(width=width, height=height, content=content),
            actions=actions, shape=ft.RoundedRectangleBorder(radius=18))

    def text(value, size=13, color=None):
        return ft.Text(value, size=size, color=color or theme.TEXT_MAIN)

    def field(label, value='', **kwargs):
        return ft.TextField(label=label, value=value, color=theme.TEXT_MAIN,
            label_style=ft.TextStyle(color=theme.TEXT_SUB), border_color=theme.LINE,
            focused_border_color=theme.ACCENT, filled=True, fill_color=theme.CARD_BG_SOFT,
            text_size=13, **kwargs)

    def dropdown(label, options, value, callback=None):
        return ft.Dropdown(label=label, value=value, options=[ft.dropdown.Option(k, v) for k,v in options],
            on_select=callback, color=theme.TEXT_MAIN, bgcolor=theme.CARD_BG_SOFT,
            border_color=theme.LINE, label_style=ft.TextStyle(color=theme.TEXT_SUB))

    def replace(view):
        after_dialog_closed(page,lambda:page.show_dialog(view))

    def shelf():
        books=journal.list_books()
        rows=[text('把一次出发，或所有走过的地方，装订成自己的手账。', 14, theme.TEXT_SUB)]
        if not books:
            rows.append(ft.Container(padding=40, alignment=ft.Alignment.CENTER,
                content=ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER, controls=[
                    ft.Icon(ft.Icons.MENU_BOOK_ROUNDED, size=52, color=theme.ACCENT),
                    text('你的第一本旅行手账',22),
                    text('选择记录、写下感想，再慢慢编排。手账由你决定何时创建。',13,theme.TEXT_SUB)])))
        for book in books:
            def edit(e, key=book['id']):
                document=journal.get_book(key)
                if document:
                    start_document(document)
            def remove(e, item=book):
                def confirmed(e):
                    journal.delete_book(item['id'])
                    after_dialog_closed(page,lambda:replace(shelf()))
                page.show_dialog(ft.AlertDialog(modal=True, bgcolor=theme.CARD_BG,
                    title=text('删除这本手账？',18),
                    content=text('只删除「'+book_title(item)+'」，原旅行日志和照片仍会保留。'),
                    actions=[ft.TextButton(tr('取消'),on_click=lambda e:page.pop_dialog()),
                             ft.TextButton('删除手账',on_click=confirmed)]))
            rows.append(ft.Container(padding=18, border_radius=12, bgcolor=theme.CARD_BG_SOFT,
                border=ft.Border.only(left=ft.BorderSide(4,theme.ACCENT)),
                content=ft.Row(controls=[cover_thumbnail(book.get('style','paper'),book['title']),
                    ft.Column(expand=True,spacing=6,controls=[text(book['title'],17),
                        text('上次保存 · '+book['updated_at'][:16].replace('T',' '),11,theme.TEXT_SUB)]),
                    ft.TextButton('打开手账',on_click=edit),
                    ft.TextButton('经典编排',on_click=lambda e,key=book['id']:editor(journal.get_book(key))),
                    ft.IconButton(ft.Icons.DELETE_OUTLINE,tooltip='删除手账',on_click=remove)])))
        return dialog('旅行手账',ft.ListView(controls=rows,spacing=18),[
            ft.TextButton('返回旅行日志',on_click=lambda e:page.pop_dialog()),
            ft.TextButton(tr('新建空白手账'),on_click=blank_book),
            ft.FilledButton('新建手账',icon=ft.Icons.ADD,on_click=lambda e:creator())])

    def book_title(book):
        return book['title']

    def start_document(document,mode='studio'):
        if mode=='classic':editor(document);return
        from notebook_studio import open_studio
        after_dialog_closed(page,lambda:open_studio(page,document,
            lambda:page.show_dialog(shelf()),fullscreen=mode=='fullscreen'))

    def blank_book(e):
        name=field('手账名称','我的拼贴手账',max_length=80)
        def begin(e):
            if not name.value.strip():name.error_text='请填写手账名称';page.update();return
            from notebook_collage import make_design
            start_document({'title':name.value.strip(),'subtitle':'把日常留成珍藏。','style':'ocean','schema':3,
                'pages':[{'title':'今日手记','place':'','date':'','note':'','photos':[],
                          'design':make_design({},'blank')}]},'fullscreen')
        replace(dialog('创建自由手账',ft.Column(controls=[name,
            text('创建后直接进入全屏工作台。按 Esc 退出全屏，随时保存或翻页预览。',13,theme.TEXT_SUB)]),[
                ft.TextButton('返回书架',on_click=lambda e:replace(shelf())),ft.FilledButton('开始创作',on_click=begin)]))

    def creator():
        logs=travel_db.list_logs()
        if not logs:
            blank_book(None);return
        name=field('手账名称','我的旅行手账',max_length=80)
        subtitle=field('封面寄语','把路上的片刻，留在这一册。',multiline=True,min_lines=2,max_lines=3)
        style=dropdown('纸页风格',[(k,v[0]) for k,v in journal.STYLES.items()],'paper')
        choices=ft.Column(spacing=2)
        hint=text('',12,theme.TEXT_SUB)
        selected_ids=set()
        place=dropdown('选择地点',[(g['key'],g['name']) for g in groups],
                       selected or (groups[0]['key'] if groups else None))
        scope=dropdown('收录范围',[('place','某个地点'),('all','全部地点'),('record','某一次旅行记录')],
                       'place' if selected else 'all')
        record=dropdown('选择旅行记录',[(str(l['id']),f"{l.get('visit_date') or '日期待补'} · {l.get('title') or l.get('city') or '未命名地点'}") for l in logs],str(logs[0]['id']))

        def filter_records(e=None):
            place.visible=scope.value=='place'
            record.visible=scope.value=='record'
            ids=next(({l['id'] for l in g['logs']} for g in groups if g['key']==place.value),set())
            available=[l for l in logs if scope.value=='all' or
                       (scope.value=='place' and l['id'] in ids) or
                       (scope.value=='record' and str(l['id'])==record.value)]
            selected_ids.clear();selected_ids.update(l['id'] for l in available)
            def changed(e, key):
                selected_ids.add(key) if e.control.value else selected_ids.discard(key)
                hint.value=f'已选 {len(selected_ids)} 条记录 · 按旅行日期排列，可在下一步调整'
                page.update()
            choices.controls=[ft.Checkbox(label=f"{l.get('visit_date') or '日期待补'}　{l.get('title') or l.get('city') or '未命名地点'}",
                value=True, label_style=ft.TextStyle(color=theme.TEXT_MAIN),
                on_change=lambda e,key=l['id']:changed(e,key)) for l in available]
            hint.value=f'已选 {len(selected_ids)} 条记录 · 按旅行日期排列，可在下一步调整'
            page.update()
        scope.on_select=place.on_select=record.on_select=filter_records
        status=text('',12,theme.DANGER)

        async def create(e):
            if not name.value.strip() or not selected_ids:
                status.value='请填写手账名称，并至少选择一条记录。';page.update();return
            form.disabled=True;create_button.disabled=True;back.disabled=True
            status.value='正在整理照片与纸页…';page.update()
            try:
                document=await asyncio.to_thread(journal.new_book,
                    [l for l in logs if l['id'] in selected_ids],name.value.strip(),style.value,subtitle.value)
                start_document(document,'fullscreen')
            except Exception as error:
                status.value='整理失败，请重试：'+str(error)
                form.disabled=False;create_button.disabled=False;back.disabled=False;page.update()

        form=ft.ListView(spacing=14,controls=[name,subtitle,style,scope,place,record,
            hint,choices,text('照片与文字会复制进手账，之后可独立编辑。',12,theme.TEXT_SUB),status])
        back=ft.TextButton('返回书架',on_click=lambda e:replace(shelf()))
        create_button=ft.FilledButton('开始编排',on_click=create)
        replace(dialog('新建旅行手账',form,[back,create_button]))
        filter_records()

    def editor(document):
        book=deepcopy(document)
        initial=json.dumps(book,sort_keys=True,ensure_ascii=False) if book.get('id') else None
        position={'value':-1}
        status=text('尚未保存' if initial is None else '已载入本地手账',12,theme.TEXT_SUB)
        if book.get('missing_photos'):
            status.value=f"有 {book['missing_photos']} 张原照片无法读取，文字已保留；可在页内补充照片。"
        fields=ft.ListView(spacing=12)
        preview=ft.Container(expand=True,bgcolor='#343D55',border_radius=12)
        page_choice=dropdown('翻到',[], 'cover')
        saved={'value':initial}
        picker=ft.FilePicker()
        page.services.append(picker)

        def update_value(target,key,value):
            target[key]=value
            status.value='有未保存的修改'
            paint_preview();page.update()

        def paint_preview():
            viewer.render(position['value'])

        def bind_field(label,target,key,**kwargs):
            return field(label,target.get(key,''),on_change=lambda e:update_value(target,key,e.control.value),**kwargs)

        def turn(index):
            if viewer.busy:return
            position['value']=max(-1,min(index,len(book['pages'])-1))
            paint_fields();paint_preview();page.update()

        async def flip(direction):
            if viewer.busy:return
            old=position['value']
            target=(0 if old<0 else old//2*2+2) if direction>0 else (old//2*2-2 if old>=2 else -1)
            if target>=len(book['pages']) or target==old:return
            fields.disabled=True
            page_choice.disabled=True
            previous_button.disabled=next_button.disabled=True
            page.update()
            try:
                if await viewer.turn_to(target):
                    position['value']=target
            finally:
                fields.disabled=False;page_choice.disabled=False;paint_fields();page.update()

        async def previous(e):await flip(-1)
        async def following(e):await flip(1)

        viewer=NotebookBook(book,max(340,(width-50)*.65),max(280,height-112),flip)
        preview.content=viewer

        def move(delta):
            i=position['value'];j=i+delta
            if i>=0 and 0<=j<len(book['pages']):
                book['pages'][i],book['pages'][j]=book['pages'][j],book['pages'][i]
                status.value='已调整页序，记得保存';turn(j)

        def remove_page(e):
            def confirmed(e):
                book['pages'].pop(position['value']);page.pop_dialog()
                status.value='已移除纸页，记得保存';turn(position['value'])
            page.show_dialog(ft.AlertDialog(modal=True,bgcolor=theme.CARD_BG,
                title=text('移除当前页？',18),content=text('只移除手账中的这一页，原旅行记录不变。'),
                actions=[ft.TextButton(tr('取消'),on_click=lambda e:page.pop_dialog()),
                         ft.TextButton('移除',on_click=confirmed)]))

        async def add_photo(e):
            item=book['pages'][position['value']]
            files=await picker.pick_files(allow_multiple=True,file_type=ft.FilePickerFileType.CUSTOM,
                                         allowed_extensions=['jpg','jpeg','png','webp','bmp'])
            failed=0
            for file in files or []:
                encoded=await asyncio.to_thread(journal.snapshot_photo,file.path)
                if encoded:item['photos'].append({'image':encoded,'caption':'','included':True})
                else:failed+=1
            if files:
                status.value='照片已加入，记得保存' if not failed else f'{failed} 张照片无法读取，其余已加入'
                paint_fields();paint_preview();page.update()

        def enter_studio(e):
            if picker in page.services:page.services.remove(picker)
            start_document(book)

        def design_page(e):
            from notebook_collage_editor import open_designer
            item=book['pages'][position['value']]
            def applied(design):
                item['design']=design
                status.value='拼贴已应用，记得保存手账'
                paint_fields();paint_preview();page.update()
            open_designer(page,item,applied)

        def paint_fields():
            page_choice.options=[ft.dropdown.Option('cover','封面')]+[
                ft.dropdown.Option(str(i),f"{i+1:02d} · {p['title'] or '未命名页'}") for i,p in enumerate(book['pages'])]
            i=position['value'];page_choice.value='cover' if i<0 else str(i)
            previous_button.disabled=i<0
            next_button.disabled=i>=0 and i//2*2+2>=len(book['pages'])
            if i<0:
                style=dropdown('纸页风格',[(k,v[0]) for k,v in journal.STYLES.items()],book['style'],
                    lambda e:update_value(book,'style',e.control.value))
                fields.controls=[text('封面与装帧',16),bind_field('手账名称',book,'title',max_length=80),
                    bind_field('封面寄语',book,'subtitle',multiline=True,min_lines=3,max_lines=5),style,
                    ft.Row(wrap=True,spacing=12,run_spacing=14,controls=[ft.Container(
                        tooltip=journal.BINDINGS[k]['detail'],on_click=lambda e,key=k:(
                            update_value(book,'style',key),paint_fields(),page.update()),
                        content=ft.Column(spacing=7,controls=[cover_thumbnail(k,v[0],64,82),text(v[0],10)]))
                        for k,v in journal.STYLES.items()]),
                    text('每一页都可以独立编辑；翻到正文开始写手记。',12,theme.TEXT_SUB)]
            else:
                item=book['pages'][i]
                fields.controls=[ft.FilledButton('设计这一页 · 自由拼贴',icon=ft.Icons.DASHBOARD_CUSTOMIZE_OUTLINED,on_click=design_page),
                    text('拼贴页内容在设计画布中编辑；下方保留原始手记。' if item.get('design') else '自由摆放照片、文字、贴纸与胶带。',11,theme.TEXT_SUB),
                    bind_field('页标题',item,'title'),bind_field('地点',item,'place'),
                    bind_field('旅行日期',item,'date'),bind_field('这一页的手记',item,'note',multiline=True,min_lines=4,max_lines=8),
                    ft.Row(wrap=True,controls=[ft.TextButton('前移一页',disabled=i==0,on_click=lambda e:move(-1)),
                        ft.TextButton('后移一页',disabled=i==len(book['pages'])-1,on_click=lambda e:move(1)),
                        ft.TextButton('移除此页',disabled=len(book['pages'])==1,on_click=remove_page)]),
                    text('照片与图注',15),ft.TextButton(tr('添加照片'),icon=ft.Icons.ADD_PHOTO_ALTERNATE_OUTLINED,on_click=add_photo)]
                for n,photo in enumerate(item['photos'],1):
                    fields.controls.append(ft.Row(controls=[
                        ft.Image(src=base64.b64decode(photo['image']),width=56,height=50,fit=ft.BoxFit.COVER),
                        ft.Checkbox(label=f'收录照片 {n}',value=photo.get('included',True),
                            label_style=ft.TextStyle(color=theme.TEXT_MAIN),
                            on_change=lambda e,p=photo:update_value(p,'included',e.control.value))]))
                    fields.controls.append(bind_field(f'照片 {n} 图注',photo,'caption',multiline=True,max_lines=3))

        def add_page(e):
            if viewer.busy:return
            book['pages'].append({'title':'路上的一页','place':'','date':'','note':'','photos':[]})
            status.value='已添加空白页，记得保存';turn(len(book['pages'])-1)

        def save(e=None):
            try:
                journal.save_book(book)
                saved['value']=json.dumps(book,sort_keys=True,ensure_ascii=False)
                status.value='已保存到旅行手账，可随时回来续写'
            except Exception as error:
                status.value='保存失败：'+str(error)
            page.update()

        async def export(e):
            if not book['title'].strip():
                status.value='请先填写手账名称';page.update();return
            name=re.sub(r'[<>:"/\\|?*\x00-\x1f]','_',book['title']).strip('. ') or '旅行手账'
            try:
                output=await picker.save_file(dialog_title='导出离线电子手账',file_name=name+'.html',
                    file_type=ft.FilePickerFileType.CUSTOM,allowed_extensions=['html'])
                if output:
                    path=await asyncio.to_thread(journal.export_html,deepcopy(book),output)
                    status.value='已导出：'+str(path)
                    page.update()
            except Exception as error:
                status.value='导出失败：'+str(error);page.update()

        def close_editor(e):
            if viewer.busy:return
            def leave():
                if picker in page.services:page.services.remove(picker)
                replace(shelf())
            if saved['value']==json.dumps(book,sort_keys=True,ensure_ascii=False):
                leave();return
            def discard(e):after_dialog_closed(page,leave)
            page.show_dialog(ft.AlertDialog(modal=True,bgcolor=theme.CARD_BG,
                title=text('还有未保存的修改',18),content=text('返回书架前，是否继续编辑并保存？'),
                actions=[ft.TextButton(tr('放弃修改'),on_click=discard),
                         ft.FilledButton(tr('继续编辑'),on_click=lambda e:page.pop_dialog())]))

        page_choice.on_select=lambda e:turn(-1 if e.control.value=='cover' else int(e.control.value))
        left=ft.Column(expand=True,controls=[page_choice,fields])
        fields.expand=True;preview.expand=True
        reading={'value':False}
        def toggle_read(e):
            if viewer.busy:return
            reading['value']=not reading['value'];left.visible=not reading['value']
            viewer.resize_book(max(340,(width-50)*(1 if reading['value'] else .65)),max(280,height-112))
            e.control.content='继续编排' if reading['value'] else '阅读预览';page.update()
        previous_button=ft.TextButton('上一页',on_click=previous)
        next_button=ft.TextButton('下一页',on_click=following)
        body=ft.Column(spacing=12,controls=[
            ft.Row(wrap=True,controls=[previous_button,next_button,
                ft.TextButton('添加空白页',on_click=add_page),ft.FilledButton('进入创作工作台',on_click=enter_studio),ft.TextButton('阅读预览',on_click=toggle_read)]),
            ft.Row(expand=True,spacing=22,vertical_alignment=ft.CrossAxisAlignment.START,controls=[left,
                ft.Container(expand=2,content=preview)]),
            status,text('左右拖动书页或点击上一页 / 下一页翻阅；长页可上下滚动。导出后也能立体翻页。',11,theme.TEXT_SUB)])
        paint_fields();paint_preview()
        replace(dialog('编写旅行手账',body,[ft.TextButton('返回书架',on_click=close_editor),
            ft.OutlinedButton('导出电子版',on_click=export),ft.FilledButton('保存手账',on_click=save)]))

    page.show_dialog(shelf())

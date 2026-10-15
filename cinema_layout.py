"""A personal screening room: poster stage and reusable filmstrip frames."""
import os
import flet as ft
import theme


def thumbnail(movie,width=64,height=90):
    path=movie.get('poster') or ''
    if path and os.path.isfile(path):
        content=ft.Image(src=path,width=width,height=height,fit=ft.BoxFit.COVER)
    else:
        content=ft.Container(width=width,height=height,bgcolor=theme.CARD_BG_SOFT,
            alignment=ft.Alignment.CENTER,content=ft.Text((movie.get('title') or '影')[:1],
                font_family='SimSun',size=30,color=theme.ACCENT))
    return ft.Container(width=width,height=height,border_radius=3,clip_behavior=ft.ClipBehavior.ANTI_ALIAS,content=content)


def film_frame(movie,index,active,callback):
    return ft.Container(width=192,height=116,padding=10,border_radius=8,
        key=ft.ScrollKey(f"movie-{movie['id']}"),data=movie['id'],
        tooltip='查看收藏：'+movie['title'],on_click=callback,
        bgcolor=theme.CARD_BG_SOFT if active else theme.CARD_BG,
        border=ft.Border.all(1.5,theme.ACCENT if active else theme.LINE),
        animate=ft.Animation(200,ft.AnimationCurve.EASE_OUT),
        content=ft.Row(spacing=11,controls=[thumbnail(movie),ft.Column(expand=True,spacing=7,controls=[
            ft.Text(f'{index+1:02d}  /  '+(movie.get('kind') or '电影'),size=10,color=theme.TEXT_SUB),
            ft.Text(movie['title'],size=13,font_family='SimSun',color=theme.TEXT_MAIN,
                max_lines=2,overflow=ft.TextOverflow.ELLIPSIS),
            ft.Text(movie.get('watch_date') or '日期待补',size=9,color=theme.TEXT_SUB),
        ])]))


def screening_room(movie,card,index,total,compact,on_read,on_edit,on_delete):
    """All movie details come from the collection, with no invented credits."""
    stage='#131A1D' if theme.DARK else '#223230'
    paper='#F3EFE4';muted='#B8C5BE';gold='#D1C39E'
    height=244 if compact else 320
    title_size=26 if compact else 36
    path=movie.get('poster') or ''
    background=[]
    if path and os.path.isfile(path):
        background.append(ft.Container(left=0,top=0,right=0,bottom=0,
            image=ft.DecorationImage(src=path,fit=ft.BoxFit.COVER)))
    background.append(ft.Container(left=0,top=0,right=0,bottom=0,
        gradient=ft.LinearGradient(begin=ft.Alignment.CENTER_LEFT,end=ft.Alignment.CENTER_RIGHT,
            colors=[stage,theme.with_alpha(stage,.94),theme.with_alpha(stage,.68)])))
    background.extend([
        ft.Container(left=22,top=18,right=22,bottom=18,border=ft.Border.all(.6,'#30D1C39E'),border_radius=8,ignore_interactions=True),
        ft.Container(right=20,bottom=-135,width=420,height=270,border_radius=200,
            gradient=ft.RadialGradient(colors=['#30D1C39E','#00D1C39E']),ignore_interactions=True),
    ])
    header=ft.Row(spacing=8,controls=[ft.Container(width=5,height=5,bgcolor=gold,border_radius=5),
        ft.Text('私人放映室',size=11,color=gold),ft.Container(expand=True),
        ft.Text(f'藏片  {index+1:03d} / {total:03d}',size=10,font_family='Consolas',color=muted)])
    details=ft.Column(expand=True,alignment=ft.MainAxisAlignment.CENTER,spacing=8 if compact else 14,controls=[
        ft.Text(' / '.join(v for v in [movie.get('kind'),movie.get('genre')] if v),size=11,color=muted),
        ft.Text(movie.get('title') or '未命名作品',size=title_size,font_family='SimSun',color=paper,
            weight=ft.FontWeight.W_600,max_lines=2,overflow=ft.TextOverflow.ELLIPSIS),
        ft.Row(spacing=12,controls=[ft.Text('★ '+str(int(movie.get('rating') or 0))+' / 5',size=13,color=gold),
            ft.Container(width=1,height=12,bgcolor='#506A716B'),
            ft.Text(movie.get('watch_date') or '还没有记录观看日期',size=11,color=muted)]),
        ft.Container(width=34,height=1,bgcolor=gold,visible=not compact),
        ft.Text(movie.get('review') or '故事落幕后，把此刻的感受留在这里。',size=14,color=paper,
            max_lines=1 if compact else 2,overflow=ft.TextOverflow.ELLIPSIS),
        ft.Row(spacing=5,wrap=True,controls=[
            ft.OutlinedButton('沉浸阅读',icon=ft.Icons.MENU_BOOK_OUTLINED,on_click=on_read,
                style=ft.ButtonStyle(color=paper,side=ft.BorderSide(1,'#60D1C39E'))),
            ft.TextButton('翻面看感想',on_click=card.turn,style=ft.ButtonStyle(color=muted)),
            ft.IconButton(ft.Icons.EDIT_OUTLINED,tooltip='编辑收藏',icon_color=muted,on_click=on_edit),
            ft.IconButton(ft.Icons.DELETE_OUTLINE,tooltip='删除当前收藏',icon_color=muted,on_click=on_delete),
        ]),
    ])
    background.append(ft.Container(left=30,top=18 if compact else 24,right=30,bottom=18 if compact else 24,
        content=ft.Column(spacing=8 if compact else 14,controls=[header,ft.Row(expand=True,spacing=42 if not compact else 22,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,controls=[details,
                ft.Container(padding=ft.Padding.only(right=14),content=card)])])))
    return ft.Container(height=height,bgcolor=stage,border_radius=14,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,content=ft.Stack(controls=background))

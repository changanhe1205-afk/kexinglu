"""Code-native keepsake layouts; photographs and posters come from the user."""
import os
import flet as ft
import theme


def stars(value, size=14):
    return ft.Row(spacing=1, tight=True, controls=[ft.Icon(
        ft.Icons.STAR if i < int(value or 0) else ft.Icons.STAR_BORDER,
        size=size, color=theme.SOFT_LEMON if i < int(value or 0) else theme.TEXT_FAINT)
        for i in range(5)])


def movie_front(movie, width, height):
    poster = movie.get("poster") or ""
    small = width < 180
    if poster and os.path.isfile(poster):
        body = ft.Image(src=poster.replace("\\","/"),width=width,height=height,
                        fit=ft.BoxFit.CONTAIN)
    else:
        ink, muted = "#ECF0F5", "#9EAEBD"
        k=width/228
        body = ft.Stack(controls=[
            ft.Container(left=10*k,top=10*k,right=10*k,bottom=10*k,border=ft.Border.all(.7,"#738799")),
            ft.Container(left=width*.175,bottom=height*.14,width=width*.65,height=width*.65,
                border_radius=width,border=ft.Border.all(.8,muted),
                alignment=ft.Alignment.CENTER,content=ft.Container(width=width*.17,height=width*.17,
                    border_radius=width,border=ft.Border.all(.8,muted),alignment=ft.Alignment.CENTER,
                    content=ft.Container(width=4,height=4,border_radius=4,bgcolor=ink))),
            ft.Container(left=24*k,right=24*k,top=28*k,content=ft.Column(spacing=16*k,controls=[
                ft.Text(movie.get("kind") or "电影",size=max(7,10*k),color=muted),
                ft.Text(movie.get("title") or "未命名",size=max(12,26*k),
                    font_family="SimSun",weight=ft.FontWeight.W_600,color=ink,max_lines=2,
                    overflow=ft.TextOverflow.ELLIPSIS),
                ft.Container(width=26*k,height=1,bgcolor=muted),
            ])),
            ft.Container(left=24*k,right=24*k,bottom=20*k,content=ft.Text(
                movie.get("watch_date") or "日期待补",size=max(6,9*k),color=muted)),
        ])
    return ft.Container(width=width,height=height,bgcolor="#1D2A36",border_radius=2,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        border=ft.Border.all(1,theme.LINE),shadow=theme.card_shadow(True),content=body)


def movie_back(movie,width,height):
    small=width<150
    return ft.Container(width=width,height=height,padding=10 if small else 20,bgcolor=theme.CARD_BG,
        border_radius=10,border=ft.Border.all(1,theme.LINE),shadow=theme.card_shadow(True),
        content=ft.Column(spacing=5 if small else 12,controls=[
            ft.Text("观后感",size=10 if small else 12,color=theme.ACCENT),
            ft.Text(movie.get("title") or "未命名",size=12 if small else 18,weight=ft.FontWeight.W_600,
                    color=theme.TEXT_MAIN,max_lines=2,overflow=ft.TextOverflow.ELLIPSIS),
            stars(movie.get("rating"),10 if small else 14),ft.Divider(height=1,color=theme.LINE),
            ft.ListView(expand=True,controls=[ft.Text(movie.get("review") or "还没有写下感想，点击编辑补上一段。",
                                                     size=10 if small else 13,color=theme.TEXT_MAIN)]),
            ft.Text(movie.get("watch_date") or "日期待补",size=8 if small else 10,color=theme.TEXT_SUB),
        ]))


def stamp(saved):
    return ft.Container(rotate=-.08,animate_scale=ft.Animation(180,ft.AnimationCurve.EASE_OUT),
        animate_opacity=ft.Animation(180,ft.AnimationCurve.EASE_OUT),padding=ft.Padding.symmetric(horizontal=10,vertical=5),
        border=ft.Border.all(1.4,theme.ACCENT),border_radius=4,
        content=ft.Text("已收藏" if saved else "待收藏",size=13,color=theme.ACCENT,
                        weight=ft.FontWeight.W_600))


def food_faces(item,width,height,saved):
    front_stamp, back_stamp = stamp(saved), stamp(saved)
    photo_path=item.get("image") or ""
    has_photo=bool(photo_path and os.path.isfile(photo_path))
    photo=ft.Container(expand=True,bgcolor=theme.CARD_BG_SOFT,
        alignment=ft.Alignment.CENTER,clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        content=ft.Image(src=photo_path.replace("\\","/"),fit=ft.BoxFit.COVER,expand=True)
        if has_photo else ft.Column(alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,spacing=12,controls=[
                ft.Icon(ft.Icons.PHOTO_OUTLINED,size=42,color=theme.TEXT_FAINT),
                ft.Text("附一张照片，留住这一餐",size=12,color=theme.TEXT_SUB)]))
    front=ft.Container(data={"stamp":front_stamp},width=width,height=height,padding=14,bgcolor=theme.CARD_BG,
        border_radius=5,border=ft.Border.all(1,theme.LINE),shadow=theme.card_shadow(True),
        content=ft.Column(spacing=12,controls=[photo,
            ft.Text(item.get("name") or "今天吃点什么",size=20,color=theme.TEXT_MAIN,
                    weight=ft.FontWeight.W_600,max_lines=2,overflow=ft.TextOverflow.ELLIPSIS),
            ft.Row(controls=[ft.Text(item.get("eat_date") or "日期待补",size=11,color=theme.TEXT_SUB,expand=True),
                             stars(item.get("rating"),13)]),
            ft.Row(controls=[ft.Text(item.get("place") or "地点待补",size=11,color=theme.TEXT_SUB,
                expand=True,max_lines=1,overflow=ft.TextOverflow.ELLIPSIS),front_stamp]),
        ]))
    def separator():
        return ft.Row(spacing=4,controls=[ft.Container(expand=True,height=1,bgcolor=theme.LINE) for _ in range(22)])
    def info(label,value):
        return ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN,controls=[
            ft.Text(label,size=11,color=theme.TEXT_SUB),
            ft.Text(value,size=12,color=theme.TEXT_MAIN,max_lines=2,expand=True,text_align=ft.TextAlign.RIGHT)])
    receipt=ft.Container(data={"stamp":back_stamp},width=width,height=height,padding=16 if height<380 else 22,bgcolor=theme.CARD_BG,
        border_radius=5,border=ft.Border.all(1,theme.LINE),shadow=theme.card_shadow(True),
        content=ft.Column(spacing=8 if height<380 else 13,controls=[
            ft.Text(item.get("place") or "食光小记",size=18,color=theme.TEXT_MAIN,
                    weight=ft.FontWeight.W_600,max_lines=2,overflow=ft.TextOverflow.ELLIPSIS),
            ft.Text(item.get("eat_date") or "日期待补",size=11,color=theme.TEXT_SUB),separator(),
            ft.Text(item.get("name") or "今天吃点什么",size=21,color=theme.TEXT_MAIN,
                    weight=ft.FontWeight.W_600,max_lines=2,overflow=ft.TextOverflow.ELLIPSIS),
            info("种类",item.get("kind") or "饭菜"),
            info("价格",("¥ "+str(item['price'])) if item.get('price') else "未记录"),
            stars(item.get("rating"),17),separator(),
            ft.ListView(expand=True,controls=[ft.Text(item.get("note") or "记一点味道，也记一点当时的心情。",
                                                     size=13,color=theme.TEXT_MAIN)]),
            ft.Row(alignment=ft.MainAxisAlignment.END,controls=[back_stamp]),
        ]))
    return front,receipt

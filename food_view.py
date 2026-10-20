"""客行录 · 食光小记模块（界面部分）

喝到的饮料、吃到的饭菜，都是值得收藏的"食光"：
    · 手动记录名称、店铺、日期、价格、评分（星星）和感想，附一张照片
    · 中间展示成一张美食照片卡，饮料天青蓝 / 饭菜杏橙暖色

布局：
    ┌─ 白色顶栏：标题 / 保存 ──────────────────────────────────────────┐
    │ 左栏 300        │ 中间：美食照片大卡（评分星星 / 标签 / 感想）  │ 右栏 340       │
    │ 收藏统计         │  没有照片时显示彩色占位                      │ 填写食光信息    │
    │ 收藏列表         │                                             │                │
    └───────────────────────────────────────────────────────────────┘
"""

from __future__ import annotations
from i18n import tr

import os
import shutil
import uuid
from datetime import datetime

import flet as ft
from date_utils import calendar_date, open_calendar

import food_db as fdb
import theme
import collection_cards
from collection_motion import FlipCard
from theme import card_shadow, glass_surface, icon_badge


KINDS = ["饮料", "饭菜"]
KIND_ICONS = {"饮料": ft.Icons.LOCAL_DRINK, "饭菜": ft.Icons.RESTAURANT}


def _pretty_date(date_str: str) -> str:
    raw = (date_str or "").strip()
    try:
        d = datetime.strptime(raw, "%Y-%m-%d")
    except ValueError:
        return raw
    week = "一二三四五六日"[d.weekday()]
    return f"{d.year}年{d.month}月{d.day}日 周{week}"


def _refresh_theme_values() -> None:
    """每次建页重新生成样式，避免模块级字段缓存旧主题。"""
    global FORM_FIELD, KIND_COLORS, KIND_SOFTS
    FORM_FIELD = dict(
        border={
            ft.ControlState.DEFAULT: ft.OutlineInputBorder(
                border_radius=10, side=ft.BorderSide(width=1, color=theme.LINE)),
            ft.ControlState.FOCUSED: ft.OutlineInputBorder(
                border_radius=10, side=ft.BorderSide(width=1.4, color=theme.MIST_BLUE)),
        },
        text_style=ft.TextStyle(size=13, color=theme.TEXT_MAIN),
        label_style=ft.TextStyle(size=11.5, color=theme.TEXT_SUB),
        hint_style=ft.TextStyle(size=12, color=theme.TEXT_FAINT),
        filled=True, fill_color=theme.CARD_BG,
        content_padding=ft.Padding.symmetric(horizontal=12, vertical=9),
    )
    KIND_COLORS = {"饮料": theme.SKY_CYAN, "饭菜": theme.APRICOT}
    KIND_SOFTS = {"饮料": theme.SKY_CYAN_SOFT, "饭菜": theme.APRICOT_SOFT}


_refresh_theme_values()


def build(page: ft.Page) -> ft.Control:
    _refresh_theme_values()
    current: dict = {"id": None}        # 当前选中的收藏
    form_image: dict = {"path": ""}     # 表单关联的照片
    picked_kind: dict = {"v": "饭菜"}
    picked_rating: dict = {"v": 0}
    preview = {"draft": False, "back": False, "card": None}

    def show_tip(msg: str) -> None:
        page.show_dialog(theme.toast(ft.Text(msg, size=12.5, color="#FFFFFF"),
                                     bgcolor=theme.MIST_BLUE_DEEP))

    # ---------------- 图片工具 ----------------
    def _save_image(src: str) -> str:
        if not src or not os.path.exists(src):
            return ""
        ext = os.path.splitext(src)[1].lower() or ".png"
        dest = os.path.join(fdb.FOOD_DIR, f"{uuid.uuid4().hex}{ext}")
        shutil.copyfile(src, dest)
        return dest

    def _remove_image(path: str) -> None:
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass

    # ---------------- 左栏：统计 + 收藏列表 ----------------
    # （顶栏已去掉：保存按钮在右侧「记录食光」卡片里，页面归属看底部导航）
    stats_text = ft.Text("", size=11, color=theme.TEXT_SUB, expand=True, max_lines=2)
    food_list = ft.ListView(spacing=9, expand=True, padding=ft.Padding.only(right=3))

    def stars_view(rating: int, size: float = 12) -> ft.Row:
        return ft.Row(spacing=1, controls=[
            ft.Icon(ft.Icons.STAR if i < rating else ft.Icons.STAR_BORDER,
                    size=size, color=theme.SOFT_LEMON if i < rating else theme.STAR_OFF)
            for i in range(5)
        ])

    def build_food_card(item: dict) -> ft.Control:
        active = item["id"] == current["id"]
        main_c = KIND_COLORS.get(item.get("kind"), theme.APRICOT)
        soft_c = KIND_SOFTS.get(item.get("kind"), theme.APRICOT_SOFT)
        sub_parts = [item.get("place") or "没记地点", item.get("eat_date") or "日期待补"]
        thumb = ft.Container(
            width=44, height=44, border_radius=12,
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS, bgcolor=soft_c,
            border=ft.Border.all(1, theme.LINE),
            content=(ft.Image(src=item["image"].replace("\\", "/"), fit=ft.BoxFit.COVER,
                              width=44, height=44)
                     if item.get("image") and os.path.exists(item["image"])
                     else ft.Icon(KIND_ICONS.get(item.get("kind"), ft.Icons.RESTAURANT),
                                  size=20, color=main_c)),
        )
        return ft.Container(
            padding=ft.Padding.symmetric(horizontal=10, vertical=9),
            border_radius=15,
            bgcolor=soft_c if active else theme.CARD_BG,
            border=ft.Border.all(1.4, main_c if active else theme.LINE),
            shadow=card_shadow() if active else None,
            on_click=lambda e, fid=item["id"]: select_food(fid),
            content=ft.Row(spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[
                thumb,
                ft.Column(spacing=3, expand=True, controls=[
                    ft.Text(item.get("name") or "未命名", size=12.5,
                            weight=ft.FontWeight.W_700, color=theme.TEXT_MAIN,
                            max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                    ft.Row(spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[
                        stars_view(int(item.get("rating") or 0)),
                        ft.Text(" · ".join(sub_parts), size=10, color=theme.TEXT_SUB,
                                max_lines=1, overflow=ft.TextOverflow.ELLIPSIS,
                                expand=True),
                    ]),
                ]),
            ]),
        )

    def refresh_food() -> None:
        items = fdb.list_food()
        st = fdb.stats()
        stats_text.value = (f"收藏 {st['total']} 件 · 饮料 {st['drinks']}"
                            f" · 饭菜 {st['meals']} · {st['places']} 家店")
        if items:
            food_list.controls = [build_food_card(t) for t in items]
        else:
            # 中间那张大卡已经把空状态说清楚了，左栏只留一句提示，不重复铺图标
            food_list.controls = [ft.Container(
                padding=ft.Padding.only(top=12, left=4),
                content=ft.Text("还没有记录，右侧填一条试试", size=11,
                                color=theme.TEXT_FAINT))]
        paint_card()
        page.update()

    def select_food(food_id: int | None) -> None:
        preview["draft"] = False
        preview["back"] = False
        current["id"] = food_id
        item = fdb.get_food(food_id) if food_id else None
        fill_form(item)
        refresh_food()

    # ---------------- 中间：美食照片大卡 ----------------
    card_area = ft.Container(expand=True, alignment=ft.Alignment.CENTER)

    def draft_item():
        return dict(id=current["id"],kind=picked_kind["v"],name=name_input.value,
            place=place_input.value,eat_date=date_input.value,price=price_input.value,
            note=note_input.value,rating=picked_rating["v"],image=form_image["path"])

    def paint_card() -> None:
        item = draft_item() if preview["draft"] else (fdb.get_food(current["id"]) if current["id"] else None)
        if item is None:
            items=fdb.list_food()
            item=items[0] if items else draft_item()
        saved=bool(item.get("id")) and not preview["draft"]
        width=min(390,max(250,(page.width or 1320)-240-320-110))
        height=min(450,max(310,(page.height or 900)-380))
        front,back=collection_cards.food_faces(item,width,height,saved)
        face_label=ft.Text("小票" if preview["back"] else "照片",size=12,color=theme.TEXT_MAIN)
        def changed(face):
            preview["back"]=face
            face_label.value="小票" if face else "照片"
            page.update()
        card=FlipCard(front,back,width,height,face=preview["back"],on_face=changed)
        preview["card"]=card
        card_area.content=ft.Column(spacing=12,tight=True,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,controls=[
                ft.Row(spacing=10,tight=True,controls=[face_label,
                    ft.TextButton("翻看照片 / 小票",icon=ft.Icons.FLIP,on_click=card.turn)]),
                card,
                ft.Text("编辑中 · 保存后收录" if preview["draft"] else "点击卡片，翻看另一面",
                        size=11,color=theme.TEXT_SUB),
            ])

    def draft_changed(e=None):
        preview["draft"]=True
        paint_card()
        page.update()

    # ---------------- 右栏：填写表单 ----------------
    def kind_button(name: str) -> ft.FilledButton:
        return ft.FilledButton(
            content=name, data=name, height=32, elevation=0,
            on_click=lambda e: (picked_kind.update({"v": e.control.data}), paint_kind(), draft_changed()),
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=9),
                                 padding=ft.Padding.symmetric(horizontal=13)),
        )

    kind_buttons = {name: kind_button(name) for name in KINDS}
    kind_row = ft.Row(spacing=7, controls=list(kind_buttons.values()))

    def paint_kind() -> None:
        for name, btn in kind_buttons.items():
            active = name == picked_kind["v"]
            btn.bgcolor = KIND_COLORS[name] if active else theme.CARD_BG
            btn.color = theme.ON_ACCENT if active else theme.TEXT_SUB

    name_input = ft.TextField(**FORM_FIELD, label="名称", hint_text="如 生椰拿铁 / 阿婆的红烧肉")
    place_input = ft.TextField(**FORM_FIELD, label="店铺 / 地点", hint_text="在哪里吃到")
    date_input = ft.TextField(**FORM_FIELD, label=tr("日期"), hint_text="点击右侧日历选择",
                              read_only=True)
    price_input = ft.TextField(**FORM_FIELD, label="价格", hint_text="如 18 / 人均 60")
    note_input = ft.TextField(**FORM_FIELD, label="感想", hint_text="味道怎么样、和谁一起…",
                              multiline=True, min_lines=2, max_lines=4, height=84)

    date_picker = ft.DatePicker(on_change=lambda e: (
        setattr(date_input, "value",
                calendar_date(e.control.value)),
        draft_changed()))
    photo_pick = ft.FilePicker()
    page.services.append(photo_pick)

    # 评分星星
    star_buttons: list[ft.IconButton] = []

    def set_rating(e) -> None:
        picked_rating["v"] = int(e.control.data)
        paint_rating()
        draft_changed()

    def paint_rating() -> None:
        for i, btn in enumerate(star_buttons):
            btn.icon = ft.Icons.STAR if i < picked_rating["v"] else ft.Icons.STAR_BORDER
            btn.icon_color = theme.SOFT_LEMON if i < picked_rating["v"] else theme.STAR_OFF

    for i in range(5):
        star_buttons.append(ft.IconButton(
            ft.Icons.STAR_BORDER, icon_size=20, width=26, height=32, padding=0,
            tooltip=f"{i + 1} 星", data=i + 1, on_click=set_rating))
    rating_row = ft.Row(spacing=2, controls=star_buttons)

    photo_status = ft.Text("", size=10.5, color=theme.TEXT_FAINT, expand=True)

    async def choose_photo(e=None) -> None:
        files = await photo_pick.pick_files(
            dialog_title="选择一张照片", file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=["png", "jpg", "jpeg", "webp", "bmp"],
            allow_multiple=False)
        if not files:
            return
        form_image["path"] = _save_image(files[0].path)
        photo_status.value = "已附上照片"
        draft_changed()

    def fill_form(item: dict | None) -> None:
        picked_kind["v"] = (item or {}).get("kind") or "饭菜"
        paint_kind()
        picked_rating["v"] = int((item or {}).get("rating") or 0)
        paint_rating()
        name_input.value = (item or {}).get("name") or ""
        place_input.value = (item or {}).get("place") or ""
        date_input.value = (item or {}).get("eat_date") or datetime.now().strftime("%Y-%m-%d")
        price_input.value = (item or {}).get("price") or ""
        note_input.value = (item or {}).get("note") or ""
        form_image["path"] = (item or {}).get("image") or ""
        photo_status.value = "已附上照片" if form_image["path"] else ""
        page.update()

    def clear_form() -> None:
        current["id"] = None
        form_image["path"] = ""
        fill_form(None)
        preview.update(draft=True, back=False)
        paint_card()
        page.update()

    def save_food(e=None) -> None:
        name = (name_input.value or "").strip()
        if not name:
            show_tip("先给它起个名字吧")
            return
        fields = dict(
            kind=picked_kind["v"], name=name,
            place=(place_input.value or "").strip(),
            eat_date=(date_input.value or "").strip(),
            price=(price_input.value or "").strip(),
            rating=picked_rating["v"],
            note=(note_input.value or "").strip(),
            image=form_image["path"],
        )
        if current["id"]:
            old = fdb.get_food(current["id"]) or {}
            if old.get("image") and old["image"] != fields["image"]:
                _remove_image(old["image"])
            fdb.update_food(current["id"], **fields)
            show_tip("收藏已更新")
        else:
            current["id"] = fdb.add_food(**fields)
            show_tip("已收藏进食光小记")
        preview["draft"] = False
        refresh_food()
        if preview["card"]:
            saved_card = preview["card"]
            async def settle():
                await saved_card.celebrate(paper=True)
            page.run_task(settle)

    def remove_food(e=None) -> None:
        if not current["id"]:
            show_tip("先在左侧选中一条要删除的收藏")
            return
        row = fdb.delete_food(current["id"])
        if row:
            _remove_image(row.get("image") or "")
        show_tip("收藏已删除")
        clear_form()
        refresh_food()

    for field in (name_input, place_input, date_input, price_input, note_input):
        field.on_change = draft_changed

    form_card = ft.Container(
        padding=16, border_radius=18, bgcolor=theme.CARD_BG,
        border=ft.Border.all(1, theme.LINE), shadow=card_shadow(),
        content=ft.Column(spacing=10, controls=[
            ft.Row(spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[
                icon_badge(ft.Icons.EDIT_OUTLINED, 30, theme.APRICOT_SOFT, theme.MIST_BLUE_DEEP, 16),
                ft.Text("记录食光", size=14, weight=ft.FontWeight.W_700, color=theme.TEXT_MAIN,
                        expand=True),
                ft.TextButton("再记一份", icon=ft.Icons.ADD, height=30,
                              on_click=lambda e: clear_form()),
            ]),
            kind_row,
            name_input,
            place_input,
            ft.Row(spacing=8, controls=[
                ft.Container(expand=True, content=date_input),
                ft.IconButton(ft.Icons.EVENT, icon_size=17, icon_color=theme.MIST_BLUE_DEEP,
                              tooltip="选择日期", width=34, height=34, padding=0,
                              on_click=lambda e: open_calendar(page, date_picker, date_input.value)),
            ]),
            ft.Row(spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[
                ft.Text("评分", size=12, color=theme.TEXT_SUB),
                rating_row,
                ft.Container(width=78, content=price_input),
            ]),
            note_input,
            ft.Row(spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[
                ft.TextButton("附一张照片", icon=ft.Icons.IMAGE_OUTLINED, height=32,
                              on_click=choose_photo),
                photo_status,
            ]),
            ft.Row(spacing=8, controls=[
                ft.FilledButton(
                    "保存收藏", icon=ft.Icons.SAVE_OUTLINED, expand=True,
                    bgcolor=theme.ACCENT, color=theme.ON_ACCENT, height=38, elevation=0,
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=11)),
                    on_click=lambda e: save_food()),
                ft.TextButton(tr("删除"), icon=ft.Icons.DELETE_OUTLINE, height=38,
                              style=ft.ButtonStyle(color=theme.DANGER),
                              on_click=remove_food),
            ]),
        ]),
    )

    left_panel = ft.Container(
        width=240,
        padding=ft.Padding.symmetric(horizontal=14, vertical=16),
        content=ft.Column(spacing=11, controls=[
            ft.Container(
                padding=ft.Padding.symmetric(horizontal=13, vertical=11),
                border_radius=14, gradient=ft.LinearGradient(
                    begin=ft.Alignment.TOP_LEFT, end=ft.Alignment.BOTTOM_RIGHT,
                    colors=[theme.APRICOT_SOFT, theme.SKY_CYAN_SOFT]),
                content=ft.Row(spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[
                    ft.Icon(ft.Icons.FREE_BREAKFAST, size=18, color=theme.MIST_BLUE_DEEP),
                    stats_text,
                ]),
            ),
            food_list,
        ]),
    )

    center_area = ft.Container(
        expand=True,
        padding=ft.Padding.symmetric(horizontal=12, vertical=12),
        alignment=ft.Alignment.CENTER,
        content=card_area,
    )

    right_panel = ft.Container(
        width=320,
        bgcolor=theme.CARD_BG_SOFT,
        border=ft.Border.only(left=ft.BorderSide(1, theme.LINE)),
        content=ft.ListView(spacing=12, padding=ft.Padding.all(14),
                            controls=[form_card]),
    )

    # 初始化
    paint_kind()
    paint_rating()
    fill_form(None)
    refresh_food()

    return ft.Row(spacing=0, expand=True,
                  data={"on_resize": paint_card},
                  controls=[left_panel, center_area, right_panel])

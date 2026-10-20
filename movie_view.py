"""客行录 · 影视收藏模块（界面部分）

这个文件只包含"影视收藏"这一页的界面逻辑，对外提供一个 build(page) 函数，
由 main.py 负责挂载。原本所有代码都在 main.py 里，新增聊天模块后拆出来，
方便两个模块各自独立维护。
"""

from __future__ import annotations
from i18n import tr

import os
import asyncio
import shutil
import uuid
import time
from datetime import datetime

import flet as ft
from date_utils import calendar_date, open_calendar

import database as db
import theme
import collection_cards
import cinema_layout
from collection_motion import CinemaCard, motion_enabled
from theme import badge, glass_surface, icon_badge

# ---------------- 常量 ----------------
KINDS = ["电影", "剧集"]            # 类别
FILTERS = ["全部"] + KINDS          # 顶部筛选选项
AUTO_ROLL_SECONDS = 6
IMG_EXTS = ["jpg", "jpeg", "png", "webp", "bmp"]   # 允许选择的海报格式

# 卡片采用「固定宽度 + 横幅封面」：一屏能看到更多藏品。
CARD_WIDTH = 240                        # 卡片宽度
COVER_HEIGHT = int(CARD_WIDTH * 3 / 4)  # 封面高度 = 180

# 输入框统一样式（聚焦时边框变成雾霭蓝）


# ---------------- 通用组件 ----------------
def stars_row(rating: int, size: int = 15) -> ft.Row:
    """只读星级：卡片上展示用，点亮的星用柔柠黄。"""
    return ft.Row(
        spacing=0,
        controls=[
            ft.Icon(
                ft.Icons.STAR if i <= rating else ft.Icons.STAR_BORDER,
                size=size,
                color=theme.SOFT_LEMON if i <= rating else theme.STAR_OFF,
            )
            for i in range(1, 6)
        ],
    )


def cover_view(poster: str, title: str) -> ft.Control:
    """封面区：横幅式封面，有海报就居中裁切铺满，没有则渐变 + 首字占位。"""
    if poster and os.path.exists(poster):
        return ft.Image(
            src=poster.replace("\\", "/"),
            fit=ft.BoxFit.COVER,
            width=CARD_WIDTH,
            height=COVER_HEIGHT,
        )

    first = (title or "影").strip()[:1] or "影"
    return ft.Container(
        height=COVER_HEIGHT,
        gradient=ft.LinearGradient(
            begin=ft.Alignment.TOP_LEFT,
            end=ft.Alignment.BOTTOM_RIGHT,
            colors=[theme.MIST_BLUE_SOFT, theme.MIST_BLUE],
        ),
        content=ft.Row(
            alignment=ft.MainAxisAlignment.CENTER,
            controls=[ft.Text(first, size=46, color="#FFFFFF", weight=ft.FontWeight.BOLD)],
        ),
    )


def build_card(movie: dict, on_edit, on_delete) -> ft.Container:
    """单张藏品卡片：封面 + 片名 + 标签 + 星级 + 感想摘要 + 操作区。"""
    review_text = (movie.get("review") or "").strip()
    review_view = ft.Text(
        review_text or "还没有感想，点右下角补一句吧～",
        size=12,
        color=theme.TEXT_SUB if review_text else theme.STAR_OFF,
        max_lines=2,
        overflow=ft.TextOverflow.ELLIPSIS,
    )

    genre = (movie.get("genre") or "").strip()
    tags = ft.Row(
        spacing=6,
        controls=[badge(movie.get("kind") or "电影", theme.MIST_BLUE)]
        + ([badge(genre, theme.SOFT_LEMON, theme.TEXT_MAIN)] if genre else []),
    )

    return ft.Container(
        width=CARD_WIDTH,                # 卡片宽度固定，保证海报比例一致
        bgcolor=theme.CARD_BG,
        border_radius=theme.RADIUS,
        border=ft.Border.all(1, theme.LINE),
        shadow=ft.BoxShadow(blur_radius=18, spread_radius=-3, color=theme.SHADOW, offset=ft.Offset(0, 6)),
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,              # 让封面的圆角生效
        content=ft.Column(
            spacing=0,
            controls=[
                cover_view(movie.get("poster") or "", movie["title"]),
                ft.Container(
                    padding=ft.Padding.all(14),
                    content=ft.Column(
                        spacing=8,
                        controls=[
                            ft.Text(
                                movie["title"], size=16, weight=ft.FontWeight.W_600,
                                color=theme.TEXT_MAIN, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                            tags,
                            stars_row(int(movie.get("rating") or 0)),
                            review_view,
                            ft.Divider(height=1, color=theme.LINE),
                            ft.Row(
                                spacing=0,
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                controls=[
                                    ft.Text(
                                        movie.get("watch_date") or "未记录日期",
                                        size=11, color=theme.TEXT_SUB, expand=True,
                                    ),
                                    ft.IconButton(
                                        ft.Icons.EDIT_OUTLINED, icon_size=18,
                                        icon_color=theme.MIST_BLUE_DEEP, tooltip=tr("编辑"),
                                        width=34, height=34, padding=0,
                                        data=movie["id"], on_click=lambda e: on_edit(e.control.data),
                                    ),
                                    ft.IconButton(
                                        ft.Icons.DELETE_OUTLINE, icon_size=18,
                                        icon_color="#D98C8C", tooltip=tr("删除"),
                                        width=34, height=34, padding=0,
                                        data=movie["id"], on_click=lambda e: on_delete(e.control.data),
                                    ),
                                ],
                            ),
                        ],
                    ),
                ),
            ],
        ),
    )


def remove_poster_file(path: str) -> None:
    """删除海报文件时做保护：只清理本应用海报目录内的文件。"""
    try:
        if path and path.startswith(db.POSTER_DIR) and os.path.exists(path):
            os.remove(path)
    except OSError:
        pass


def save_poster_file(src: str) -> str:
    """把用户选中的图片复制进海报目录，避免原图被移动后卡片空白。"""
    os.makedirs(db.POSTER_DIR, exist_ok=True)
    ext = os.path.splitext(src)[1].lower() or ".jpg"
    dst = os.path.join(db.POSTER_DIR, f"{uuid.uuid4().hex}{ext}")
    shutil.copyfile(src, dst)
    return dst


# ---------------- 影视收藏页 ----------------
def _refresh_theme_values() -> None:
    """每次建页重新生成样式，避免模块级字段缓存旧主题。"""
    global FIELD_STYLE
    FIELD_STYLE = dict(
        border={
            ft.ControlState.DEFAULT: ft.OutlineInputBorder(
                border_radius=12, side=ft.BorderSide(width=1, color=theme.LINE),
            ),
            ft.ControlState.FOCUSED: ft.OutlineInputBorder(
                border_radius=12, side=ft.BorderSide(width=1.5, color=theme.MIST_BLUE),
            ),
        },
        bgcolor=theme.CARD_BG,
        filled=True,
        text_size=13,
        color=theme.TEXT_MAIN,
        content_padding=ft.Padding.symmetric(horizontal=12, vertical=8),
    )


_refresh_theme_values()


def build(page: ft.Page) -> ft.Control:
    """构建影视收藏整页内容，返回一个可以直接放进页面的控件。"""
    _refresh_theme_values()
    db.init_db()     # 首次运行自动建库建表

    # --- 界面状态 ---
    filter_kind = {"v": "全部"}
    editing_id = {"v": None}
    focus = {"id": None, "items": [], "card": None, "revision": 0}
    rolling = {"active":False,"task":None,"hover":False,"search":False,"deadline":0,"busy":False}
    def postpone():rolling['deadline']=time.monotonic()+AUTO_ROLL_SECONDS
    def hover_feature(e):
        rolling['hover']=str(e.data).lower()=='true';postpone()
    featured = ft.Container(visible=False,opacity=1,offset=ft.Offset(0,0),
        on_hover=hover_feature,
        animate_opacity=ft.Animation(180,ft.AnimationCurve.EASE_OUT),
        animate_offset=ft.Animation(240,ft.AnimationCurve.EASE_OUT))
    picked_kind = {"v": "电影"}
    picked_rating = {"v": 5}
    picked_poster = {"v": None}          # 表单里当前选中的海报路径
    original_poster = {"v": None}        # 打开表单时的旧海报，用于替换后清理

    # --- 顶部统计数字 ---
    stat_total = ft.Text("0", size=17, weight=ft.FontWeight.BOLD, color=theme.MIST_BLUE_DEEP)
    stat_movie = ft.Text("0", size=17, weight=ft.FontWeight.BOLD, color=theme.MIST_BLUE_DEEP)
    stat_tv = ft.Text("0", size=17, weight=ft.FontWeight.BOLD, color=theme.MIST_BLUE_DEEP)

    # --- 搜索框 ---
    def on_search(e) -> None:
        postpone()
        refresh()

    def search_focus(e):rolling['search']=True;postpone()
    def search_blur(e):rolling['search']=False;postpone()

    search_input = ft.TextField(
        **FIELD_STYLE,
        hint_text="搜索片名 / 题材 / 感想…",
        height=42,
        expand=True,
        prefix_icon=ft.Icons.SEARCH,
        on_change=on_search,
        on_focus=search_focus,on_blur=search_blur,
    )

    # --- 类别筛选按钮 ---
    filter_buttons = {
        name: ft.FilledButton(
            content=name, data=name, height=42, elevation=0,
            on_click=lambda e: on_filter(e.control.data),
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=12),
                padding=ft.Padding.symmetric(horizontal=18),
            ),
        )
        for name in FILTERS
    }

    def paint_filters() -> None:
        """当前选中的筛选项用雾霭蓝实心，其余保持浅色。"""
        for name, btn in filter_buttons.items():
            active = name == filter_kind["v"]
            btn.bgcolor = theme.ACCENT if active else theme.CARD_BG
            btn.color = theme.ON_ACCENT if active else theme.TEXT_SUB

    def on_filter(name: str) -> None:
        postpone()
        filter_kind["v"] = name
        paint_filters()
        refresh()

    # --- 卡片墙与空状态 ---
    grid = ft.ListView(horizontal=True, spacing=10, height=116, build_controls_on_demand=False)

    empty_view = ft.Container(
        visible=False,
        padding=ft.Padding.symmetric(vertical=48),
        alignment=ft.Alignment.CENTER,
        content=ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=8,
            controls=[
                ft.Icon(ft.Icons.MOVIE, size=56, color=theme.MIST_BLUE),
                ft.Text("收藏柜还空着", size=16, weight=ft.FontWeight.W_600, color=theme.TEXT_MAIN),
                ft.Text("点右上角「添加影视」记录第一部作品吧", size=12, color=theme.TEXT_SUB),
            ],
        ),
    )

    # --- 表单输入项（新增 / 编辑共用同一批控件） ---
    title_input = ft.TextField(**FIELD_STYLE, label="片名", hint_text="请输入影视名称")
    genre_input = ft.TextField(**FIELD_STYLE, label="类型题材", hint_text="如：悬疑 / 科幻 / 爱情")
    date_input = ft.TextField(
        **FIELD_STYLE, label="观看日期", hint_text="YYYY-MM-DD", expand=True,
        value=datetime.now().strftime("%Y-%m-%d"),
    )
    review_input = ft.TextField(
        **FIELD_STYLE, label="个人感想", hint_text="写下此刻的感受…",
        multiline=True, min_lines=3, max_lines=5,
    )
    poster_input = ft.TextField(
        **FIELD_STYLE, label="海报（可选）", value="未选择图片",
        read_only=True, hint_text="支持 jpg / png / webp",
    )

    # 类别切换（电影 / 剧集）
    kind_row = ft.Row(spacing=8)
    kind_buttons = {
        name: ft.FilledButton(
            content=name, data=name, height=36, elevation=0,
            on_click=lambda e: on_kind(e.control.data),
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=10),
                padding=ft.Padding.symmetric(horizontal=16),
            ),
        )
        for name in KINDS
    }
    kind_row.controls = list(kind_buttons.values())

    def paint_kind() -> None:
        for name, btn in kind_buttons.items():
            active = name == picked_kind["v"]
            btn.bgcolor = theme.ACCENT if active else "#FFFFFF"
            btn.color = theme.ON_ACCENT if active else theme.TEXT_SUB

    def on_kind(name: str) -> None:
        picked_kind["v"] = name
        paint_kind()
        page.update()

    # 评分：5 颗可点击的星星
    rating_row = ft.Row(spacing=0)

    def paint_rating() -> None:
        rating_row.controls = [
            ft.IconButton(
                icon=ft.Icons.STAR if i <= picked_rating["v"] else ft.Icons.STAR_BORDER,
                icon_color=theme.SOFT_LEMON if i <= picked_rating["v"] else theme.STAR_OFF,
                icon_size=26, tooltip=f"{i} 星", data=i,
                width=36, height=36, padding=0,
                on_click=lambda e: on_rating(e.control.data),
            )
            for i in range(1, 6)
        ]

    def on_rating(value: int) -> None:
        picked_rating["v"] = value
        paint_rating()
        page.update()

    # 日期选择器
    def on_date_picked(e) -> None:
        value = e.control.value
        if value:
            date_input.value = calendar_date(value)
            page.update()

    date_picker = ft.DatePicker(
        first_date=datetime(1990, 1, 1),
        last_date=datetime(2035, 12, 31),
        on_change=on_date_picked,
    )

    def set_today() -> None:
        date_input.value = datetime.now().strftime("%Y-%m-%d")
        page.update()

    # 海报文件选择器
    def apply_poster(path: str) -> None:
        saved = save_poster_file(path)      # 复制到应用海报目录，防止原图被移动后失效
        picked_poster["v"] = saved
        poster_input.value = os.path.basename(saved)
        page.update()

    async def choose_poster(e) -> None:
        """打开系统文件选择框；pick_files 是异步方法，所以这里用 async 处理。"""
        files = await file_picker.pick_files(
            dialog_title="选择一张海报",
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=IMG_EXTS,
            allow_multiple=False,
        )
        if files:
            apply_poster(files[0].path)

    def clear_poster(e) -> None:
        picked_poster["v"] = None
        poster_input.value = "未选择图片"
        page.update()

    file_picker = ft.FilePicker()
    page.services.append(file_picker)

    # --- 弹窗 ---
    current_dialog: dict = {"v": None}

    def close_current() -> None:
        """关闭当前弹窗（flet 会关闭栈顶的那个）。"""
        page.pop_dialog()
        current_dialog["v"] = None

    def show_tip(text: str) -> None:
        """底部轻提示。"""
        page.show_dialog(
            theme.toast(ft.Text(text, color="#FFFFFF"), bgcolor=theme.MIST_BLUE_DEEP)
        )

    def build_form_dialog(title_text: str, on_save) -> ft.AlertDialog:
        """组装表单弹窗。每次打开都新建一个实例，避免重复打开同一个弹窗报错。"""
        return ft.AlertDialog(
            modal=True,
            title=ft.Text(title_text, size=18, weight=ft.FontWeight.BOLD, color=theme.TEXT_MAIN),
            bgcolor=theme.CARD_BG,
            shape=ft.RoundedRectangleBorder(radius=20),
            content=ft.Container(
                width=440,
                content=ft.Column(
                    spacing=14,
                    scroll=ft.ScrollMode.ADAPTIVE,
                    height=430,
                    controls=[
                        title_input,
                        ft.Row(
                            spacing=10,
                            controls=[
                                ft.Column(spacing=4, expand=True, controls=[
                                    ft.Text("类别", size=12, color=theme.TEXT_SUB), kind_row,
                                ]),
                                ft.Column(spacing=4, expand=True, controls=[
                                    ft.Text("评分", size=12, color=theme.TEXT_SUB), rating_row,
                                ]),
                            ],
                        ),
                        genre_input,
                        ft.Row(
                            spacing=8,
                            controls=[
                                date_input,      # 放进 Row，靠 expand 撑满剩余宽度
                                ft.IconButton(
                                    ft.Icons.CALENDAR_MONTH, icon_color=theme.MIST_BLUE_DEEP,
                                    tooltip="选择日期", on_click=lambda e: open_calendar(page, date_picker, date_input.value),
                                ),
                                ft.IconButton(
                                    ft.Icons.TODAY, icon_color=theme.MIST_BLUE_DEEP,
                                    tooltip="设为今天", on_click=lambda e: set_today(),
                                ),
                            ],
                        ),
                        review_input,
                        poster_input,
                        ft.Row(
                            spacing=8,
                            controls=[
                                ft.TextButton("选择海报", icon=ft.Icons.IMAGE, on_click=choose_poster),
                                ft.TextButton("清除海报", icon=ft.Icons.CLOSE, on_click=clear_poster),
                            ],
                        ),
                    ],
                ),
            ),
            actions=[
                ft.TextButton(tr("取消"), on_click=lambda e: close_current()),
                ft.FilledButton(
                    tr("保存"), icon=ft.Icons.CHECK,
                    bgcolor=theme.ACCENT, color=theme.ON_ACCENT, elevation=0,
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
                    on_click=lambda e: on_save(),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

    def open_form(movie_id=None) -> None:
        """打开表单：传 id 表示编辑，不传表示新增。"""
        editing_id["v"] = movie_id
        if movie_id:
            movie = db.get_movie(movie_id) or {}
            dialog_title = "编辑收藏"
            title_input.value = movie.get("title", "")
            genre_input.value = movie.get("genre", "")
            date_input.value = movie.get("watch_date") or ""
            review_input.value = movie.get("review", "")
            picked_kind["v"] = movie.get("kind") or "电影"
            picked_rating["v"] = int(movie.get("rating") or 0)
            picked_poster["v"] = movie.get("poster")
            original_poster["v"] = movie.get("poster")
            poster_input.value = os.path.basename(movie["poster"]) if movie.get("poster") else "未选择图片"
        else:
            dialog_title = "添加收藏"
            title_input.value = ""
            genre_input.value = ""
            date_input.value = datetime.now().strftime("%Y-%m-%d")
            review_input.value = ""
            picked_kind["v"] = "电影"
            picked_rating["v"] = 5
            picked_poster["v"] = None
            original_poster["v"] = None
            poster_input.value = "未选择图片"

        paint_kind()
        paint_rating()
        current_dialog["v"] = build_form_dialog(dialog_title, save_form)
        page.show_dialog(current_dialog["v"])
        page.update()

    def save_form() -> None:
        """保存表单：校验 → 入库 → 刷新列表。"""
        title = (title_input.value or "").strip()
        if not title:
            show_tip("请先填写片名～")
            return

        date_text = (date_input.value or "").strip()
        if date_text:
            try:
                datetime.strptime(date_text, "%Y-%m-%d")
            except ValueError:
                show_tip("日期格式应为 YYYY-MM-DD")
                return

        data = {
            "title": title,
            "kind": picked_kind["v"],
            "genre": (genre_input.value or "").strip(),
            "watch_date": date_text,
            "rating": int(picked_rating["v"]),
            "review": (review_input.value or "").strip(),
            "poster": picked_poster["v"],
        }

        if editing_id["v"]:
            if original_poster["v"] and original_poster["v"] != data["poster"]:
                remove_poster_file(original_poster["v"])   # 换了新海报就清掉旧图
            db.update_movie(editing_id["v"], data)
            tip = "已更新收藏 ✨"
        else:
            editing_id["v"] = db.add_movie(data)
            tip = "已加入收藏 ✨"

        focus["id"] = editing_id["v"]
        search_input.value = ""
        filter_kind["v"] = "全部"
        paint_filters()
        close_current()
        refresh()
        if focus["card"]:
            page.run_task(focus["card"].celebrate)
        show_tip(tip)

    # --- 删除确认 ---
    pending_delete = {"id": None}

    def confirm_delete(movie_id: int) -> None:
        movie = db.get_movie(movie_id) or {}
        pending_delete["id"] = movie_id
        hint = ft.Text(
            f"确定把《{movie.get('title', '')}》从收藏柜里移除吗？此操作不可撤销。",
            size=13, color=theme.TEXT_MAIN,
        )
        current_dialog["v"] = ft.AlertDialog(
            modal=True,
            title=ft.Text("删除收藏", size=18, weight=ft.FontWeight.BOLD, color=theme.TEXT_MAIN),
            bgcolor=theme.CARD_BG,
            shape=ft.RoundedRectangleBorder(radius=20),
            content=ft.Container(width=360, content=hint),
            actions=[
                ft.TextButton("再想想", on_click=lambda e: close_current()),
                ft.FilledButton(
                    tr("删除"), icon=ft.Icons.DELETE_OUTLINE,
                    bgcolor="#D98C8C", color="#FFFFFF", elevation=0,
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
                    on_click=do_delete,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.show_dialog(current_dialog["v"])

    def do_delete(e) -> None:
        removed = db.delete_movie(pending_delete["id"])
        if removed:
            remove_poster_file(removed.get("poster"))
        close_current()
        refresh()
        show_tip("已移出收藏")

    async def select_movie(movie_id, direction=1):
        postpone()
        focus["revision"] += 1
        if focus["id"] == movie_id:
            featured.opacity=1
            featured.offset=ft.Offset(0,0)
            page.update()
            return
        revision=focus["revision"]
        animate=motion_enabled()
        if animate:
            featured.opacity=0
            featured.offset=ft.Offset(-.12*direction,0)
            page.update()
            await asyncio.sleep(.15)
            if revision != focus["revision"]: return
        focus["id"] = movie_id
        refresh(reload=False)
        revision=focus["revision"]
        if animate:
            featured.opacity=0
            featured.offset=ft.Offset(.12*direction,0)
            page.update()
            await asyncio.sleep(.03)
            if revision != focus["revision"]: return
            featured.opacity=1
            featured.offset=ft.Offset(0,0)
            page.update()
            if focus["card"]: page.run_task(focus["card"].celebrate)
        if rolling['active']:
            index=next((i for i,m in enumerate(focus['items']) if m['id']==movie_id),0)
            await grid.scroll_to(offset=index*202,duration=320 if animate else 0)

    async def auto_roll():
        while rolling['active']:
            await asyncio.sleep(.2)
            card=focus['card']
            blocked=(rolling['hover'] or rolling['search'] or len(focus['items'])<2
                or not motion_enabled() or page.window.minimized
                or any(isinstance(d,ft.AlertDialog) and d.open for d in page._dialogs.controls)
                or (card and (card.busy or card.back_visible)))
            if blocked:postpone();continue
            if time.monotonic()<rolling['deadline']:continue
            rolling['busy']=True
            try:await step_movie(1)
            finally:rolling['busy']=False;postpone()

    def show_page():
        if rolling['active']:return
        rolling['active']=True;postpone()
        rolling['task']=page.run_task(auto_roll)

    def leave_page():
        focus["revision"] += 1
        rolling['active']=False
        if rolling['task']:rolling['task'].cancel();rolling['task']=None

    async def pick_archive(e):
        items=focus["items"]
        old=next((i for i,m in enumerate(items) if m['id']==focus['id']),0)
        new=next((i for i,m in enumerate(items) if m['id']==e.control.data),0)
        await select_movie(e.control.data,1 if new>=old else -1)

    async def step_movie(delta):
        items=focus["items"]
        if not items: return
        index=next((i for i,m in enumerate(items) if m["id"]==focus["id"]),0)
        await select_movie(items[(index+delta)%len(items)]["id"],delta)

    async def previous_movie(e): await step_movie(-1)
    async def next_movie(e): await step_movie(1)

    def read_review(movie):
        page.show_dialog(ft.AlertDialog(
            bgcolor=theme.CARD_BG,shape=ft.RoundedRectangleBorder(radius=16),
            title=ft.Text(movie['title'],font_family="SimSun",size=28,color=theme.TEXT_MAIN),
            content=ft.Container(width=600,height=max(220,min(460,(page.height or 900)-320)),
                content=ft.ListView(spacing=24,controls=[
                    ft.Text(" / ".join(x for x in (movie.get('kind'),movie.get('watch_date')) if x),
                            size=12,color=theme.TEXT_SUB),
                    collection_cards.stars(movie.get('rating'),17),
                    ft.Divider(height=1,color=theme.LINE),
                    ft.Text(movie.get('review') or "还没有写下感想。",size=17,color=theme.TEXT_MAIN),
                ])),
            actions=[ft.TextButton("返回影库",on_click=lambda e: page.pop_dialog())]))

    def paint_feature(movie):
        compact=(page.height or 900)<850
        width=108 if compact else 146
        height=width*1.5
        card=CinemaCard(collection_cards.movie_front(movie,width,height),
                      collection_cards.movie_back(movie,width,height),width,height)
        focus["card"]=card
        index=next((i for i,m in enumerate(focus["items"]) if m["id"]==movie["id"]),0)
        featured.visible=True
        def perforations():
            return ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN,controls=[
                ft.Container(width=8,height=4,border_radius=1,bgcolor=theme.LINE) for _ in range(30)])
        featured.content=ft.Column(spacing=14,controls=[
            cinema_layout.screening_room(movie,card,index,len(focus['items']),compact,
                lambda e:read_review(movie),lambda e:open_form(movie['id']),lambda e:confirm_delete(movie['id'])),
            ft.Row(controls=[ft.Text('我的藏片',size=14,font_family='SimSun',color=theme.TEXT_MAIN),
                ft.Text('每一帧，都有当时的自己',size=10,color=theme.TEXT_SUB),ft.Container(expand=True),
                ft.IconButton(ft.Icons.CHEVRON_LEFT,tooltip='上一部',icon_color=theme.TEXT_SUB,on_click=previous_movie),
                ft.Text(f"{index+1:02d} / {len(focus['items']):02d}",size=12,color=theme.TEXT_SUB),
                ft.IconButton(ft.Icons.CHEVRON_RIGHT,tooltip='下一部',icon_color=theme.TEXT_SUB,on_click=next_movie)]),
            ft.Container(padding=10,bgcolor=theme.CARD_BG_SOFT,border_radius=9,
                content=ft.Column(spacing=7,controls=[perforations(),grid,perforations()])),
        ])

    # --- 列表刷新 ---
    def refresh(reload=True) -> None:
        focus["revision"] += 1
        featured.opacity=1
        featured.offset=ft.Offset(0,0)
        movies = db.list_movies((search_input.value or "").strip(), filter_kind["v"]) if reload else focus['items']
        focus["items"] = movies
        if movies:
            selected=next((m for m in movies if m['id']==focus['id']),movies[0])
            focus['id']=selected['id']
            paint_feature(selected)
        else:
            featured.visible=False
            focus['card']=None
        if reload:
            grid.controls=[cinema_layout.film_frame(m,i,m['id']==focus['id'],pick_archive) for i,m in enumerate(movies)]
        else:
            for row in grid.controls:
                active=row.data==focus['id']
                row.border=ft.Border.all(1.5,theme.ACCENT if active else theme.LINE)
                row.bgcolor=theme.CARD_BG_SOFT if active else theme.CARD_BG
        empty_view.visible = not movies

        if reload:
            st = db.stats()
            stat_total.value = str(st["total"])
            stat_movie.value = str(st["电影"])
            stat_tv.value = str(st["剧集"])
        page.update()

    # --- 顶部区域 ---
    def stat_block(label: str, value: ft.Text) -> ft.Container:
        """统计块：一个浅蓝小药丸，里面是数字 + 说明。"""
        return ft.Container(
            padding=ft.Padding.symmetric(horizontal=14, vertical=6),
            border_radius=12,
            bgcolor=theme.MIST_BLUE_SOFT,
            content=ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=0,
                controls=[value, ft.Text(label, size=11, color=theme.MIST_BLUE_DEEP)],
            ),
        )

    # （原来的标题栏去掉了：统计和「添加影视」合并进下面这条工具条）
    toolbar = ft.Container(
        padding=ft.Padding.only(left=28, right=28, top=16, bottom=6),
        content=ft.Row(
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                search_input,
                *filter_buttons.values(),
                ft.FilledButton(
                    "添加影视",
                    bgcolor=theme.ACCENT, color=theme.ON_ACCENT, elevation=0, height=44,
                    icon=ft.Icons.ADD,
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=12),
                        padding=ft.Padding.symmetric(horizontal=20),
                    ),
                    on_click=lambda e: open_form(),
                ),
            ],
        ),
    )

    body = ft.Container(
        expand=True,
        padding=ft.Padding.only(left=28, right=28, top=14, bottom=20),
        content=ft.Column(expand=True,scroll=ft.ScrollMode.ADAPTIVE,spacing=20, controls=[featured, empty_view]),
    )

    # 初始化显示
    paint_filters()
    paint_kind()
    paint_rating()
    refresh()

    return ft.Column(spacing=0, expand=True,
                     data={"on_resize": refresh,"on_hide":leave_page,"on_show":show_page,
                           "movie_focus":focus,"movie_rolling":rolling},
                     controls=[toolbar, body])

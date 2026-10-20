"""客行录 · 聊天长卷模块（界面部分）

把微信 / QQ 的聊天记录导入本地，像真实手机一样翻阅长长的对话，
支持分类整理、按关键字 / 日期查找，并可导出为一张长图。

布局：
    ┌─ 白色顶栏：标题 / 导入 / 清空 / 导出；关键字 + 日期范围查找 ────────┐
    │ 左栏 274       │ 中间：仿真手机聊天窗口          │ 右栏 352        │
    │ 搜索会话        │      （按日期分组、气泡尾巴、    │ 对话设置         │
    │ 分类（带数量）  │       命中高亮、上下跳转）       │ 写消息 / 管理    │
    │ 会话列表        │      长记录分页翻阅             │ 导出预览         │
    └───────────────────────────────────────────────────────────────┘
"""

from __future__ import annotations
from i18n import tr

import math
import os
import re
import shutil
import unicodedata
import uuid
from datetime import datetime, timedelta

import flet as ft

import chat_db as cdb
import chat_export as exp
import chat_import as imp
import theme
from theme import badge, blue_gradient, card_shadow, category_colors, count_pill, empty_state, glass_surface, icon_badge

IMG_EXTS = ["jpg", "jpeg", "png", "webp", "bmp"]
RECORD_EXTS = ["txt", "csv", "log", "bak"]   # 可导入的聊天记录文件（含 QQ 导出 .bak）
DEFAULT_CATEGORIES = ["朋友", "家人", "同学", "工作", "其他"]

PAGE_SIZE = 200            # 长记录每次渲染多少条（点"加载更早"再翻一页）
MANAGE_CAP = 80            # 右侧消息管理最多显示多少条
BUBBLE_MAX_W = 296         # 气泡最大宽度
BUBBLE_MIN_W = 44          # 气泡最小宽度
BUBBLE_FONT = 13           # 气泡正文字号
BUBBLE_PAD_X = 13 * 2 + 4  # 左右内边距 + 余量
WEEKDAY = "一二三四五六日"


def bubble_width(text: str) -> int:
    """按最长一行的视觉宽度估算气泡宽度（中文全角 1 字宽，西文约 0.55），
    让短消息紧凑、长消息在 BUBBLE_MAX_W 处自动换行。"""
    max_w = 0
    for line in (text or "").splitlines() or [""]:
        w = 0
        for ch in line:
            if unicodedata.east_asian_width(ch) in ("W", "F"):
                w += BUBBLE_FONT
            else:
                w += BUBBLE_FONT * 0.56
        max_w = max(max_w, w)
    return int(min(BUBBLE_MAX_W, max(BUBBLE_MIN_W, max_w + BUBBLE_PAD_X)))


# 我的气泡配色（和 chat_export.THEMES 保持一致）


# ---------------- 小工具 ----------------
def _save_image(src: str) -> str:
    """把用户选的图片复制到应用目录，避免原图被删除后失效。"""
    os.makedirs(cdb.CHAT_DIR, exist_ok=True)
    ext = os.path.splitext(src)[1].lower() or ".png"
    dst = os.path.join(cdb.CHAT_DIR, f"{uuid.uuid4().hex}{ext}")
    shutil.copyfile(src, dst)
    return dst


def _remove_image(path: str) -> None:
    """只清理本应用目录内的图片，避免误删用户文件。"""
    try:
        if path and path.startswith(cdb.CHAT_DIR) and os.path.exists(path):
            os.remove(path)
    except OSError:
        pass


def avatar_view(path: str, size: int, text: str = "影", ring: bool = True) -> ft.Control:
    """圆形头像：有图用图，没图用渐变色 + 首字；外圈一圈白边。"""
    if path and os.path.exists(path):
        inner = ft.Container(
            width=size, height=size, border_radius=size / 2,
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            content=ft.Image(src=path.replace("\\", "/"), fit=ft.BoxFit.COVER,
                             width=size, height=size),
        )
    else:
        inner = ft.Container(
            width=size, height=size, border_radius=size / 2,
            gradient=ft.LinearGradient(
                begin=ft.Alignment.TOP_LEFT, end=ft.Alignment.BOTTOM_RIGHT,
                colors=[theme.MIST_BLUE_SOFT, theme.MIST_BLUE],
            ),
            alignment=ft.Alignment.CENTER,
            content=ft.Text(text[:1], size=size * 0.42, color="#FFFFFF",
                            weight=ft.FontWeight.BOLD),
        )
    if not ring:
        return inner
    return ft.Container(
        width=size + 4, height=size + 4, border_radius=(size + 4) / 2,
        bgcolor=theme.CARD_BG,
        border=ft.Border.all(1.5, theme.LINE_SOFT),
        alignment=ft.Alignment.CENTER,
        content=inner,
    )


def section_title(text: str, icon: str | None = None) -> ft.Row:
    """小分区标题。"""
    controls = [ft.Container(width=4, height=15, border_radius=2, bgcolor=theme.MIST_BLUE)]
    if icon:
        controls.append(ft.Icon(icon, size=15, color=theme.MIST_BLUE_DEEP))
    controls.append(ft.Text(text, size=13, weight=ft.FontWeight.W_700, color=theme.TEXT_MAIN))
    return ft.Row(spacing=7, controls=controls)


def panel_card(controls: list, padding: int = 14) -> ft.Container:
    """右栏统一的白色设置卡片。"""
    return ft.Container(
        padding=ft.Padding.all(padding),
        border_radius=16,
        bgcolor=theme.CARD_BG,
        border=ft.Border.all(1, theme.LINE),
        content=ft.Column(spacing=10, controls=controls),
    )


def weekday_cn(date_text: str) -> str:
    """2026-05-01 → 周四。"""
    try:
        return "周" + WEEKDAY[datetime.strptime(date_text, "%Y-%m-%d").weekday()]
    except (ValueError, TypeError):
        return ""


def pretty_date(date_text: str) -> str:
    """2026-05-01 → 2026年5月1日 周四。"""
    try:
        d = datetime.strptime(date_text, "%Y-%m-%d")
        return f"{d.year}年{d.month}月{d.day}日 {weekday_cn(date_text)}"
    except (ValueError, TypeError):
        return date_text or ""


def short_date(date_text: str) -> str:
    """会话列表里的紧凑日期：今年只显示 05-01。"""
    try:
        d = datetime.strptime(date_text, "%Y-%m-%d")
        if d.year == datetime.now().year:
            return f"{d.month:02d}-{d.day:02d}"
        return f"{d.year % 100:02d}-{d.month:02d}-{d.day:02d}"
    except (ValueError, TypeError):
        return ""


def highlighted_text(content: str, keyword: str, color: str, size: int = 13) -> ft.Control:
    """气泡文字：命中的关键字用橙色底高亮（TextSpan），没关键字时普通文本。"""
    keyword = (keyword or "").strip()
    if not keyword:
        return ft.Text(content, size=size, color=color, selectable=True)
    normal = ft.TextStyle(color=color, size=size, height=1.35)
    hit = ft.TextStyle(color="#FFFFFF", bgcolor=theme.SEARCH_HIT, weight=ft.FontWeight.BOLD,
                       size=size, height=1.35)
    spans: list[ft.TextSpan] = []
    pos = 0
    for match in re.finditer(re.escape(keyword), content, flags=re.IGNORECASE):
        if match.start() > pos:
            spans.append(ft.TextSpan(content[pos:match.start()], normal))
        spans.append(ft.TextSpan(match.group(), hit))
        pos = match.end()
    if pos < len(content):
        spans.append(ft.TextSpan(content[pos:], normal))
    return ft.Text(spans=spans, selectable=True)


def _refresh_theme_values() -> None:
    """每次建页重新生成样式，避免模块级字段缓存旧主题。"""
    global FIELD_STYLE, THEME_OPTIONS
    FIELD_STYLE = dict(
        border={
            ft.ControlState.DEFAULT: ft.OutlineInputBorder(
                border_radius=10, side=ft.BorderSide(width=1, color=theme.LINE),
            ),
            ft.ControlState.FOCUSED: ft.OutlineInputBorder(
                border_radius=10, side=ft.BorderSide(width=1.5, color=theme.MIST_BLUE),
            ),
        },
        bgcolor=theme.CARD_BG,
        filled=True,
        text_size=13,
        color=theme.TEXT_MAIN,
        content_padding=ft.Padding.symmetric(horizontal=12, vertical=8),
    )
    THEME_OPTIONS = [("柔柠黄", "lemon", theme.SOFT_LEMON, theme.TEXT_MAIN),
                     ("雾霭蓝", "mist", theme.MIST_BLUE, "#FFFFFF")]


_refresh_theme_values()


def build(page: ft.Page) -> ft.Control:
    """构建聊天长卷模块整页内容。"""
    _refresh_theme_values()
    cdb.init_db()

    # --- 当前状态 ---
    current_conv: dict = {"id": None}
    editing_msg: dict = {"id": None}
    search_state: dict = {"keyword": "", "date_from": "", "date_to": ""}
    category_filter: dict = {"v": "全部"}
    view_state: dict = {"msgs": [], "start": 0, "after": "bottom"}
    hits_state: dict = {"indices": [], "cursor": -1}

    def show_tip(text: str) -> None:
        page.show_dialog(theme.toast(ft.Text(text, color="#FFFFFF"), bgcolor=theme.MIST_BLUE_DEEP))

    def close_dialog() -> None:
        page.pop_dialog()

    # ---------------- 文件选择器 ----------------
    image_picker = ft.FilePicker()
    record_picker = ft.FilePicker()
    page.services.append(image_picker)
    page.services.append(record_picker)

    async def pick_image(apply) -> None:
        files = await image_picker.pick_files(
            dialog_title="选择一张图片",
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=IMG_EXTS,
            allow_multiple=False,
        )
        if files:
            apply(files[0].path)

    # ---------------- 左栏：分类筛选 ----------------
    category_row = ft.Row(spacing=7, wrap=True, run_spacing=7)
    category_buttons: dict[str, ft.Control] = {}

    def paint_categories() -> None:
        for name, btn in category_buttons.items():
            active = name == category_filter["v"]
            main_c, soft_c = category_colors(name if name != "全部" else "全部")
            if name == "全部":
                main_c, soft_c = theme.MIST_BLUE, theme.MIST_BLUE_SOFT
            btn.bgcolor = soft_c if active else theme.CARD_BG
            btn.color = main_c if active else theme.TEXT_SUB
            btn.content.controls[2].color = main_c if active else theme.TEXT_FAINT

    def rebuild_categories() -> None:
        """分类按钮随会话变化重建，带上每个分类的会话数量。"""
        names = [c for c in cdb.list_categories() if c != "全部"]
        for extra in DEFAULT_CATEGORIES:
            if extra not in names:
                names.append(extra)
        names = ["全部"] + names
        counts = cdb.category_counts()
        category_buttons.clear()
        for name in names:
            icon = theme.CATEGORY_ICONS.get(name, ft.Icons.LABEL_OUTLINE)
            label = ft.Row(
                spacing=5,
                controls=[
                    ft.Icon(icon, size=13),
                    ft.Text(name, size=12, weight=ft.FontWeight.W_600),
                    ft.Text(str(counts.get(name, 0)), size=10,
                            weight=ft.FontWeight.W_700),
                ],
            )
            category_buttons[name] = ft.FilledButton(
                content=label, data=name, height=30, elevation=0,
                on_click=lambda e: on_category(e.control.data),
                style=ft.ButtonStyle(
                    shape=ft.RoundedRectangleBorder(radius=9),
                    padding=ft.Padding.symmetric(horizontal=11),
                ),
            )
        category_row.controls = list(category_buttons.values())
        if category_filter["v"] not in category_buttons:
            category_filter["v"] = "全部"
        paint_categories()

    def on_category(name: str) -> None:
        category_filter["v"] = name
        paint_categories()
        refresh_conversations()

    # ---------------- 左栏：会话列表 ----------------
    conv_search = ft.TextField(
        **FIELD_STYLE, hint_text="搜索会话 / 消息…", height=38,
        prefix_icon=ft.Icons.SEARCH,
        on_change=lambda e: refresh_conversations(keep_current=True),
    )
    conv_list = ft.ListView(spacing=9, expand=True, padding=ft.Padding.only(right=3))

    def build_conversation_card(conv: dict) -> ft.Control:
        active = conv["id"] == current_conv["id"]
        main_c, soft_c = category_colors(conv.get("category") or "未分类")
        preview = (conv.get("last_preview") or "").replace("\n", " ").strip()
        if len(preview) > 22:
            preview = preview[:22] + "…"
        if not preview:
            preview = "还没有消息，点右侧导入或写一条"
        if conv.get("last_side") == 0 and (conv.get("last_preview") or "").strip():
            preview = "我: " + preview
        date_text = short_date(conv.get("last_date") or "")

        return ft.Container(
            padding=ft.Padding.symmetric(horizontal=12, vertical=11),
            border_radius=16,
            bgcolor=soft_c if active else theme.CARD_BG,
            border=ft.Border.all(1.4, main_c if active else theme.LINE),
            shadow=card_shadow() if active else None,
            on_click=lambda e, cid=conv["id"]: select_conversation(cid),
            content=ft.Column(
                spacing=8,
                controls=[
                    ft.Row(
                        spacing=10,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            avatar_view(conv.get("avatar") or "", 40, conv["name"][:1]),
                            ft.Column(
                                spacing=3, expand=True,
                                controls=[
                                    ft.Row(spacing=8, controls=[
                                        ft.Text(
                                            conv["name"], size=13.5,
                                            weight=ft.FontWeight.W_700, color=theme.TEXT_MAIN,
                                            max_lines=1, overflow=ft.TextOverflow.ELLIPSIS,
                                            expand=True,
                                        ),
                                        ft.Text(date_text, size=10, color=theme.TEXT_SUB),
                                    ]),
                                    ft.Text(
                                        preview, size=11, color=theme.TEXT_SUB,
                                        max_lines=1, overflow=ft.TextOverflow.ELLIPSIS,
                                    ),
                                ],
                            ),
                            ft.IconButton(
                                ft.Icons.DELETE_OUTLINE, icon_size=15,
                                icon_color=theme.DANGER, tooltip="删除这段对话",
                                width=26, height=26, padding=0,
                                data=conv["id"], on_click=remove_conversation,
                            ),
                        ],
                    ),
                    ft.Row(spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                           controls=[
                        ft.Container(
                            padding=ft.Padding.symmetric(horizontal=8, vertical=2.5),
                            border_radius=8, bgcolor=theme.CARD_BG if active else theme.CARD_BG_SOFT,
                            content=ft.Row(spacing=4, controls=[
                                ft.Container(width=6, height=6, border_radius=3, bgcolor=main_c),
                                ft.Text(conv.get("category") or "未分类", size=10,
                                        color=theme.MIST_BLUE_DEEP),
                            ]),
                        ),
                        ft.Container(expand=True),
                        ft.Icon(ft.Icons.FORUM_OUTLINED, size=11, color=theme.TEXT_FAINT),
                        ft.Text(f"{conv['message_count']} 条", size=10, color=theme.TEXT_FAINT),
                    ]),
                ],
            ),
        )

    def refresh_conversations(keep_current: bool = True) -> None:
        keyword = (conv_search.value or "").strip()
        convs = cdb.list_conversations(category_filter["v"], keyword)
        if not keep_current or current_conv["id"] not in [c["id"] for c in convs]:
            current_conv["id"] = convs[0]["id"] if convs else None

        if convs:
            conv_list.controls = [build_conversation_card(c) for c in convs]
        else:
            conv_list.controls = [
                ft.Container(
                    padding=ft.Padding.symmetric(vertical=34),
                    content=ft.Column(spacing=6, horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                      controls=[
                        ft.Icon(ft.Icons.INBOX_OUTLINED, size=40, color=theme.TEXT_FAINT),
                        ft.Text("没有符合的对话", size=12, color=theme.TEXT_SUB),
                    ]),
                )
            ]
        refresh_chat()

    def select_conversation(conversation_id: int) -> None:
        current_conv["id"] = conversation_id
        editing_msg["id"] = None
        reset_search_state(silent=True)
        view_state["after"] = "bottom"
        refresh_conversations()

    def add_conversation(e=None) -> None:
        name = (new_conv_input.value or "").strip() or "新对话"
        cid = cdb.add_conversation(
            name,
            category_filter["v"] if category_filter["v"] != "全部" else "未分类",
        )
        new_conv_input.value = ""
        current_conv["id"] = cid
        rebuild_categories()
        refresh_conversations()
        show_tip("已创建新对话")

    def remove_conversation(e) -> None:
        conv = cdb.delete_conversation(e.control.data)
        if conv:
            for key in ("avatar", "my_avatar", "background"):
                _remove_image(conv.get(key) or "")
        rebuild_categories()
        refresh_conversations()
        show_tip("对话已删除")

    new_conv_input = ft.TextField(
        **FIELD_STYLE, hint_text="新对话名称", height=38,
        on_submit=add_conversation,
    )

    left_panel = ft.Container(
        width=274,
        padding=ft.Padding.symmetric(horizontal=14, vertical=16),
        bgcolor=theme.CARD_BG,
        border=ft.Border.only(right=ft.BorderSide(1, theme.LINE)),
        content=ft.Column(spacing=12, controls=[
            ft.Row(spacing=9, controls=[
                icon_badge(ft.Icons.FORUM_OUTLINED, 36),
                ft.Column(spacing=1, controls=[
                    ft.Text("我的消息卷", size=14, weight=ft.FontWeight.W_700,
                            color=theme.TEXT_MAIN),
                    ft.Text("导入微信 / QQ，留住长对话", size=10.5, color=theme.TEXT_SUB),
                ]),
            ]),
            conv_search,
            section_title("分类"),
            category_row,
            ft.Row(spacing=8, controls=[
                ft.Container(expand=True, content=new_conv_input),
                ft.IconButton(ft.Icons.ADD, icon_color="#FFFFFF", bgcolor=theme.MIST_BLUE,
                              tooltip="新建对话", width=38, height=38, padding=0,
                              style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=11)),
                              on_click=add_conversation),
            ]),
            ft.Divider(height=1, color=theme.LINE_SOFT),
            conv_list,
        ]),
    )

    # ---------------- 顶栏 ----------------
    def clear_messages(e=None) -> None:
        if not current_conv["id"]:
            return

        def confirm(e) -> None:
            cdb.clear_messages(current_conv["id"])
            close_dialog()
            editing_msg["id"] = None
            refresh_conversations()
            show_tip("已清空这段对话的消息")

        page.show_dialog(ft.AlertDialog(
            modal=True,
            title=ft.Text("清空消息", size=17, weight=ft.FontWeight.BOLD, color=theme.TEXT_MAIN),
            bgcolor=theme.CARD_BG,
            shape=ft.RoundedRectangleBorder(radius=18),
            content=ft.Text("会删除这段对话里的所有消息，对话本身保留。确定吗？",
                            size=13, color=theme.TEXT_MAIN),
            actions=[
                ft.TextButton("再想想", on_click=lambda e: close_dialog()),
                ft.FilledButton("清空", bgcolor=theme.DANGER, color="#FFFFFF",
                                elevation=0, on_click=confirm),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        ))

    # ---- 搜索区 ----
    search_input = ft.TextField(
        **FIELD_STYLE, hint_text="搜索消息中的关键字…", height=38, width=230,
        prefix_icon=ft.Icons.SEARCH, on_submit=lambda e: run_search(),
    )
    date_from_input = ft.TextField(
        **FIELD_STYLE, hint_text="开始日期", height=38, width=132, read_only=True,
    )
    date_to_input = ft.TextField(
        **FIELD_STYLE, hint_text="结束日期", height=38, width=132, read_only=True,
    )

    def on_date_picked(which: str):
        def handler(e) -> None:
            if e.control.value:
                text = e.control.value.strftime("%Y-%m-%d")
                if which == "from":
                    date_from_input.value = text
                else:
                    date_to_input.value = text
                page.update()
                run_search()
        return handler

    date_from_picker = ft.DatePicker(first_date=datetime(1990, 1, 1),
                                     last_date=datetime(2040, 12, 31),
                                     on_change=on_date_picked("from"))
    date_to_picker = ft.DatePicker(first_date=datetime(1990, 1, 1),
                                   last_date=datetime(2040, 12, 31),
                                   on_change=on_date_picked("to"))

    def set_quick_range(days: int | None) -> None:
        """days=None 表示全部；0 表示今天。"""
        if days is None:
            date_from_input.value = ""
            date_to_input.value = ""
        else:
            today = datetime.now()
            start = today if days == 0 else today - timedelta(days=days - 1)
            date_from_input.value = start.strftime("%Y-%m-%d")
            date_to_input.value = today.strftime("%Y-%m-%d")
        run_search()

    def quick_chip(label: str, days) -> ft.Control:
        return ft.FilledButton(
            content=label, data=days, height=30, elevation=0,
            bgcolor=theme.CARD_BG, color=theme.TEXT_SUB,
            on_click=lambda e: set_quick_range(e.control.data),
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=9),
                padding=ft.Padding.symmetric(horizontal=10),
            ),
        )

    quick_row = ft.Row(spacing=6, controls=[
        quick_chip("全部", None),
        quick_chip("今天", 0),
        quick_chip("近7天", 7),
        quick_chip("近30天", 30),
    ])

    def run_search() -> None:
        search_state["keyword"] = (search_input.value or "").strip()
        search_state["date_from"] = (date_from_input.value or "").strip()
        search_state["date_to"] = (date_to_input.value or "").strip()
        view_state["after"] = "top"
        refresh_chat()

    def reset_search_state(silent: bool = False) -> None:
        search_input.value = ""
        date_from_input.value = ""
        date_to_input.value = ""
        search_state.update(keyword="", date_from="", date_to="")
        if not silent:
            view_state["after"] = "bottom"
            refresh_chat()

    # 顶栏只保留查找工具条（标题已去掉，导入 / 清空 / 导出移到右栏顶部）
    top_bar = ft.Container(
        padding=ft.Padding.symmetric(horizontal=22, vertical=12),
        **glass_surface(),
        border=ft.Border.only(bottom=ft.BorderSide(1, theme.GLASS_BORDER)),
        content=ft.Column(spacing=0, controls=[
            ft.Container(
                padding=ft.Padding.symmetric(horizontal=12, vertical=8),
                border_radius=12, bgcolor=theme.CARD_BG_SOFT,
                border=ft.Border.all(1, theme.LINE_SOFT),
                content=ft.Row(
                    spacing=9, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Container(width=228, content=search_input),
                        ft.Container(width=1, height=22, bgcolor=theme.LINE),
                        ft.Icon(ft.Icons.CALENDAR_MONTH_OUTLINED, size=16, color=theme.TEXT_SUB),
                        ft.Container(width=132, content=date_from_input),
                        ft.Text("至", size=11, color=theme.TEXT_SUB),
                        ft.Container(width=132, content=date_to_input),
                        ft.IconButton(ft.Icons.CALENDAR_TODAY_OUTLINED, icon_size=17,
                                      icon_color=theme.MIST_BLUE_DEEP, tooltip="选择开始日期",
                                      width=30, height=30, padding=0,
                                      on_click=lambda e: page.show_dialog(date_from_picker)),
                        ft.IconButton(ft.Icons.EVENT_OUTLINED, icon_size=17,
                                      icon_color=theme.MIST_BLUE_DEEP, tooltip="选择结束日期",
                                      width=30, height=30, padding=0,
                                      on_click=lambda e: page.show_dialog(date_to_picker)),
                        ft.Container(width=1, height=22, bgcolor=theme.LINE),
                        quick_row,
                        ft.Container(expand=True),
                        ft.FilledButton(
                            "查找", icon=ft.Icons.MANAGE_SEARCH,
                            bgcolor=theme.MIST_BLUE, color="#FFFFFF", height=34, elevation=0,
                            style=ft.ButtonStyle(
                                shape=ft.RoundedRectangleBorder(radius=10),
                                padding=ft.Padding.symmetric(horizontal=14),
                            ),
                            on_click=lambda e: run_search(),
                        ),
                        ft.TextButton(tr("清除"), height=34,
                                      on_click=lambda e: reset_search_state()),
                    ],
                ),
            ),
        ]),
    )

    # ---------------- 中间：仿真手机 ----------------
    chat_list = ft.ListView(spacing=13, padding=ft.Padding.all(18), expand=True,
                            auto_scroll=False)
    phone_title = ft.Text("", size=15.5, weight=ft.FontWeight.W_700, color="#FFFFFF",
                          max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, text_align=ft.TextAlign.CENTER)
    phone_subtitle = ft.Text("", size=10.5, color="#E3EBF7", text_align=ft.TextAlign.CENTER)
    bg_layer = ft.Container(expand=True, bgcolor=theme.BG)
    empty_layer = ft.Container(visible=False, expand=True,
                               alignment=ft.Alignment.CENTER)

    # 查找状态条（标题栏下方）
    hit_pos_text = ft.Text("", size=11, weight=ft.FontWeight.W_700, color=theme.SEARCH_HIT)
    hit_bar = ft.Container(
        visible=False,
        padding=ft.Padding.symmetric(horizontal=12, vertical=7),
        bgcolor="#FFF9F2",
        border=ft.Border.only(bottom=ft.BorderSide(1, "#F4DFC6")),
        content=ft.Row(spacing=7, vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[
            ft.Icon(ft.Icons.MANAGE_SEARCH, size=14, color=theme.SEARCH_HIT),
            ft.Text("", size=11.5, weight=ft.FontWeight.W_600, color=theme.TEXT_MAIN,
                    expand=True),
            hit_pos_text,
            ft.IconButton(ft.Icons.KEYBOARD_ARROW_UP_ROUNDED, icon_size=17,
                          icon_color=theme.MIST_BLUE_DEEP, width=28, height=28, padding=0,
                          tooltip="上一条命中", on_click=lambda e: goto_hit(-1)),
            ft.IconButton(ft.Icons.KEYBOARD_ARROW_DOWN_ROUNDED, icon_size=17,
                          icon_color=theme.MIST_BLUE_DEEP, width=28, height=28, padding=0,
                          tooltip="下一条命中", on_click=lambda e: goto_hit(1)),
            ft.IconButton(ft.Icons.CLOSE_ROUNDED, icon_size=15, icon_color=theme.TEXT_SUB,
                          width=26, height=26, padding=0, tooltip="清除查找",
                          on_click=lambda e: reset_search_state()),
        ]),
    )
    range_bar = ft.Container(
        padding=ft.Padding.symmetric(horizontal=12, vertical=6),
        bgcolor=theme.CARD_BG_SOFT,
        border=ft.Border.only(bottom=ft.BorderSide(1, theme.LINE_SOFT)),
        content=ft.Row(alignment=ft.MainAxisAlignment.CENTER, controls=[
            ft.Text("", size=10.5, color=theme.TEXT_SUB),
        ]),
    )

    # 微信风手机标题栏（灵动岛 + 返回 + 居中标题 + 更多）
    phone_header = ft.Container(
        height=64,
        gradient=blue_gradient(),
        content=ft.Stack(expand=True, controls=[
            ft.Container(
                left=0, right=0, top=7, height=22,
                alignment=ft.Alignment.CENTER,
                content=ft.Container(width=94, height=20, border_radius=10,
                                     bgcolor="#20294A"),
            ),
            ft.Row(
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(width=50, alignment=ft.Alignment.CENTER,
                                 content=ft.Icon(ft.Icons.ARROW_BACK_IOS_NEW_ROUNDED,
                                                 size=17, color="#FFFFFF")),
                    ft.Container(expand=True, padding=ft.Padding.only(top=14),
                                 content=ft.Column(spacing=1, alignment=ft.CrossAxisAlignment.CENTER,
                                                   controls=[phone_title, phone_subtitle])),
                    ft.Container(width=50, alignment=ft.Alignment.CENTER,
                                 content=ft.Icon(ft.Icons.MORE_HORIZ, size=19, color="#FFFFFF")),
                ],
            ),
        ]),
    )

    chat_stage = ft.Stack(expand=True, controls=[bg_layer, chat_list, empty_layer])

    screen = ft.Container(
        expand=True, border_radius=32, clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        bgcolor=theme.BG,
        content=ft.Column(spacing=0, expand=True, controls=[
            phone_header, hit_bar, range_bar,
            ft.Container(expand=True, content=chat_stage),
        ]),
    )

    # 深色机身 + 侧边按键
    phone_body = ft.Container(
        width=466, expand=True,
        padding=ft.Padding.all(8),
        border_radius=40,
        gradient=ft.LinearGradient(
            begin=ft.Alignment.TOP_CENTER, end=ft.Alignment.BOTTOM_CENTER,
            colors=["#3A4663", "#232C42"],
        ),
        shadow=card_shadow(True),
        content=ft.Stack(clip_behavior=ft.ClipBehavior.NONE, controls=[
            screen,
            ft.Container(width=4, height=54, border_radius=2, bgcolor="#1C2438",
                         right=-2, top=120),
            ft.Container(width=4, height=42, border_radius=2, bgcolor="#1C2438",
                         right=-2, top=192),
            ft.Container(width=4, height=64, border_radius=2, bgcolor="#1C2438",
                         left=-2, top=160),
        ]),
    )

    center_area = ft.Container(
        expand=True,
        padding=ft.Padding.symmetric(horizontal=26, vertical=18),
        alignment=ft.Alignment.CENTER,
        content=phone_body,
    )

    # ---------------- 右侧：设置 / 录入 / 管理 / 导出 ----------------
    # 对话基础信息
    title_input = ft.TextField(**FIELD_STYLE, label="对方昵称", height=42)
    subtitle_input = ft.TextField(**FIELD_STYLE, label="标题栏小字", height=42)

    def save_meta(e=None) -> None:
        if not current_conv["id"]:
            return
        cdb.update_conversation(
            current_conv["id"],
            name=(title_input.value or "").strip() or "未命名对话",
            subtitle=(subtitle_input.value or "").strip(),
        )
        refresh_conversations()

    title_input.on_blur = save_meta
    subtitle_input.on_blur = save_meta

    def image_field_button(label: str, icon: str, field_name: str, clear: bool = False):
        if clear:
            return ft.TextButton(label, icon=icon, on_click=clear_field(field_name))
        return ft.TextButton(label, icon=icon, on_click=set_field(field_name))

    def set_field(field_name: str):
        def apply(path: str) -> None:
            if not current_conv["id"]:
                return
            conv = cdb.get_conversation(current_conv["id"]) or {}
            old = conv.get(field_name)
            if old and old != path:
                _remove_image(old)
            saved = _save_image(path)
            cdb.update_conversation(current_conv["id"], **{field_name: saved})
            refresh_chat()

        async def handler(e) -> None:
            await pick_image(apply)

        return handler

    def clear_field(field_name: str):
        def handler(e) -> None:
            if not current_conv["id"]:
                return
            conv = cdb.get_conversation(current_conv["id"]) or {}
            _remove_image(conv.get(field_name) or "")
            cdb.update_conversation(current_conv["id"], **{field_name: None})
            refresh_chat()

        return handler

    # 气泡配色
    theme_buttons = {
        key: ft.Container(
            border_radius=11, padding=ft.Padding.symmetric(horizontal=12, vertical=7),
            border=ft.Border.all(1.5, theme.LINE), data=key, ink=True,
            on_click=lambda e: set_theme(e.control.data),
            content=ft.Row(spacing=7, controls=[
                ft.Container(width=16, height=16, border_radius=8,
                             bgcolor=color, border=ft.Border.all(1, theme.LINE)),
                ft.Text(label, size=12, color=theme.TEXT_MAIN, weight=ft.FontWeight.W_600),
            ]),
        )
        for label, key, color, _ in THEME_OPTIONS
    }
    theme_row = ft.Row(spacing=8, controls=list(theme_buttons.values()))

    def set_theme(key: str) -> None:
        if not current_conv["id"]:
            return
        cdb.update_conversation(current_conv["id"], theme=key)
        refresh_chat()

    def paint_theme(current: str) -> None:
        for label, key, color, text_c in THEME_OPTIONS:
            btn = theme_buttons[key]
            active = key == current
            btn.border = ft.Border.all(1.5, color if active else theme.LINE)
            btn.bgcolor = color + "18" if active else theme.CARD_BG

    # 分类设置
    category_pick_row = ft.Row(spacing=6, wrap=True, run_spacing=6)
    category_pick_buttons: dict[str, ft.Control] = {}

    def set_category_of_conv(name: str) -> None:
        if not current_conv["id"]:
            return
        cdb.update_conversation(current_conv["id"], category=name)
        rebuild_categories()
        refresh_conversations()

    def paint_category_pick(current: str) -> None:
        for name, btn in category_pick_buttons.items():
            active = (name == (current or "未分类"))
            main_c, soft_c = category_colors(name)
            btn.bgcolor = main_c if active else theme.CARD_BG
            btn.color = "#FFFFFF" if active else theme.TEXT_SUB

    def rebuild_category_pick(current: str) -> None:
        names = [c for c in cdb.list_categories() if c != "全部"]
        for extra in DEFAULT_CATEGORIES:
            if extra not in names:
                names.append(extra)
        category_pick_buttons.clear()
        for name in names:
            category_pick_buttons[name] = ft.FilledButton(
                content=name, data=name, height=29, elevation=0,
                on_click=lambda e: set_category_of_conv(e.control.data),
                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=9),
                                     padding=ft.Padding.symmetric(horizontal=11)),
            )
        category_pick_row.controls = list(category_pick_buttons.values())
        paint_category_pick(current)

    def add_custom_category(e=None) -> None:
        name = (new_category_input.value or "").strip()
        if name and current_conv["id"]:
            set_category_of_conv(name)
        new_category_input.value = ""

    new_category_input = ft.TextField(
        **FIELD_STYLE, hint_text="自定义分类", height=34,
        on_submit=add_custom_category,
    )

    actions_card = panel_card([
        section_title("常用操作"),
        ft.Row(spacing=8, controls=[
            ft.OutlinedButton(
                "导入聊天记录", icon=ft.Icons.FILE_UPLOAD_OUTLINED,
                height=36, expand=True, style=ft.ButtonStyle(
                    shape=ft.RoundedRectangleBorder(radius=11),
                    side=ft.BorderSide(1.2, theme.LINE),
                    color=theme.TEXT_SUB,
                    padding=ft.Padding.symmetric(horizontal=10),
                ),
                on_click=lambda e: open_import(),
            ),
            ft.OutlinedButton(
                "清空消息", icon=ft.Icons.DELETE_SWEEP_OUTLINED,
                height=36, expand=True, style=ft.ButtonStyle(
                    shape=ft.RoundedRectangleBorder(radius=11),
                    side=ft.BorderSide(1.2, theme.LINE),
                    color=theme.TEXT_SUB,
                    padding=ft.Padding.symmetric(horizontal=10),
                ),
                on_click=clear_messages,
            ),
        ]),
        ft.FilledButton(
            "导出为长图", icon=ft.Icons.DOWNLOAD_ROUNDED, expand=True,
            bgcolor=theme.SOFT_LEMON, color=theme.TEXT_MAIN, height=36, elevation=0,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=11),
                padding=ft.Padding.symmetric(horizontal=18),
            ),
            on_click=lambda e: export_image(),
        ),
    ])

    settings_card = panel_card([
        section_title("对话设置", ft.Icons.TUNE_ROUNDED),
        title_input,
        subtitle_input,
        ft.Row(spacing=6, wrap=True, controls=[
            image_field_button("对方头像", ft.Icons.PERSON_OUTLINE, "avatar"),
            image_field_button("我的头像", ft.Icons.FACE_6_OUTLINED, "my_avatar"),
            image_field_button("聊天背景", ft.Icons.IMAGE_OUTLINED, "background"),
            image_field_button("清除背景", ft.Icons.CLOSE_ROUNDED, "background", clear=True),
        ]),
        ft.Text("我的气泡配色", size=11, color=theme.TEXT_SUB),
        theme_row,
        ft.Text("分类", size=11, color=theme.TEXT_SUB),
        category_pick_row,
        ft.Row(spacing=8, controls=[
            ft.Container(expand=True, content=new_category_input),
            ft.IconButton(ft.Icons.ADD, icon_color="#FFFFFF", bgcolor=theme.MIST_BLUE,
                          tooltip="添加并设为该分类", width=34, height=34, padding=0,
                          on_click=add_custom_category),
        ]),
    ])

    # ---- 写消息 ----
    msg_content = ft.TextField(
        **FIELD_STYLE, label="消息内容", hint_text="写一句话…",
        multiline=True, min_lines=3, max_lines=6, height=110,
    )
    msg_time = ft.TextField(**FIELD_STYLE, label="时间文字", hint_text="如 21:30", height=42)
    msg_show_time = ft.Checkbox(label="在这条上方显示时间分隔", value=False,
                                active_color=theme.MIST_BLUE)
    msg_list = ft.ListView(spacing=7, height=300, padding=ft.Padding.only(right=3))
    export_preview = ft.Column(spacing=8, visible=False)

    picked_side: dict = {"v": 1}
    side_buttons = {
        name: ft.FilledButton(
            content=name, data=1 if name == "对方" else 0, height=33, elevation=0,
            on_click=lambda e: (picked_side.update({"v": e.control.data}), paint_side()),
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=9),
                                 padding=ft.Padding.symmetric(horizontal=16)),
        )
        for name in ["对方", "我"]
    }
    side_row = ft.Row(spacing=8, controls=list(side_buttons.values()))

    def paint_side() -> None:
        for name, btn in side_buttons.items():
            active = picked_side["v"] == (1 if name == "对方" else 0)
            btn.bgcolor = theme.MIST_BLUE if active else theme.CARD_BG
            btn.color = "#FFFFFF" if active else theme.TEXT_SUB

    def fill_now(e=None) -> None:
        msg_time.value = datetime.now().strftime("%H:%M")
        page.update()

    def save_message(e=None) -> None:
        content = (msg_content.value or "").strip()
        if not current_conv["id"]:
            show_tip("先在左边新建一段对话")
            return
        if not content:
            show_tip("消息内容不能为空")
            return

        time_label = (msg_time.value or "").strip()
        if editing_msg["id"]:
            cdb.update_message(editing_msg["id"], picked_side["v"], content,
                               time_label, bool(msg_show_time.value))
            editing_msg["id"] = None
            tip = "消息已更新"
        else:
            cdb.add_message(current_conv["id"], picked_side["v"], content, time_label,
                            bool(msg_show_time.value))
            tip = "已添加一条消息"

        msg_content.value = ""
        msg_show_time.value = False
        msg_time.value = ""
        view_state["after"] = "bottom"
        refresh_conversations()
        show_tip(tip)

    def cancel_edit(e=None) -> None:
        editing_msg["id"] = None
        msg_content.value = ""
        msg_time.value = ""
        msg_show_time.value = False
        refresh_chat()

    def edit_message(msg_id: int) -> None:
        msg = next((m for m in cdb.list_messages(current_conv["id"])
                    if m["id"] == msg_id), None)
        if not msg:
            return
        editing_msg["id"] = msg_id
        msg_content.value = msg.get("content") or ""
        msg_time.value = msg.get("time_label") or ""
        msg_show_time.value = bool(msg.get("show_time"))
        picked_side["v"] = int(msg.get("side") or 0)
        paint_side()
        page.update()

    def delete_message(msg_id: int) -> None:
        cdb.delete_message(msg_id)
        if editing_msg["id"] == msg_id:
            cancel_edit()
        refresh_conversations()
        show_tip("消息已删除")

    def move_message(msg_id: int, delta: int) -> None:
        cdb.move_message(msg_id, delta)
        refresh_chat()

    editor_card = panel_card([
        section_title("写一条消息", ft.Icons.EDIT_NOTE_OUTLINED),
        side_row,
        msg_content,
        ft.Row(spacing=8, controls=[
            ft.Container(expand=True, content=msg_time),
            ft.IconButton(ft.Icons.SCHEDULE_ROUNDED, icon_color=theme.MIST_BLUE_DEEP,
                          tooltip="填入当前时间", on_click=fill_now),
        ]),
        msg_show_time,
        ft.Row(spacing=10, controls=[
            ft.FilledButton(
                "保存消息", icon=ft.Icons.ADD_ROUNDED, expand=True,
                bgcolor=theme.MIST_BLUE, color="#FFFFFF", height=38, elevation=0,
                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=11)),
                on_click=save_message),
            ft.TextButton("取消编辑", on_click=cancel_edit),
        ]),
    ])

    manage_card = panel_card([
        ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[
            section_title("消息管理", ft.Icons.LIST_ALT_ROUNDED),
            ft.Text("最近 80 条", size=10, color=theme.TEXT_FAINT),
        ]),
        ft.Container(height=300, content=msg_list),
    ])

    export_card = panel_card([export_preview])

    right_panel = ft.Container(
        width=352,
        bgcolor=theme.CARD_BG_SOFT,
        border=ft.Border.only(left=ft.BorderSide(1, theme.LINE)),
        content=ft.ListView(
            spacing=12, padding=ft.Padding.all(14),
            controls=[actions_card, settings_card, editor_card, manage_card,
                      export_card],
        ),
    )

    # ---------------- 中间渲染 ----------------
    def make_bubble(msg: dict, conv: dict | None, keyword: str,
                    hit: bool, global_index: int) -> ft.Control:
        is_me = int(msg.get("side") or 0) == 0
        theme_key = (conv or {}).get("theme") or "lemon"
        if is_me:
            bubble_c = theme.SOFT_LEMON if theme_key == "lemon" else theme.MIST_BLUE
            text_c = theme.TEXT_MAIN if theme_key == "lemon" else "#FFFFFF"
        else:
            bubble_c = "#FFFFFF"
            text_c = theme.TEXT_MAIN

        content = (msg.get("content") or "").strip()
        bubble_inner = ft.Container(
            width=bubble_width(content),
            padding=ft.Padding.symmetric(horizontal=13, vertical=9),
            border_radius=15,
            bgcolor=bubble_c,
            border=ft.Border.all(1.4, theme.APRICOT if hit else "#00000000"),
            shadow=ft.BoxShadow(blur_radius=8, spread_radius=-3, color=theme.SHADOW,
                               offset=ft.Offset(0, 3)),
            content=highlighted_text(content, keyword, text_c, 13),
        )
        bubble_wrap = bubble_inner

        # 小三角气泡尾巴：旋转 45° 的小方块，一半压在气泡下面
        tail = ft.Container(
            width=11, height=11, border_radius=2.5, bgcolor=bubble_c,
            rotate=ft.Rotate(angle=math.pi / 4),
            top=13, right=-3 if is_me else None, left=-3 if not is_me else None,
            shadow=ft.BoxShadow(blur_radius=3, spread_radius=-1, color=theme.SHADOW,
                                offset=ft.Offset(0 if is_me else 1, 1)),
        )
        bubble_stack = ft.Stack(clip_behavior=ft.ClipBehavior.NONE,
                                controls=[tail, bubble_wrap])

        avatar_path = ((conv or {}).get("my_avatar") if is_me
                       else (conv or {}).get("avatar"))
        avatar = avatar_view(avatar_path or "", 36,
                             (conv or {}).get("name", "影")[:1])
        row_controls = [bubble_stack, avatar] if is_me else [avatar, bubble_stack]
        return ft.Row(
            key=f"hit-{global_index}" if hit else None,
            spacing=8,
            alignment=ft.MainAxisAlignment.END if is_me else ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.START,
            controls=row_controls,
        )

    def load_earlier(e=None) -> None:
        view_state["start"] = max(0, view_state["start"] - PAGE_SIZE)
        render_messages(scroll_mode="keep")

    def render_messages(scroll_mode: str = "") -> None:
        """按当前窗口把消息画到手机里（窗口化，保证长记录不卡）。"""
        conv = cdb.get_conversation(current_conv["id"]) if current_conv["id"] else None
        msgs = view_state["msgs"]
        total = len(msgs)
        start = view_state["start"]
        end = min(total, start + PAGE_SIZE)
        visible = msgs[start:end]
        keyword = search_state["keyword"]
        filtering = bool(keyword or search_state["date_from"] or search_state["date_to"])

        # 背景层
        bg_path = (conv or {}).get("background") or ""
        if bg_path and os.path.exists(bg_path):
            bg_layer.content = ft.Image(src=bg_path.replace("\\", "/"),
                                        fit=ft.BoxFit.COVER, expand=True)
            bg_layer.bgcolor = None
            bg_layer.gradient = None
        else:
            bg_layer.content = None
            bg_layer.bgcolor = theme.BG
            bg_layer.gradient = ft.LinearGradient(
                begin=ft.Alignment.TOP_CENTER, end=ft.Alignment.BOTTOM_CENTER,
                colors=["#F2F6FC", "#E9F0F9"],
            )

        controls: list[ft.Control] = []
        if start > 0:
            controls.append(ft.Row(alignment=ft.MainAxisAlignment.CENTER, controls=[
                ft.Container(
                    border_radius=18, bgcolor="#FFFFFF",
                    border=ft.Border.all(1, theme.LINE),
                    padding=ft.Padding.symmetric(horizontal=14, vertical=6),
                    ink=True, on_click=load_earlier,
                    content=ft.Row(spacing=6, controls=[
                        ft.Icon(ft.Icons.ARROW_DROP_UP_ROUNDED, size=16,
                                color=theme.MIST_BLUE_DEEP),
                        ft.Text(f"加载更早的 {min(PAGE_SIZE, start)} 条",
                                size=11, color=theme.MIST_BLUE_DEEP,
                                weight=ft.FontWeight.W_600),
                    ]),
                ),
            ]))

        last_date = ""
        for offset, msg in enumerate(visible):
            gi = start + offset
            msg_date = (msg.get("msg_date") or "").strip()
            if msg_date and msg_date != last_date:
                controls.append(ft.Row(alignment=ft.MainAxisAlignment.CENTER, controls=[
                    ft.Container(
                        padding=ft.Padding.symmetric(horizontal=13, vertical=4.5),
                        border_radius=13, bgcolor="#FFFFFFEE",
                        border=ft.Border.all(1, theme.LINE),
                        content=ft.Text(pretty_date(msg_date), size=10.5,
                                        color=theme.MIST_BLUE_DEEP, weight=ft.FontWeight.W_600),
                    ),
                ]))
                last_date = msg_date

            if msg.get("show_time") and (msg.get("time_label") or "").strip():
                controls.append(ft.Row(alignment=ft.MainAxisAlignment.CENTER, controls=[
                    ft.Container(
                        padding=ft.Padding.symmetric(horizontal=10, vertical=3),
                        border_radius=11, bgcolor="#2C3A5299",
                        content=ft.Text(msg["time_label"], size=10.5, color="#FFFFFF"),
                    ),
                ]))

            content = (msg.get("content") or "").strip()
            hit = bool(keyword) and keyword.lower() in content.lower()
            controls.append(make_bubble(msg, conv, keyword, hit, gi))

        # 空状态
        has_conv = conv is not None
        if total == 0:
            empty_layer.visible = True
            if not has_conv:
                empty_layer.content = empty_state(
                    ft.Icons.FORUM_OUTLINED, "还没有聊天卷",
                    "点左下角「+」新建对话\n或在上方「导入聊天记录」粘贴微信 / QQ 记录",
                    theme.MIST_BLUE)
            elif filtering:
                empty_layer.content = empty_state(
                    ft.Icons.MANAGE_SEARCH, "没有找到匹配的消息",
                    "换个关键字或清空日期范围试试", theme.APRICOT)
            else:
                empty_layer.content = empty_state(
                    ft.Icons.CHAT_BUBBLE_OUTLINE, "这段对话还没有消息",
                    "用右侧「写一条消息」记录，或导入聊天记录", theme.MINT_GREEN)
            chat_list.visible = False
        else:
            empty_layer.visible = False
            chat_list.visible = True

        chat_list.controls = controls

        # 顶部状态条
        if filtering:
            hit_bar.visible = True
            summary_parts = [f"共找到 {total} 条结果"]
            if keyword:
                summary_parts.append(f"关键字「{keyword}」")
            if search_state["date_from"] or search_state["date_to"]:
                summary_parts.append(
                    f"{search_state['date_from'] or '…'} ~ {search_state['date_to'] or '…'}")
            hit_bar.content.controls[1].value = " · ".join(summary_parts)
            hit_count = len(hits_state["indices"])
            if hit_count:
                cur = hits_state["cursor"] + 1 if hits_state["cursor"] >= 0 else 0
                hit_pos_text.value = f"{max(cur, 1)} / {hit_count}"
            else:
                hit_pos_text.value = ""
        else:
            hit_bar.visible = False
            if conv:
                all_count = cdb.count_messages(conv["id"])
                if all_count:
                    dfrom = msgs[0].get("msg_date") or ""
                    dto = msgs[-1].get("msg_date") or ""
                    range_bar.visible = True
                    range_bar.content.controls[0].value = (
                        f"共 {all_count} 条消息 · {dfrom} 至 {dto}"
                        + (f" · 当前显示 {start + 1}–{end}" if total > PAGE_SIZE else ""))
                else:
                    range_bar.visible = False
            else:
                range_bar.visible = False

        page.update()

        # 渲染完后的滚动
        mode = scroll_mode or view_state.get("after") or ""
        if mode == "bottom":
            page.run_task(_scroll_to, chat_list, -1.0)
            view_state["after"] = ""
        elif mode == "top":
            page.run_task(_scroll_to, chat_list, 0.0)
            view_state["after"] = ""
        elif mode == "hit":
            key = f"hit-{hits_state['indices'][hits_state['cursor']]}"
            page.run_task(_scroll_key, chat_list, key)
            view_state["after"] = ""

    async def _scroll_to(view: ft.ListView, offset: float) -> None:
        await view.scroll_to(offset=offset, duration=250)

    async def _scroll_key(view: ft.ListView, key: str) -> None:
        await view.scroll_to(scroll_key=key, duration=250)

    def goto_hit(delta: int) -> None:
        """上一条 / 下一条命中：必要时先翻页，再滚到对应气泡。"""
        hits = hits_state["indices"]
        if not hits:
            return
        cur = hits_state["cursor"]
        cur = 0 if cur < 0 else (cur + delta) % len(hits)
        hits_state["cursor"] = cur
        target = hits[cur]
        total = len(view_state["msgs"])
        if target < view_state["start"] or target >= view_state["start"] + PAGE_SIZE:
            view_state["start"] = max(0, min(target - 60, total - PAGE_SIZE))
        view_state["after"] = "hit"
        render_messages()

    def refresh_chat() -> None:
        conv = cdb.get_conversation(current_conv["id"]) if current_conv["id"] else None
        keyword = search_state["keyword"]
        day_from = search_state["date_from"]
        day_to = search_state["date_to"]

        if conv:
            msgs = cdb.search_messages(conv["id"], keyword, day_from, day_to)
            title_input.value = conv.get("name") or ""
            subtitle_input.value = conv.get("subtitle") or ""
            phone_title.value = conv.get("name") or "未命名对话"
            phone_subtitle.value = conv.get("subtitle") or ""
            paint_theme(conv.get("theme") or "lemon")
        else:
            msgs = []
            title_input.value = ""
            subtitle_input.value = ""
            phone_title.value = "聊天长卷"
            phone_subtitle.value = ""
            paint_theme("lemon")

        view_state["msgs"] = msgs
        total = len(msgs)
        if view_state.get("after") == "top":
            view_state["start"] = 0
        else:
            view_state["start"] = max(0, total - PAGE_SIZE)

        # 命中的全局下标（仅关键字）
        kw = keyword.lower()
        hits_state["indices"] = (
            [i for i, m in enumerate(msgs) if kw and kw in (m.get("content") or "").lower()]
            if keyword else [])
        hits_state["cursor"] = -1

        # 右侧消息管理：始终显示该对话最近 MANAGE_CAP 条（不受查找影响）
        msg_list.controls = []
        if conv:
            recent = cdb.list_messages(conv["id"])[-MANAGE_CAP:]
            for msg in recent:
                who = "我" if int(msg.get("side") or 0) == 0 else "对方"
                text = (msg.get("content") or "").replace("\n", " ")
                text = text if len(text) <= 16 else text[:16] + "…"
                msg_list.controls.append(
                    ft.Container(
                        padding=ft.Padding.symmetric(horizontal=9, vertical=7),
                        border_radius=11, bgcolor=theme.CARD_BG,
                        border=ft.Border.all(
                            1, theme.MIST_BLUE if msg["id"] == editing_msg["id"] else theme.LINE),
                        content=ft.Column(spacing=3, controls=[
                            ft.Row(spacing=5, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                   controls=[
                                badge(who, theme.SOFT_LEMON if who == "我" else theme.MIST_BLUE,
                                      theme.TEXT_MAIN if who == "我" else "#FFFFFF", 10),
                                ft.Text(short_date(msg.get("msg_date") or ""), size=9.5,
                                        color=theme.TEXT_SUB),
                                ft.Container(expand=True),
                                ft.IconButton(ft.Icons.ARROW_UPWARD_ROUNDED, icon_size=14,
                                              icon_color=theme.MIST_BLUE_DEEP, width=25, height=25,
                                              padding=0, tooltip="上移", data=msg["id"],
                                              on_click=lambda e: move_message(e.control.data, -1)),
                                ft.IconButton(ft.Icons.ARROW_DOWNWARD_ROUNDED, icon_size=14,
                                              icon_color=theme.MIST_BLUE_DEEP, width=25, height=25,
                                              padding=0, tooltip="下移", data=msg["id"],
                                              on_click=lambda e: move_message(e.control.data, 1)),
                            ]),
                            ft.Row(spacing=4, controls=[
                                ft.Text(text, size=10.5, color=theme.TEXT_MAIN, expand=True,
                                        max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                                ft.IconButton(ft.Icons.EDIT_OUTLINED, icon_size=14,
                                              icon_color=theme.MIST_BLUE_DEEP, width=25, height=25,
                                              padding=0, tooltip=tr("编辑"), data=msg["id"],
                                              on_click=lambda e: edit_message(e.control.data)),
                                ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_size=14,
                                              icon_color=theme.DANGER, width=25, height=25,
                                              padding=0, tooltip=tr("删除"), data=msg["id"],
                                              on_click=lambda e: delete_message(e.control.data)),
                            ]),
                        ]),
                    )
                )
            if not recent:
                msg_list.controls.append(
                    ft.Container(padding=ft.Padding.all(16), alignment=ft.Alignment.CENTER,
                                 content=ft.Text("还没有消息", size=11, color=theme.TEXT_FAINT)))

        rebuild_category_pick((conv or {}).get("category") or "未分类")
        render_messages()

    # ---------------- 导入微信 / QQ 聊天记录 ----------------
    import_text = ft.TextField(
        **FIELD_STYLE, label="粘贴聊天记录",
        hint_text="在微信 / QQ 里选中消息复制后粘贴到这里，也可以直接选择导出的 txt / bak 文件",
        multiline=True, min_lines=7, max_lines=12, height=190,
    )
    import_my_name = ft.TextField(
        **FIELD_STYLE, label="我的昵称（用于区分左右，群聊时建议填写）",
        value="我", height=42,
    )
    import_file_label = ft.Text("未选择文件，可直接粘贴", size=11, color=theme.TEXT_SUB,
                                expand=True)
    import_hint = ft.Text("", size=11.5, color=theme.MIST_BLUE_DEEP, weight=ft.FontWeight.W_600)
    stats_box = ft.Container(visible=False, border_radius=12, padding=12,
                             bgcolor=theme.MINT_GREEN_SOFT,
                             border=ft.Border.all(1, "#BFE3D0"))
    parsed_cache: dict = {"v": []}
    import_mode = {"v": "new"}
    picked_record: dict = {"path": ""}

    mode_group = ft.RadioGroup(
        value="new",
        on_change=lambda e: import_mode.update(v=e.control.value),
        content=ft.Column(spacing=4, controls=[
            ft.Radio(value="new", label="自动新建一段对话（识别到对方昵称时推荐）",
                     label_style=ft.TextStyle(size=12, color=theme.TEXT_MAIN)),
            ft.Radio(value="append", label="追加到当前对话末尾（保留已有消息）",
                     label_style=ft.TextStyle(size=12, color=theme.TEXT_MAIN)),
            ft.Radio(value="replace", label="替换当前对话的全部消息",
                     label_style=ft.TextStyle(size=12, color=theme.TEXT_MAIN)),
        ]),
    )

    def update_stats_view() -> None:
        parsed = parsed_cache["v"]
        if not parsed:
            stats_box.visible = False
            return
        info = imp.summarize(parsed, import_my_name.value or "")
        names = "、".join(info["names"][:6])
        if len(info["names"]) > 6:
            names += f" 等 {len(info['names'])} 人"
        date_range = (f"{info['date_from']} 至 {info['date_to']}"
                      if info["date_from"] else "未识别到日期（按今天记录）")
        stats_box.visible = True
        stats_box.content = ft.Column(spacing=5, controls=[
            ft.Row(spacing=7, controls=[
                ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE, size=15, color="#3F8F66"),
                ft.Text(f"识别成功：{info['count']} 条消息", size=12.5,
                        weight=ft.FontWeight.W_700, color="#2F6B4D"),
            ]),
            ft.Text(f"参与人：{names or '未识别'}", size=11, color=theme.TEXT_MAIN),
            ft.Text(f"对方：{info['peer'] or '未识别'} · 我发 {info['mine']} 条 / "
                    f"对方 {info['other']} 条", size=11, color=theme.TEXT_MAIN),
            ft.Text(f"日期范围：{date_range}", size=11, color=theme.TEXT_MAIN),
        ])

    def parse_preview(e=None) -> None:
        parsed = imp.parse_chat_text(import_text.value or "", import_my_name.value or "")
        parsed_cache["v"] = parsed
        import_hint.value = (f"识别到 {len(parsed)} 条消息，点下方「导入」"
                             if parsed else "没有识别到消息，请检查粘贴格式")
        update_stats_view()
        page.update()

    async def choose_record(e) -> None:
        files = await record_picker.pick_files(
            dialog_title="选择微信 / QQ 导出的聊天记录文件",
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=RECORD_EXTS,
            allow_multiple=False,
        )
        if not files:
            return
        path = files[0].path
        picked_record["path"] = path
        try:
            text = imp.read_chat_file(path)
        except ValueError as exc:
            show_tip(str(exc))
            return
        except OSError as exc:
            show_tip(f"读取文件失败：{exc}")
            return
        import_text.value = text
        import_file_label.value = os.path.basename(path)
        parse_preview()

    def do_import(e=None) -> None:
        parsed = parsed_cache["v"] or imp.parse_chat_text(
            import_text.value or "", import_my_name.value or "")
        if not parsed:
            show_tip("没有识别到消息，检查一下粘贴的格式")
            return

        mode = import_mode["v"]
        conv = cdb.get_conversation(current_conv["id"]) if current_conv["id"] else None
        peer = imp.guess_peer_name(parsed, import_my_name.value or "")

        if mode == "new" or (conv is None and mode != "replace") or (conv is None and peer):
            name = peer
            if not name and picked_record["path"]:
                name = os.path.splitext(os.path.basename(picked_record["path"]))[0]
            conv_id = cdb.add_conversation(
                name or (conv or {}).get("name") or "导入的对话",
                category_filter["v"] if category_filter["v"] != "全部" else "未分类",
            )
            cdb.add_messages_bulk(conv_id, parsed)
            current_conv["id"] = conv_id
        elif mode == "replace":
            if conv is None:
                show_tip("请先在左边选择要替换的对话")
                return
            cdb.clear_messages(conv["id"])
            cdb.add_messages_bulk(conv["id"], parsed)
            conv_id = conv["id"]
        else:        # append
            conv_id = conv["id"]
            cdb.add_messages_bulk(conv_id, parsed)

        count = len(parsed)
        import_text.value = ""
        parsed_cache["v"] = []
        picked_record["path"] = ""
        import_hint.value = ""
        stats_box.visible = False
        close_dialog()
        rebuild_categories()
        reset_search_state(silent=True)
        view_state["after"] = "bottom"
        refresh_conversations()
        show_tip(f"成功导入 {count} 条消息")

    def open_import() -> None:
        import_hint.value = ""
        stats_box.visible = False
        import_file_label.value = (picked_record["path"] or "未选择文件，可直接粘贴")
        mode_group.value = "new"
        import_mode["v"] = "new"
        page.show_dialog(ft.AlertDialog(
            modal=True,
            title=ft.Row(spacing=9, controls=[
                ft.Icon(ft.Icons.FILE_UPLOAD_OUTLINED, color=theme.MIST_BLUE_DEEP, size=20),
                ft.Text("导入微信 / QQ 聊天记录", size=17, weight=ft.FontWeight.BOLD,
                        color=theme.TEXT_MAIN),
            ]),
            bgcolor=theme.CARD_BG,
            shape=ft.RoundedRectangleBorder(radius=18),
            content=ft.Container(
                width=560,
                content=ft.Column(spacing=12, scroll=ft.ScrollMode.ADAPTIVE, height=560,
                                  controls=[
                    ft.Container(
                        padding=11, border_radius=12, bgcolor=theme.MIST_BLUE_SOFT,
                        content=ft.Column(spacing=4, controls=[
                            ft.Row(spacing=7, controls=[
                                ft.Icon(ft.Icons.TIPS_AND_UPDATES_OUTLINED, size=15,
                                        color=theme.MIST_BLUE_DEEP),
                                ft.Text("支持两种方式", size=12, weight=ft.FontWeight.W_700,
                                        color=theme.MIST_BLUE_DEEP),
                            ]),
                            ft.Text("1. 在微信 / QQ 聊天窗口多选消息 → 复制 → 粘贴到下方",
                                    size=11, color=theme.TEXT_MAIN),
                            ft.Text("2. 选择 QQ 导出的记录文件（.txt / .bak 明文，自动识别 GBK 编码、日期行）",
                                    size=11, color=theme.TEXT_MAIN),
                        ]),
                    ),
                    ft.Row(spacing=9, controls=[
                        ft.FilledButton(
                            "选择记录文件", icon=ft.Icons.DESCRIPTION_OUTLINED,
                            bgcolor=theme.MIST_BLUE, color="#FFFFFF", height=36, elevation=0,
                            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
                            on_click=choose_record),
                        import_file_label,
                    ]),
                    import_text,
                    import_my_name,
                    ft.Row(spacing=8, controls=[
                        ft.OutlinedButton(
                            "先解析看看", icon=ft.Icons.PLAY_ARROW,
                            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10),
                                                 color=theme.MIST_BLUE_DEEP),
                            on_click=parse_preview),
                        import_hint,
                    ]),
                    stats_box,
                    mode_group,
                ]),
            ),
            actions=[
                ft.TextButton(tr("取消"), on_click=lambda e: close_dialog()),
                ft.FilledButton(tr("导入"), icon=ft.Icons.FILE_DOWNLOAD_OUTLINED,
                                bgcolor=theme.MIST_BLUE, color="#FFFFFF", elevation=0,
                                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
                                on_click=do_import),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        ))

    # ---------------- 导出 ----------------
    def export_image() -> None:
        conv = cdb.get_conversation(current_conv["id"]) if current_conv["id"] else None
        if not conv:
            show_tip("先选一段对话")
            return
        msgs = cdb.list_messages(conv["id"])       # 导出始终导出完整对话，不受查找影响
        if not msgs:
            show_tip("这段对话还没有消息")
            return

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = "".join(ch for ch in (conv["name"] or "聊天")
                            if ch not in r'\/:*?"<>|').strip() or "聊天"
        save_path = os.path.join(cdb.EXPORT_DIR, f"{safe_name}_{stamp}.png")
        try:
            path = exp.export_chat(conv, msgs, save_path)
        except ImportError:
            show_tip("缺少 Pillow，请在虚拟环境里 pip install Pillow")
            return
        except Exception as exc:
            show_tip(f"导出失败：{exc}")
            return

        export_card.visible = True
        export_preview.visible = True
        export_preview.controls = [
            ft.Row(spacing=8, controls=[
                ft.Icon(ft.Icons.CHECK_CIRCLE, size=16, color="#3F8F66"),
                ft.Text("导出完成", size=13, weight=ft.FontWeight.W_700, color="#2F6B4D"),
            ]),
            ft.Container(
                border_radius=12, border=ft.Border.all(1, theme.LINE),
                clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                content=ft.Image(src=path.replace("\\", "/"), fit=ft.BoxFit.CONTAIN,
                                 width=300, height=220),
            ),
            ft.Row(spacing=8, controls=[
                ft.TextButton("打开所在文件夹", icon=ft.Icons.FOLDER_OPEN,
                              on_click=lambda e: open_folder(cdb.EXPORT_DIR)),
                ft.TextButton("收起预览", icon=ft.Icons.KEYBOARD_ARROW_UP,
                              on_click=lambda e: (setattr(export_preview, "visible", False),
                                                  page.update())),
            ]),
        ]
        page.update()
        show_tip(f"已导出：{path}")

    def open_folder(folder: str) -> None:
        try:
            os.startfile(folder)   # type: ignore[attr-defined]
        except Exception:
            show_tip(f"文件在：{folder}")

    # 初始化
    paint_side()
    rebuild_categories()
    refresh_conversations()

    return ft.Column(spacing=0, expand=True, controls=[
        top_bar,
        ft.Row(spacing=0, expand=True, controls=[left_panel, center_area, right_panel]),
    ])

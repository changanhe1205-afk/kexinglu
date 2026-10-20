"""客行录 · 我的

一页看完三件事：

    1. 数据概览：票根 / 食光 / 旅行 / 影视 各收了多少条
    2. 背景图：三张自带预设 + 上传自己的一张，所有页面共用，点选立即生效
    3. 主题色：5 种预设，作用到各页的主按钮、强调色与选中态

设置写进数据目录的 settings.json / background.json，下次启动保持。
"""

from __future__ import annotations
from i18n import tr

import os

import flet as ft

import cloud_view
import background
import database
import food_db
import storage
import theme
import ticket_db
import travel_db
from theme import card_shadow

THUMB_W, THUMB_H = 152, 92     # 预设缩略图尺寸
CONTENT_W = 900                # 内容区最大宽度，窗口再宽也不会拉散


def _count(fn) -> int:
    """取一个模块的统计数字；某一模块出问题也不该连累整页。"""
    try:
        return int(fn())
    except Exception:
        return 0


def _stats() -> list[tuple[str, str, int, str]]:
    """(图标, 名称, 数量, 主色)：四个模块各一块。"""
    try:
        database.init_db()        # 影视库平时由 movie_view 建，这里兜个底
    except Exception:
        pass
    return [
        (ft.Icons.CONFIRMATION_NUMBER_OUTLINED, "旅程票根",
         _count(lambda: ticket_db.stats()["trips"]), theme.MIST_BLUE_DEEP),
        (ft.Icons.RESTAURANT_OUTLINED, "食光小记",
         _count(lambda: food_db.stats()["total"]), "#C98A5B"),
        (ft.Icons.LUGGAGE_OUTLINED, "旅行日志",
         _count(lambda: travel_db.stats()["total"]), "#5F9E86"),
        (ft.Icons.MOVIE_FILTER_OUTLINED, "影视收藏",
         _count(lambda: database.stats()["total"]), "#8E7CC3"),
    ]


def build(page: ft.Page, on_theme_change=None,
          on_background_change=None) -> ft.Control:
    """我的。on_theme_change() 主题色变了；on_background_change() 背景图变了。"""

    def show_tip(msg: str) -> None:
        page.show_dialog(theme.toast(ft.Text(msg, size=12.5, color="#FFFFFF"),
                                     bgcolor=theme.MIST_BLUE_DEEP))

    def head(icon: str, title: str, subtitle: str, trailing=None) -> ft.Row:
        """卡片标题：图标徽章 + 标题 + 说明 +（可选）右侧控件。"""
        parts: list[ft.Control] = [
            ft.Container(width=38, height=38, border_radius=12,
                         bgcolor=theme.with_alpha(theme.ACCENT, 0.13),
                         alignment=ft.Alignment.CENTER,
                         content=ft.Icon(icon, size=19, color=theme.ACCENT)),
            ft.Column(spacing=1, expand=True, controls=[
                ft.Text(title, size=15, weight=ft.FontWeight.W_700,
                        color=theme.TEXT_MAIN),
                ft.Text(subtitle, size=11, color=theme.TEXT_SUB),
            ]),
        ]
        if trailing is not None:
            parts.append(trailing)
        return ft.Row(spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                      controls=parts)

    def chip(text: str) -> ft.Container:
        """小信息药丸：当前背景名、数据位置之类。"""
        return ft.Container(
            padding=ft.Padding.symmetric(horizontal=11, vertical=5),
            border_radius=13, bgcolor=theme.CARD_GLASS_SOFT,
            border=ft.Border.all(1, theme.CARD_GLASS_LINE),
            content=ft.Text(text, size=11, color=theme.TEXT_SUB),
        )

    stats = _stats()
    total = sum(s[2] for s in stats)

    # ---------------- 概览 ----------------
    def stat_tile(icon: str, label: str, value: int, color: str) -> ft.Container:
        return ft.Container(
            expand=True,
            padding=ft.Padding.symmetric(horizontal=14, vertical=13),
            border_radius=15, bgcolor=theme.CARD_GLASS_SOFT,
            border=ft.Border.all(1, theme.CARD_GLASS_LINE),
            content=ft.Column(spacing=8, controls=[
                ft.Row(spacing=7, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                       controls=[
                    ft.Container(width=26, height=26, border_radius=9,
                                 bgcolor=theme.with_alpha(color, 0.15),
                                 alignment=ft.Alignment.CENTER,
                                 content=ft.Icon(icon, size=14, color=color)),
                    ft.Text(label, size=11.5, color=theme.TEXT_SUB),
                ]),
                ft.Text(str(value), size=27, weight=ft.FontWeight.W_800,
                        color=theme.TEXT_MAIN),
            ]),
        )

    hero = theme.glass_card(
        ft.Row(spacing=16, vertical_alignment=ft.CrossAxisAlignment.CENTER,
               controls=[
            theme.brand_mark(62),
            ft.Column(spacing=3, expand=True, controls=[
                ft.Text(tr("客行录"), size=23, weight=ft.FontWeight.W_800,
                        color=theme.TEXT_MAIN),
                ft.Text("把走过看过的都收进来 · 内容只留在本机", size=11.5,
                        color=theme.TEXT_SUB),
            ]),
            chip(f"共 {total} 条珍藏"),
        ]),
        ft.Row(spacing=12, controls=[stat_tile(*s) for s in stats]),
        padding=22, spacing=16,
    )

    # ---------------- 背景图 ----------------
    bg_pick = ft.FilePicker()
    bg_pick.data = "profile_background"
    if not any(getattr(s, "data", None) == "profile_background"
               for s in page.services):
        page.services.append(bg_pick)

    def apply_background(msg: str) -> None:
        """通知外壳换图并重建这一块（选中框要跟着变）。"""
        if on_background_change:
            on_background_change()
        paint_bg()
        show_tip(msg)

    async def pick_background(e=None) -> None:
        files = await bg_pick.pick_files(
            dialog_title="选一张当背景", file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=background.PICK_EXT, allow_multiple=False)
        if not files:
            return
        if background.set_custom(files[0].path):
            apply_background("背景已换成你上传的这张")
        else:
            show_tip("这张图读不进来，换一张试试")

    def reset_background(e=None) -> None:
        background.reset()
        apply_background("背景已恢复跟随主题")

    def pick_preset(rel: str, name: str) -> None:
        if background.set_preset(rel):
            apply_background(f"背景已切换为「{name}」")

    bg_chip = chip("")
    bg_row = ft.Row(spacing=14, wrap=True)
    restore_btn = ft.TextButton("恢复默认", icon=ft.Icons.RESTORE_OUTLINED,
                                height=40,
                                style=ft.ButtonStyle(color=theme.TEXT_SUB),
                                on_click=reset_background)

    def preset_thumb(name: str, rel: str) -> ft.Container:
        """预设缩略图：底图 + 压暗渐变 + 名称，选中的那张带主题色描边和勾。"""
        active = background.preset_src(rel) == background.current()
        return ft.Container(
            width=THUMB_W, height=THUMB_H, border_radius=16, ink=True,
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            border=ft.Border.all(2.5 if active else 1,
                                 theme.ACCENT if active else theme.CARD_GLASS_LINE),
            shadow=card_shadow() if active else None,
            on_click=lambda e, r=rel, n=name: pick_preset(r, n),
            content=ft.Stack(controls=[
                ft.Image(src=background.preset_src(rel), width=THUMB_W,
                         height=THUMB_H, fit=ft.BoxFit.COVER),
                ft.Container(
                    expand=True,
                    gradient=ft.LinearGradient(
                        begin=ft.Alignment.TOP_CENTER,
                        end=ft.Alignment.BOTTOM_CENTER,
                        colors=["#00000000", "#000000A6"])),
                ft.Container(
                    alignment=ft.Alignment.BOTTOM_LEFT,
                    padding=ft.Padding.only(left=11, bottom=9),
                    content=ft.Row(spacing=6, tight=True, controls=[
                        ft.Text(name, size=12.5, color="#FFFFFF",
                                weight=ft.FontWeight.W_700),
                        ft.Text("使用中", size=9.5, color="#D9FFFFFF",
                                visible=active),
                    ])),
                ft.Container(
                    alignment=ft.Alignment.TOP_RIGHT, visible=active,
                    padding=ft.Padding.only(right=8, top=8),
                    content=ft.Icon(ft.Icons.CHECK_CIRCLE, size=19,
                                    color="#FFFFFF")),
            ]),
        )

    def paint_bg() -> None:
        """重画预设缩略图，当前的那张加主题色边框。"""
        bg_row.controls = [preset_thumb(name, rel)
                           for name, rel in background.PRESETS]
        bg_chip.content.value = f"当前：{background.current_name()}"
        restore_btn.visible = background.is_custom()

    paint_bg()

    bg_card = theme.glass_card(
        head(ft.Icons.WALLPAPER_OUTLINED, tr("背景图"),
             "所有页面共用同一张，换完立刻生效", bg_chip),
        bg_row,
        ft.Row(spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER,
               controls=[
            ft.FilledButton(
                "上传一张", icon=ft.Icons.IMAGE_OUTLINED,
                bgcolor=theme.ACCENT, color=theme.ON_ACCENT, height=40, elevation=0,
                style=ft.ButtonStyle(
                    shape=ft.RoundedRectangleBorder(radius=12)),
                on_click=pick_background),
            restore_btn,
            ft.Container(expand=True),
            ft.Text("png / jpg / webp / bmp", size=10.5, color=theme.TEXT_FAINT),
        ]),
        padding=22, spacing=16,
    )

    # ---------------- 完整外观主题 ----------------
    def pick_theme(preset: str) -> None:
        theme.set_theme(preset=preset)
        background.follow_theme()
        if on_theme_change:
            on_theme_change()
        else:
            page.update()

    def theme_tile(key: str, palette: dict) -> ft.Container:
        active = theme.THEME_ID == key
        return ft.Container(
            width=230, padding=12, border_radius=14, tooltip="应用主题：" + palette["name"],
            bgcolor=theme.CARD_BG_SOFT,
            border=ft.Border.all(1.5 if active else 1, theme.ACCENT if active else theme.LINE),
            on_click=lambda e, k=key: pick_theme(k),
            content=ft.Column(spacing=10, controls=[
                ft.Container(height=58, border_radius=9, padding=12, bgcolor=palette["bg"],
                    content=ft.Row(spacing=10, controls=[
                        ft.Container(width=36, height=50, border_radius=6, bgcolor=palette["card"],
                            content=ft.Column(spacing=5, controls=[
                                ft.Container(height=5, width=20, bgcolor=palette["accent"], border_radius=2),
                                ft.Container(height=4, width=20, bgcolor=palette["line"], border_radius=2),
                            ]), padding=8),
                        ft.Container(expand=True, content=ft.Column(spacing=7, controls=[
                            ft.Container(height=6, width=80, bgcolor=palette["text"], border_radius=3),
                            ft.Container(height=4, width=110, bgcolor=palette["line"], border_radius=2),
                            ft.Container(height=15, width=44, bgcolor=palette["accent"], border_radius=4),
                        ])),
                    ])),
                ft.Row(controls=[
                    ft.Text(palette["name"], size=12, color=theme.TEXT_MAIN, expand=True),
                    ft.Icon(ft.Icons.CHECK_CIRCLE if active else ft.Icons.CIRCLE_OUTLINED,
                            size=17, color=theme.ACCENT if active else theme.TEXT_FAINT),
                ]),
            ]))

    theme_card = theme.glass_card(
        head(ft.Icons.PALETTE_OUTLINED, "外观主题", "整套切换背景、卡片、文字、表单和导航"),
        ft.Row(wrap=True, spacing=12, run_spacing=12,
               controls=[theme_tile(k, p) for k, p in theme.THEMES.items()]),
        ft.Text("选择后立即生效并记住；首页背景也会跟随，可在下方单独更换。",
                size=11, color=theme.TEXT_SUB),
        padding=22, spacing=16,
    )

    # ---------------- 关于 ----------------
    def info_row(icon: str, label: str, value: str, trailing=None) -> ft.Row:
        parts: list[ft.Control] = [
            ft.Container(width=32, height=32, border_radius=10,
                         bgcolor=theme.CARD_GLASS_SOFT,
                         border=ft.Border.all(1, theme.CARD_GLASS_LINE),
                         alignment=ft.Alignment.CENTER,
                         content=ft.Icon(icon, size=16, color=theme.TEXT_SUB)),
            ft.Column(spacing=1, expand=True, controls=[
                ft.Text(label, size=10.5, color=theme.TEXT_FAINT),
                ft.Text(value, size=12.5, color=theme.TEXT_MAIN,
                        max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
            ]),
        ]
        if trailing is not None:
            parts.append(trailing)
        return ft.Row(spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                      controls=parts)

    data_dir = storage.current_dir()

    def open_data_dir(e=None) -> None:
        """在资源管理器里打开数据目录，方便自己备份 / 清理。"""
        try:
            from platform_files import open_local
            open_local(storage.current_dir())
        except OSError:
            show_tip(f"打不开目录，路径是：{data_dir}")

    # ---------------- 数据存储位置 ----------------
    dir_picker = ft.FilePicker()
    dir_picker.data = "data_dir_picker"
    if not any(getattr(s, "data", None) == "data_dir_picker"
               for s in page.services):
        page.services.append(dir_picker)

    path_text = ft.Text(data_dir, size=11.5, color=theme.TEXT_MAIN,
                        max_lines=2, overflow=ft.TextOverflow.ELLIPSIS,
                        selectable=True)
    size_text = ft.Text("", size=10.5, color=theme.TEXT_FAINT)
    env_text = ft.Text("", size=10.5, color=theme.TEXT_FAINT)
    move_btn = ft.FilledButton(
        "更换位置", icon=ft.Icons.DRIVE_FILE_MOVE_OUTLINED, height=36,
        bgcolor=theme.ACCENT, color=theme.ON_ACCENT, elevation=0,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=11)))

    def _dir_size(path: str) -> tuple[int, int]:
        """(文件数, 总字节)。"""
        n = total = 0
        for root, _dirs, files in os.walk(path):
            for f in files:
                try:
                    total += os.path.getsize(os.path.join(root, f))
                    n += 1
                except OSError:
                    pass
        return n, total

    def paint_storage() -> None:
        cur = storage.current_dir()
        path_text.value = cur
        n, total = _dir_size(cur)
        mb = total / 1024 / 1024
        size_text.value = (f"{n} 个文件 · {mb:.1f} MB"
                           if mb < 1024 else
                           f"{n} 个文件 · {mb / 1024:.2f} GB")
        env_text.value = ("正在使用默认位置" if storage.is_default()
                          else "已改到自定义位置")
        page.update()

    def _do_move(target: str) -> None:
        ok, msg = storage.migrate(target)
        if not ok:
            show_tip(msg)
            page.update()
            return
        # migrate 里已经 reload 过各模块，路径立刻生效，卡片马上显示新地址
        paint_storage()
        page.update()
        show_tip("已切换到新位置")
        page.show_dialog(ft.AlertDialog(
            modal=True,
            title=ft.Text("数据已搬到新位置", size=16,
                          weight=ft.FontWeight.W_700),
            content=ft.Column(spacing=10, tight=True, width=430, controls=[
                ft.Container(
                    padding=11, border_radius=10, bgcolor=theme.CARD_GLASS_SOFT,
                    border=ft.Border.all(1, theme.CARD_GLASS_LINE),
                    content=ft.Text(storage.current_dir(), size=11,
                                    color=theme.TEXT_MAIN, selectable=True)),
                ft.Text(msg, size=11, color=theme.TEXT_SUB),
                ft.Text("已经生效，不用重启。原来的文件夹我留着没删，"
                        "确认新位置没问题之后可以自己清理。",
                        size=11, color=theme.TEXT_FAINT),
            ]),
            actions=[
                ft.FilledButton(tr("知道了"), icon=ft.Icons.CHECK,
                                bgcolor=theme.ACCENT, color=theme.ON_ACCENT,
                                style=ft.ButtonStyle(
                                    shape=ft.RoundedRectangleBorder(radius=10)),
                                on_click=lambda e: page.pop_dialog()),
            ],
            actions_alignment=ft.MainAxisAlignment.END))

    def _show_confirm(full: str) -> None:
        """弹确认框。

        注意：Flet 1.x 里弹窗**必须**用 page.show_dialog() 打开，
        光设 dialog.open = True 是弹不出来的；而且 pop_dialog() 不会把它
        从弹窗栈里摘掉，所以同一个 AlertDialog 对象不能复用，每次都要新建。
        """
        n, total = _dir_size(storage.current_dir())
        has = storage.has_data(full)

        def do_it(e=None) -> None:
            page.pop_dialog()
            _do_move(full)

        page.show_dialog(ft.AlertDialog(
            modal=True,
            title=ft.Text("更换数据存储位置", size=16,
                          weight=ft.FontWeight.W_700),
            content=ft.Column(spacing=10, tight=True, width=430, controls=[
                ft.Text(f"把现在的数据（{n} 个文件 · "
                        f"{total / 1024 / 1024:.1f} MB）复制到：",
                        size=12, color=theme.TEXT_SUB),
                ft.Container(
                    padding=11, border_radius=10, bgcolor=theme.CARD_GLASS_SOFT,
                    border=ft.Border.all(1, theme.CARD_GLASS_LINE),
                    content=ft.Text(full, size=11, color=theme.TEXT_MAIN,
                                    selectable=True)),
                ft.Text("这个文件夹里已经有一份客行录的数据，它会被改名成 "
                        ".bak 留档，然后被现在的数据替换掉。" if has else
                        "复制完成后立刻生效，不用重启；原文件夹保留不删。",
                        size=11, color=theme.DANGER if has else theme.TEXT_FAINT),
            ]),
            actions=[
                ft.TextButton(tr("取消"), on_click=lambda e: page.pop_dialog()),
                ft.FilledButton("开始复制",
                                icon=ft.Icons.CONTENT_COPY_OUTLINED,
                                bgcolor=theme.ACCENT, color=theme.ON_ACCENT,
                                style=ft.ButtonStyle(
                                    shape=ft.RoundedRectangleBorder(radius=10)),
                                on_click=do_it),
            ],
            actions_alignment=ft.MainAxisAlignment.END))

    def pick_dir(e=None) -> None:
        page.run_task(_pick_dir_task)

    async def _pick_dir_task() -> None:
        path = await dir_picker.get_directory_path(
            dialog_title="选一个文件夹来存放客行录的数据")
        if not path:
            return
        full = os.path.join(path, "客行录数据")
        if storage.check(full):
            # 用户可能就想直接放在选中的这个文件夹里
            if storage.check(path):
                show_tip(storage.check(full))
                return
            full = path
        _show_confirm(full)

    move_btn.on_click = pick_dir

    storage_card = theme.glass_card(
        head(ft.Icons.STORAGE_OUTLINED, tr("数据存储位置"),
             "记录、照片都放在这个文件夹里，可以搬到别的盘"),
        ft.Container(
            padding=13, border_radius=12, bgcolor=theme.CARD_GLASS_SOFT,
            border=ft.Border.all(1, theme.CARD_GLASS_LINE),
            content=ft.Column(spacing=5, tight=True, controls=[
                ft.Row(spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                       controls=[
                    ft.Icon(ft.Icons.FOLDER_OUTLINED, size=16,
                            color=theme.MIST_BLUE_DEEP),
                    ft.Text(tr("当前位置"), size=10.5, color=theme.TEXT_FAINT),
                    ft.Container(expand=True),
                    env_text,
                ]),
                path_text,
                size_text,
            ])),
        ft.Row(spacing=10, controls=[
            move_btn,
            ft.TextButton(tr("打开文件夹"), icon=ft.Icons.OPEN_IN_NEW, height=36,
                          on_click=open_data_dir),
            ft.TextButton(tr("恢复默认位置"), icon=ft.Icons.SETTINGS_BACKUP_RESTORE,
                          height=36,
                          on_click=lambda e: _do_move(
                              storage.default_data_dir())),
        ]),
        padding=22, spacing=14,
    )

    about_card = theme.glass_card(
        head(ft.Icons.INFO_OUTLINE, tr("关于"), tr("客行录 · 本地珍藏")),
        info_row(ft.Icons.FOLDER_OPEN_OUTLINED, tr("数据目录"),
                 storage.current_dir(),
                 ft.TextButton(tr("打开"), icon=ft.Icons.OPEN_IN_NEW,
                               style=ft.ButtonStyle(color=theme.ACCENT),
                               on_click=open_data_dir)),
        info_row(ft.Icons.STORAGE_OUTLINED, tr("已收藏"),
                 f"票根 {stats[0][2]} · 食光 {stats[1][2]} · "
                 f"旅行 {stats[2][2]} · 影视 {stats[3][2]}"),
        ft.Text(tr("未开启云同步时，记录只保存在这台电脑上。"), size=10.5,
                color=theme.TEXT_FAINT),
        padding=22, spacing=14,
    )

    paint_storage()

    from i18n import LANGUAGES
    import config
    def change_language(e):
        config.set('language',e.control.value)
        if on_theme_change: on_theme_change()
    language_card=theme.glass_card(ft.Dropdown(
        label='语言 / Language',value=config.get('language','zh'),
        options=[ft.DropdownOption(key=code,text=name) for code,name in LANGUAGES.items()],
        on_select=change_language),padding=22)

    body = ft.Container(
        expand=True,
        content=ft.ListView(
            expand=True, spacing=0,
            padding=ft.Padding.only(left=24, right=24, top=22, bottom=20),
            controls=[ft.Row(
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.START,
                controls=[ft.Column(width=CONTENT_W, spacing=16,
                                    controls=[hero, cloud_view.build(page), language_card, theme_card, bg_card,
                                              storage_card, about_card])])],
        ),
    )

    return body

"""客行录 · 程序入口

这里只负责：窗口设置 + 底部导航 + 内容区切换。
各模块各自独立实现：
    ticket_view.py → 旅程票根
    food_view.py   → 食光小记
    travel_view.py → 旅行日志
    movie_view.py  → 影视收藏
"""

from __future__ import annotations

import os
import sys

from runtime_bootstrap import configure_desktop_runtime
configure_desktop_runtime()

# Python 3.15 预览版上，msgpack 的 C 扩展会报
# "module msgpack._cmsgpack uses unknown slot ID 84"，强制走纯 Python 实现。
# 用 3.14 / 3.13 正式版时这段不会生效，可以直接删掉。
if sys.version_info >= (3, 15):
    os.environ["MSGPACK_PUREPYTHON"] = "1"

import desktop_identity
import flet as ft
from flet.controls.core.animated_switcher import (
    AnimatedSwitcher,
    AnimatedSwitcherTransition,
)

import background
import food_view
import home_view
import movie_view
import profile_view
import theme
import ticket_view
import travel_view

PAGES = [("首页", ft.Icons.HOME_ROUNDED),
         ("旅行日志", ft.Icons.LUGGAGE_OUTLINED),
         ("旅程票根", ft.Icons.FLIGHT_TAKEOFF),
         ("食光小记", ft.Icons.RESTAURANT_OUTLINED),
         ("影视收藏", ft.Icons.MOVIE_FILTER_OUTLINED),
         ("我的", ft.Icons.PERSON_OUTLINED)]
MODULE_BUILDERS = [travel_view.build, ticket_view.build, food_view.build,
                   movie_view.build]


def main(page: ft.Page) -> None:
    page.title = "客行录"
    page.bgcolor = theme.BG
    page.padding = 0
    page.theme_mode = ft.ThemeMode.DARK if theme.DARK else ft.ThemeMode.LIGHT
    page.theme = theme.app_theme()
    page.dark_theme = theme.app_theme()
    page.window.width = 1320
    page.window.height = 900
    page.window.min_width = 1080
    page.window.min_height = 700
    from desktop_window import DesktopWindow
    native_window = DesktopWindow(page)
    page.desktop_window = native_window
    # 任务栏 / 标题栏显示自己的图标（否则会显示 flet 运行时的默认 logo）
    try:
        page.window.icon = theme.res("assets/" + desktop_identity.ICON_NAME)
    except Exception:
        pass

    current: dict = {"index": 0}          # 当前页序号
    travel_cache = {}
    content = AnimatedSwitcher(           # 内容区：切页时淡入淡出
        ft.Container(expand=True),
        expand=True, transition=AnimatedSwitcherTransition.FADE,
        duration=320, reverse_duration=180,
        switch_in_curve=ft.AnimationCurve.EASE_OUT,
        switch_out_curve=ft.AnimationCurve.EASE_IN,
    )

    def build_page(index: int) -> ft.Control:
        current["resize"] = None
        if index == 0:
            return home_view.build(page, on_navigate=switch_to)
        if index == len(PAGES) - 1:
            return profile_view.build(page, on_theme_change=repaint_theme,
                                      on_background_change=repaint_background)
        descriptions = ["地点、照片与旅行记录", "收藏行程 · 设计票面",
                        "饮食、店铺与日常记录", "让散场之后的感受，有处可留。"]
        if index == 1:
            if "body" not in travel_cache:
                travel_cache["body"] = travel_view.build(page)
            body = travel_cache["body"]
        else:
            body = MODULE_BUILDERS[index - 1](page)
        if isinstance(body.data, dict):
            current["resize"] = body.data.get("on_resize")
            current["hide"] = body.data.get("on_hide")
            if body.data.get("on_show"):
                body.data["on_show"]()
        return theme.module_frame(PAGES[index][0], descriptions[index - 1],
                                  PAGES[index][1], body)

    def repaint_theme() -> None:
        """主题变更后：窗口底色 / 背景渐变 / 弹窗配色 / 当前页全部刷新。"""
        travel_cache.clear()
        page.bgcolor = theme.BG
        page.theme = theme.app_theme()
        page.dark_theme = theme.app_theme()
        page.theme_mode = ft.ThemeMode.DARK if theme.DARK else ft.ThemeMode.LIGHT
        veil.bgcolor = theme.VEIL
        home_shade.gradient.colors = theme.HOME_SHADE
        app_bg.image = ft.DecorationImage(src=background.current(), fit=ft.BoxFit.COVER)
        bg_layer.gradient.colors = [theme.BG, theme.BG_DEEP]
        switch_to(current["index"])      # 重建当前页，应用新主题

    # --- 背景图层：铺满整个窗口，所有页面共用一张背景图 --- # noqa: E501
    app_bg = ft.Container(
        left=0, right=0, top=0, bottom=0,
        image=ft.DecorationImage(src=background.current(), fit=ft.BoxFit.COVER),
    )

    # --- 柔化纱罩：首页以外都在背景图上盖一层浅色磨砂 ---
    # 背景图是深色的，浅色卡片直接压上去会像浮在黑板上；加一层纱罩后
    # 背景退成柔和的色调，卡片的描边、阴影和正文对比度才立得住。
    # 首页保留原图，继续做沉浸式的深色玻璃面板。
    veil = ft.Container(
        left=0, right=0, top=0, bottom=0, visible=False,
        bgcolor=theme.VEIL, blur=ft.Blur(theme.VEIL_BLUR, theme.VEIL_BLUR),
    )
    home_shade = ft.Container(
        left=0, right=0, top=0, bottom=0,
        gradient=ft.LinearGradient(begin=ft.Alignment.TOP_CENTER,
                                   end=ft.Alignment.BOTTOM_CENTER,
                                   colors=theme.HOME_SHADE),
    )

    def repaint_background() -> None:
        """用户在首页换了背景图：换成新的那张（所有页面一起变）。"""
        app_bg.image = ft.DecorationImage(src=background.current(),
                                          fit=ft.BoxFit.COVER)
        page.update()

    # --- 底部全局导航（磨砂药丸，悬浮在背景之上，固定在窗口最下方）---
    def switch_to(index: int) -> None:
        """切换页面：重新构建对应模块的界面放进内容区。"""
        if current.get("hide"):
            current.pop("hide")()
        # Map tiles remain cached; avoid fading a heavy map in/out across two layers.
        content.duration = 0 if index == 1 or current["index"] == 1 else 180
        content.reverse_duration = content.duration
        current["index"] = index
        paint_nav()
        layout_nav(index)
        content.content = build_page(index)
        veil.visible = index != 0        # 首页不用纱罩，其余页都盖上
        home_shade.visible = index == 0
        paint_chrome()                   # 顶栏按钮跟着深 / 浅页换色
        page.update()

    def make_nav_item(idx: int, name: str, icon_name: str) -> ft.Container:
        # 不开 ink：点下去不要那圈高光/水波纹，滑动的毛玻璃块本身就是反馈
        return ft.Container(
            expand=True, ink=False, border_radius=19, tooltip=name,
            on_click=lambda e, i=idx: switch_to(i),
            on_hover=lambda e, i=idx: hover_nav(i, e.data == "true"),
            content=ft.Column(
                spacing=3, alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER, controls=[
                    ft.Icon(icon_name, size=22),
                    ft.Text(name, size=11),
                ]),
        )

    nav_items = {
        idx: make_nav_item(idx, name, icon_name)
        for idx, (name, icon_name) in enumerate(PAGES)
    }
    nav_hover: dict[int, bool] = {idx: False for idx in nav_items}

    # 首页是深色底：导航用深色玻璃 + 白字；其余页是浅色纱罩，
    # 导航跟着换成浅色玻璃，选中项用主题色，不再是硬邦邦的一条黑。
    def paint_nav() -> None:
        dark = current["index"] == 0
        accent = theme.ACCENT
        dock.bgcolor = theme.DOCK_HOME if dark else theme.GLASS_BAR
        dock.border = ft.Border.all(1, theme.HOME_LINE if dark else theme.LINE)
        dock.shadow = ft.BoxShadow(
            blur_radius=30, spread_radius=-10, offset=ft.Offset(0, 12),
            color=theme.SHADOW_DEEP)
        nav_indicator.bgcolor = (theme.with_alpha(theme.HOME_ACCENT, .22) if dark
                                 else theme.with_alpha(accent, 0.13))
        nav_indicator.border = ft.Border.all(
            1, "#3DFFFFFF" if dark else theme.with_alpha(accent, 0.45))

        for idx, item in nav_items.items():
            on = idx == current["index"]
            hover = nav_hover.get(idx, False)
            if on:
                color = theme.HOME_TEXT if dark else accent
            elif dark:
                color = theme.HOME_TEXT if hover else theme.HOME_SUB
            else:
                color = theme.TEXT_MAIN if hover else theme.TEXT_SUB
            item.content.controls[0].color = color
            item.content.controls[1].color = color
            item.content.controls[1].weight = (ft.FontWeight.W_700 if on
                                               else ft.FontWeight.W_500)

    def hover_nav(idx: int, on: bool) -> None:
        if nav_hover.get(idx) == on:
            return
        nav_hover[idx] = on
        paint_nav()
        page.update()

    # 选中的那一格：一块透明毛玻璃，切换页面时平滑滑过去（iOS 风格）
    nav_indicator = ft.Container(
        left=0, top=5, bottom=5, width=0,
        bgcolor="#2EFFFFFF", blur=ft.Blur(18, 18),
        border=ft.Border.all(1, "#3DFFFFFF"), border_radius=19,
        animate_position=ft.Animation(320, ft.AnimationCurve.EASE_OUT_CUBIC),
    )
    dock = ft.Container(
        width=780, height=72, border_radius=28,
        bgcolor=theme.DOCK_HOME, blur=ft.Blur(30, 30),
        border=ft.Border.all(1, "#1FFFFFFF"),
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        content=ft.Stack(controls=[
            nav_indicator,
            ft.Container(left=0, right=0, top=0, bottom=0,
                         content=ft.Row(spacing=0,
                                        controls=list(nav_items.values()))),
        ]),
    )

    def layout_nav(index: int) -> None:
        """把毛玻璃滑块挪到当前导航项下面；窗口尺寸变了也要重算。"""
        total = min(780, max(320, (page.width or page.window.width or 1320) - 48))
        dock.width = total
        item = total / len(PAGES)
        nav_indicator.width = item - 8
        nav_indicator.left = index * item + 4

    def on_resize(e=None) -> None:
        native_window.resize()
        layout_nav(current["index"])
        if current.get("resize"):
            current["resize"]()
        page.update()

    page.on_resize = on_resize

    # ---------------- 自定义标题栏 ----------------
    # 隐藏系统标题栏（去掉顶上那行"图标 + 客行录"），自己画一条能拖动的顶栏，
    # 只保留最小化 / 最大化 / 关闭三个按钮。
    page.window.title_bar_hidden = True

    win = {"max": False, "hover": None}

    def chrome_colors(close: bool = False, hover: bool = False):
        dark = current["index"] == 0
        if close and hover:
            return "#E81123", "#FFFFFF"
        if close:
            return "#00000000", (theme.HOME_SUB if dark else theme.TEXT_SUB)
        if hover:
            return ("#26FFFFFF" if dark else "#14000000",
                    theme.HOME_TEXT if dark else theme.TEXT_MAIN)
        return "#00000000", (theme.HOME_SUB if dark else theme.TEXT_SUB)

    def _win_btn(name: str, icon: str, on_click, close: bool = False
                 ) -> ft.Container:
        def on_hover(e) -> None:
            on = e.data == "true"
            win["hover"] = name if on else None
            bg, fg = chrome_colors(close, on)
            e.control.bgcolor = bg
            e.control.content.color = fg
            e.control.update()

        return ft.Container(
            width=44, height=30, border_radius=8, alignment=ft.Alignment.CENTER,
            bgcolor="#00000000", ink=False, on_hover=on_hover, on_click=on_click,
            content=ft.Icon(icon, size=14, color="#9FB0C4"))

    def do_min(e=None) -> None:
        page.window.minimized = True
        page.update()

    def do_max(e=None) -> None:
        win["max"] = not win["max"]
        page.window.maximized = win["max"]
        max_btn.content.icon = (ft.Icons.FILTER_NONE if win["max"]
                                else ft.Icons.CROP_SQUARE)
        page.update()

    def do_close(e=None) -> None:
        # 注意：Flet 1.x 里 Window.close() 是 async 的，
        # 直接调用只会拿到一个协程、窗口不会关，必须丢进事件循环。
        page.run_task(page.window.close)

    max_btn = _win_btn("max", ft.Icons.CROP_SQUARE, do_max)
    chrome_btns = [
        _win_btn("min", ft.Icons.REMOVE, do_min),
        max_btn,
        _win_btn("close", ft.Icons.CLOSE, do_close, close=True),
    ]

    brand_label = ft.Text("客行录", size=12, weight=ft.FontWeight.W_600)
    brand_icon = theme.brand_mark(22)
    title_brand = ft.Row(spacing=8, controls=[brand_icon, brand_label])
    title_strip = ft.WindowDragArea(
        maximizable=True, height=44,
        content=ft.Row(spacing=0, alignment=ft.MainAxisAlignment.END,
                       vertical_alignment=ft.CrossAxisAlignment.CENTER,
                       controls=[ft.Container(width=20),
                                 title_brand,
                                 ft.Container(expand=True),
                                 *chrome_btns, ft.Container(width=8)]),
    )

    def paint_chrome() -> None:
        """跟随深 / 浅页面切换按钮配色。"""
        brand_label.color = theme.HOME_TEXT if current["index"] == 0 else theme.TEXT_MAIN
        title_brand.visible = current["index"] not in (0, len(PAGES) - 1)
        brand_icon.color = theme.ACCENT
        for b in chrome_btns:
            close = b is chrome_btns[-1]
            b.content.color = chrome_colors(close, win["hover"] ==
                                            ("close" if close else
                                             "max" if b is max_btn else "min"))[1]
            b.bgcolor = "#00000000"


    bar_bg = ft.Container(
        height=98, bgcolor="#00000000",   # 透明留白让导航形成独立浮岛
        alignment=ft.Alignment.CENTER,
        padding=ft.Padding.only(left=24, right=24, bottom=16, top=10),
        content=dock,
    )

    # 底层：主题背景渐变（首页自身为深色，会盖住它）
    bg_layer = ft.Container(
        left=0, right=0, top=0, bottom=0,
        gradient=ft.LinearGradient(
            begin=ft.Alignment.TOP_LEFT, end=ft.Alignment.BOTTOM_RIGHT,
            colors=[theme.BG, theme.BG_DEEP]),
    )

    page.add(ft.Stack(expand=True, controls=[
        bg_layer,
        app_bg,
        home_shade,
        veil,
        ft.Container(left=0, right=0, top=0, bottom=0,
                     content=ft.Column(spacing=0, expand=True,
                                       controls=[title_strip, content, bar_bg])),
    ]))

    # 默认打开首页
    switch_to(0)
    page.startup_window_task = page.run_task(native_window.initialize)


if __name__ == "__main__":
    ft.run(main)   # flet 1.x 的启动入口

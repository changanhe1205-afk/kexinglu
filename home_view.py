"""客行录 · 首页（全屏背景 + 磨砂悬浮面板）

背景图由 main.py 铺满整个窗口（换背景的入口在「我的」页），
这一页只负责浮在上面的面板：

    ┌─ 左栏：三张独立磨砂卡片 ──────────────────────────────┐
    │   1. 时钟（最大）+ 日期（小一号）                       │
    │   2. 天气                                              │
    │   3. 每日一句                                          │
    └──────────────────────────────────────────────────────┘
    ┌─ 右侧：多组独立磨砂卡片模块，每组横向滚动 ─────────────┐
    │   旅程票根 / 旅行记录相册 / 食光小记                      │
    └──────────────────────────────────────────────────────┘

居中时钟、天气和语录，以及四个可跳转的模块入口。
"""

from __future__ import annotations
from i18n import tr

import asyncio
from datetime import datetime

import flet as ft

import quotes
import theme
import weather

# 首页使用独立的深色玻璃令牌，由当前完整主题派生。
RADIUS = 20

# 每次重建首页自增；旧的秒级循环发现自己过期后自动退出
_GEN = {"v": 0}


def glass(radius: float = RADIUS, bg: str | None = None, shadow: bool = True,
          **over) -> dict:
    """磨砂面板通用参数：半透明深色底 + 背景模糊 + 高光描边 + 悬浮投影。"""
    base = dict(
        bgcolor=bg or theme.HOME_SURFACE,
        blur=ft.Blur(30, 30),
        border=ft.Border.all(1, theme.HOME_LINE),
        border_radius=radius,
        shadow=ft.BoxShadow(blur_radius=26, spread_radius=-8,
                            color=theme.SHADOW_DEEP, offset=ft.Offset(0, 10)),
    )
    if not shadow:
        base.pop("shadow")
    base.update(over)
    return base


def _hover(e, base: str | None = None) -> None:
    """面板悬停提亮。"""
    e.control.bgcolor = theme.HOME_HOVER if e.data == "true" else (base or theme.HOME_SURFACE)
    e.control.update()


def build(page: ft.Page, on_navigate=None) -> ft.Control:
    """首页。on_navigate(idx)：点击右侧模块分组里的入口时跳到对应模块页。"""

    _GEN["v"] += 1
    gen = _GEN["v"]

    def alive() -> bool:
        return gen == _GEN["v"]

    def safe_update(control: ft.Control | None = None) -> None:
        """控件可能已被卸载（切页 / 关窗），忽略 RuntimeError 即可。"""
        try:
            control.update() if control else page.update()
        except RuntimeError:
            pass

    def tip(msg: str) -> None:
        page.show_dialog(theme.toast(ft.Text(msg, size=12.5, color=theme.HOME_TEXT),
                                     bgcolor=theme.HOME_BG))

    def pill(label: str, icon: str, on_click, size: float = 10.5) -> ft.Container:
        """小玻璃按钮。"""
        return ft.Container(
            height=28, padding=ft.Padding.symmetric(horizontal=10),
            border_radius=14, bgcolor="#1FFFFFFF", ink=True,
            border=ft.Border.all(1, theme.HOME_LINE), on_click=on_click,
            content=ft.Row(spacing=5, tight=True, controls=[
                ft.Icon(icon, size=12.5, color=theme.HOME_SUB),
                ft.Text(label, size=size, color=theme.HOME_TEXT),
            ]),
        )

    # ================= 1) 时间 / 日期 / 天气 / 每日一句 =================
    # 时:分 和 秒 放在同一个 Text 的两个 span 里 —— 这样它们共用一条基线，
    # 秒不会像之前那样在右下角飘着。秒用小一号 + 主题色，主次分明。
    clock_text = ft.Text(spans=[], text_align=ft.TextAlign.CENTER)
    date_text = ft.Text(size=14, color=theme.HOME_SUB)
    meta_text = ft.Text(size=11, color=theme.HOME_FAINT)
    weather_box = ft.Container()
    quote_text = ft.Text(max_lines=2, overflow=ft.TextOverflow.ELLIPSIS, size=16, color=theme.HOME_TEXT, weight=ft.FontWeight.W_500)
    quote_author = ft.Text(size=12.5, color=theme.HOME_SUB)

    def paint_time() -> None:
        n = datetime.now()
        hour = n.hour
        greet = ("夜深了" if hour >= 23 or hour < 5 else
                 "早上好" if hour < 9 else
                 "中午好" if hour < 13 else
                 "下午好" if hour < 18 else "晚上好")
        week = "星期" + "一二三四五六日"[n.weekday()]
        season = ("春" if 3 <= n.month <= 5 else
                  "夏" if 6 <= n.month <= 8 else
                  "秋" if 9 <= n.month <= 11 else "冬")
        clock_text.spans = [
            ft.TextSpan(n.strftime("%H:%M"), style=ft.TextStyle(
                size=80, weight=ft.FontWeight.W_400, color=theme.HOME_TEXT,
                letter_spacing=-4)),
            ft.TextSpan(n.strftime(":%S"), style=ft.TextStyle(
                size=22, weight=ft.FontWeight.W_400,
                color=theme.HOME_ACCENT, letter_spacing=-1)),
        ]
        date_text.value = f"{n.year}年{n.month}月{n.day}日 {week}"
        meta_text.value = f"{greet} · 第{n.strftime('%j').lstrip('0')}天 · {season}"

    paint_time()

    # 时钟这一块必须只建一次、控件对象一直活着：
    # 定时器是靠 clock_block.update() 把新时间推上去的，
    # 如果装配页面时又新建了一个，定时器刷的就是界面上不存在的那个控件，
    # 表现就是秒针不动。
    clock_block = ft.Column(
        spacing=0, tight=True,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            clock_text,
            ft.Container(height=10),
            date_text,
            ft.Container(height=4),
            meta_text,
        ])

    async def tick() -> None:
        """逐秒刷新时钟；面板被卸载（离开首页 / 关窗）时自然退出。"""
        while alive():
            await asyncio.sleep(1)
            if not alive():
                return
            paint_time()
            try:
                clock_block.update()
            except RuntimeError:
                return
            except Exception:           # noqa: BLE001 —— 偶发失败别把秒针停了
                continue

    # --- 天气（一行，放在日期下面）---
    def _degree(value) -> str:
        return "--" if value is None else f"{int(round(value))}°"

    def paint_weather(city: dict, data: dict) -> None:
        today = data["days"][0] if data["days"] else None
        today_text = (f"今日 {_degree(today['min'])}/{_degree(today['max'])}"
                      if today else "今日 --")
        weather_box.content = ft.Column(
            spacing=12, tight=True, controls=[
                ft.Row(spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                       controls=[
                    ft.Icon(data["icon"], size=27, color=theme.HOME_ACCENT),
                    ft.Text(f"{data['temp']}°", size=30,
                            weight=ft.FontWeight.W_800, color=theme.HOME_TEXT),
                    ft.Column(spacing=1, controls=[
                        ft.Text(data["text"], size=12, color=theme.HOME_SUB),
                        ft.Text(f"体感 {data['feels']}° · 湿度 {data['humidity']}%",
                                size=10, color=theme.HOME_FAINT),
                    ]),
                ]),
                ft.Row(spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                       controls=[
                    ft.Icon(ft.Icons.LOCATION_ON_OUTLINED, size=12, color=theme.HOME_FAINT),
                    ft.Text(city["name"], size=11.5, color=theme.HOME_SUB),
                    ft.Text(today_text, size=10, color=theme.HOME_FAINT),
                    ft.Container(expand=True),
                    pill("切换", ft.Icons.MY_LOCATION_OUTLINED,
                         open_city_dialog, 10),
                ]),
            ])

    def paint_weather_state(icon: str, text: str) -> None:
        weather_box.content = ft.Row(spacing=8, controls=[
            ft.Icon(icon, size=17, color=theme.HOME_FAINT),
            ft.Text(text, size=11, color=theme.HOME_SUB),
            ft.Container(expand=True),
            pill("重试", ft.Icons.REFRESH, reload_weather, 10),
        ])

    def _resolve_city() -> dict | None:
        return weather.load_city() or weather.locate_ip()

    # --- 切换城市弹窗 ---
    city_field = ft.TextField(
        label=tr("城市"), hint_text="输入城市名，如 杭州", expand=True, height=44,
        border_radius=12, text_size=13, color=theme.HOME_TEXT,
        label_style=ft.TextStyle(size=11.5, color=theme.HOME_SUB),
        hint_style=ft.TextStyle(size=11.5, color=theme.HOME_FAINT),
        border_color=theme.HOME_LINE, focused_border_color=theme.HOME_ACCENT,
        bgcolor=theme.HOME_SURFACE_SOFT)
    _SEARCH_TIP = "支持中文城市名；同名会有多个候选，按所属省份区分"
    city_tip = ft.Text(_SEARCH_TIP, size=10, color=theme.HOME_FAINT)
    city_results = ft.Column(spacing=8, scroll=ft.ScrollMode.ADAPTIVE,
                             height=190, controls=[])
    city_dialog = ft.AlertDialog(
        title=ft.Text("切换城市", size=15, weight=ft.FontWeight.W_700),
        content=ft.Container(width=340, content=ft.Column(spacing=10, controls=[
            city_tip, city_field, city_results,
        ])))

    async def do_search(e=None) -> None:
        name = (city_field.value or "").strip()
        if not name:
            city_tip.value = "先输入城市名再搜"
            safe_update(city_dialog)
            return
        city_tip.value = "搜索中…"
        city_results.controls = []
        safe_update(city_dialog)
        cities = await asyncio.to_thread(weather.search_city, name)
        if not alive():
            return
        city_tip.value = (f"找到 {len(cities)} 个候选" if cities
                          else "没找到，换个名字试试")
        city_results.controls = [candidate_row(c) for c in cities]
        safe_update(city_dialog)

    def candidate_row(city: dict) -> ft.Container:
        return ft.Container(
            padding=ft.Padding.symmetric(horizontal=12, vertical=10),
            border_radius=14, bgcolor=theme.HOME_SURFACE_SOFT, ink=True,
            border=ft.Border.all(1, theme.HOME_LINE),
            on_click=lambda e, c=city: pick_city(c),
            content=ft.Row(spacing=8, controls=[
                ft.Icon(ft.Icons.LOCATION_ON_OUTLINED, size=15, color=theme.HOME_ACCENT),
                ft.Text(city["name"], size=12.5, weight=ft.FontWeight.W_600,
                        color=theme.HOME_TEXT),
                ft.Text(f"{city.get('region') or ''} {city.get('country') or ''}".strip(),
                        size=10, color=theme.HOME_SUB),
            ]))

    def pick_city(city: dict) -> None:
        weather.save_city(city)
        page.pop_dialog()
        page.run_task(reload_weather)
        tip(f"已切换到 {city['name']}")

    def use_auto_location(e=None) -> None:
        weather.clear_city()
        page.pop_dialog()
        page.run_task(reload_weather)
        tip("已恢复自动定位")

    def open_city_dialog(e=None) -> None:
        city_field.value = ""
        city_results.controls = []
        city_tip.value = _SEARCH_TIP
        city_field.on_submit = do_search
        city_dialog.actions = [
            ft.TextButton("自动定位", on_click=use_auto_location),
            ft.TextButton(tr("取消"), on_click=lambda e: page.pop_dialog()),
            ft.FilledButton(tr("搜索"), on_click=do_search),
        ]
        page.show_dialog(city_dialog)

    async def reload_weather(e=None) -> None:
        if not alive():
            return
        paint_weather_state(ft.Icons.HOURGLASS_EMPTY, "正在获取天气…")
        safe_update(weather_card)
        try:
            city = await asyncio.to_thread(_resolve_city)
            data = (await asyncio.to_thread(weather.fetch, city["lat"],
                                            city["lon"])) if city else None
        except Exception:
            city, data = None, None
        if not alive():
            return
        if data and city:
            paint_weather(city, data)
        else:
            paint_weather_state(ft.Icons.CLOUD_OFF, "天气暂时取不到，检查下网络")
        safe_update(weather_card)

    # --- 每日一句 ---
    def paint_quote() -> None:
        text, author = quotes.current_quote()
        quote_text.value = text
        quote_author.value = f"—— {author}"

    paint_quote()

    def shuffle_quote(e=None) -> None:
        text, author = quotes.next_quote()
        quote_text.value = text
        quote_author.value = f"—— {author}"
        safe_update(quote_card)

    # 1) 时钟 + 日期由上面建好的 clock_block 负责，这里不再重建

    # 2) 天气：单独一张（和名言等宽等高，摆在一起才齐）
    weather_card = ft.Container(
        **glass(radius=RADIUS),
        width=376, height=144,
        padding=ft.Padding.symmetric(horizontal=18, vertical=16),
        alignment=ft.Alignment.CENTER_LEFT,
        on_hover=lambda e: _hover(e),
        content=weather_box,
    )

    # 3) 每日一句：单独一张
    quote_card = ft.Container(
        **glass(radius=RADIUS),
        width=376, height=144,
        padding=ft.Padding.symmetric(horizontal=20, vertical=16),
        on_hover=lambda e: _hover(e),
        content=ft.Column(spacing=8, controls=[
            ft.Row(spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                   controls=[
                ft.Icon(ft.Icons.FORMAT_QUOTE, size=17, color=theme.HOME_ACCENT),
                ft.Text(tr("每日一句"), size=11, color=theme.HOME_FAINT),
                ft.Container(expand=True),
                pill("换一句", ft.Icons.SHUFFLE, shuffle_quote),
            ]),
            quote_text,
            quote_author,
        ]),
    )

    page.run_task(tick)
    page.run_task(reload_weather)

    # ================= 2) 组装：居中、留白、自适应 =================
    quick = [
        ("旅行日志", ft.Icons.LUGGAGE_OUTLINED, 1),
        ("旅程票根", ft.Icons.CONFIRMATION_NUMBER_OUTLINED, 2),
        ("食光小记", ft.Icons.RESTAURANT_OUTLINED, 3),
        ("影视收藏", ft.Icons.MOVIE_FILTER_OUTLINED, 4),
    ]

    def quick_chip(label: str, icon: str, index: int) -> ft.Container:
        def go(e) -> None:
            if on_navigate is not None:
                on_navigate(index)

        return ft.Container(
            width=180, height=64, padding=ft.Padding.symmetric(horizontal=16, vertical=10),
            border_radius=16, ink=True, on_click=go,
            bgcolor=theme.HOME_SURFACE,
            border=ft.Border.all(1, theme.HOME_LINE),
            on_hover=lambda e: _hover(e),
            content=ft.Row(spacing=8, tight=True,
                           vertical_alignment=ft.CrossAxisAlignment.CENTER,
                           controls=[
                ft.Icon(icon, size=16, color=theme.HOME_ACCENT),
                ft.Text(label, size=12.5, color=theme.HOME_TEXT,
                        weight=ft.FontWeight.W_500),
            ]))

    chips_row = ft.Row(spacing=16, wrap=True, run_spacing=12,
                       alignment=ft.MainAxisAlignment.CENTER,
                       controls=[quick_chip(*q) for q in quick])

    brand = ft.Row(spacing=10, alignment=ft.MainAxisAlignment.CENTER,
                   vertical_alignment=ft.CrossAxisAlignment.CENTER,
                   controls=[
        theme.brand_mark(34, theme.HOME_TEXT),
        ft.Text(tr("客行录"), size=14, weight=ft.FontWeight.W_500, color=theme.HOME_TEXT),
    ])

    lower = ft.Row(
        spacing=16, run_spacing=16, wrap=True,
        alignment=ft.MainAxisAlignment.CENTER,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[weather_card, quote_card])

    def open_books():
        import travel_db, travel_journal_view
        groups = {}
        for log in travel_db.list_logs():
            name = (log.get('city') or log.get('title') or '未命名地点').strip()
            groups.setdefault(name, {'key': name, 'name': name, 'logs': []})['logs'].append(log)
        travel_journal_view.open_shelf(page, list(groups.values()), None)

    body = ft.Column(
        spacing=0, tight=True,
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            brand,
            ft.Container(height=16),
            clock_block,
            ft.Container(height=24),
            lower,
            ft.Container(height=20),
            chips_row,
            ft.Container(height=14),
            ft.TextButton(tr('旅行手账'), icon=ft.Icons.MENU_BOOK_OUTLINED,
                style=ft.ButtonStyle(color=theme.HOME_TEXT),
                on_click=lambda e: open_books()),
        ])

    return ft.Container(
        expand=True,
        padding=ft.Padding.symmetric(horizontal=24, vertical=12),
        alignment=ft.Alignment.CENTER,
        content=ft.Column(
            expand=True, scroll=ft.ScrollMode.ADAPTIVE, alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[body]),
    )

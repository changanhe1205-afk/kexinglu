"""客行录 · 旅行日志模块

一页装下所有走过的地方：

    ┌─ 左栏 320 ──────────┬─ 中间：中国地图 ─────────────┬─ 右栏 340 ─────┐
    │ 足迹统计             │  省级边界 + 南海诸岛          │ 上传照片        │
    │ 地点小卡片           │  去过的地方在地图上亮起来      │ 地点 / 日期 / 评分│
    │ （同地照片自动轮播）  │  每个地方钉一枚照片标记        │ 这个地点的照片   │
    └─────────────────────┴─────────────────────────────┴────────────────┘

地名用 map_data 解析成经纬度，同一地点的照片自动聚合成一张卡片、
在地图上缩成一枚圆形照片标记。
"""

from __future__ import annotations
from i18n import tr

import asyncio
import math
import os
import shutil
import uuid
from datetime import datetime

import flet as ft
from date_utils import calendar_date, open_calendar

import map_data
import theme
import tile_map
import travel_db as tdb
from theme import card_shadow, icon_badge

IMG_EXTS = ["png", "jpg", "jpeg", "webp", "bmp"]
CAROUSEL_SECONDS = 3.6        # 卡片自动翻页间隔
LEFT_W, RIGHT_W = 300, 326

_GEN = {"v": 0}               # 每次重建自增，旧的轮播循环自己退出



def _pretty_date(date_str: str) -> str:
    raw = (date_str or "").strip()
    try:
        d = datetime.strptime(raw, "%Y-%m-%d")
    except ValueError:
        return raw or "日期待补"
    return f"{d.year}年{d.month}月{d.day}日"


def _short_date(date_str: str) -> str:
    raw = (date_str or "").strip()
    try:
        d = datetime.strptime(raw, "%Y-%m-%d")
    except ValueError:
        return raw or ""
    return f"{d.year}.{d.month:02d}.{d.day:02d}"


def _uri(path: str) -> str:
    return (path or "").replace("\\", "/")


def _refresh_theme_values() -> None:
    """每次建页重新生成样式，避免模块级字段缓存旧主题。"""
    global FORM_FIELD
    FORM_FIELD = dict(
        border={
            ft.ControlState.DEFAULT: ft.OutlineInputBorder(
                border_radius=10, side=ft.BorderSide(width=1, color=theme.LINE)),
            ft.ControlState.FOCUSED: ft.OutlineInputBorder(
                border_radius=10, side=ft.BorderSide(width=1.4, color=theme.MIST_BLUE_DEEP)),
        },
        text_style=ft.TextStyle(size=13, color=theme.TEXT_MAIN),
        label_style=ft.TextStyle(size=11.5, color=theme.TEXT_SUB),
        hint_style=ft.TextStyle(size=12, color=theme.TEXT_FAINT),
        filled=True, fill_color=theme.CARD_BG,
        content_padding=ft.Padding.symmetric(horizontal=12, vertical=9),
    )


_refresh_theme_values()


def build(page: ft.Page) -> ft.Control:
    _refresh_theme_values()
    _GEN["v"] += 1
    gen = _GEN["v"]

    def alive() -> bool:
        return gen == _GEN["v"]

    def safe_update(control: ft.Control | None = None) -> None:
        try:
            control.update() if control else page.update()
        except RuntimeError:
            pass

    state: dict = {"sel": None, "idx": {}, "pending": [], "hover": None,
                   "view": {}, "groups": [], "lit": set(),
                   "layer": "std", "fs": False, "mapview": None,
                   "map_w": 640, "map_h": 550, "active": True, "repaint_pending": False,
                   "scroll_mode": "pan", "editor_open": False}
    hint_text: ft.Text | None = None

    def show_tip(msg: str) -> None:
        page.show_dialog(theme.toast(ft.Text(msg, size=12.5, color="#FFFFFF"),
                                     bgcolor=theme.MIST_BLUE_DEEP))

    # ---------------- 图片工具 ----------------
    def _save_image(src: str) -> str:
        if not src or not os.path.exists(src):
            return ""
        ext = os.path.splitext(src)[1].lower() or ".jpg"
        dest = os.path.join(tdb.TRAVEL_DIR, f"{uuid.uuid4().hex}{ext}")
        try:
            shutil.copyfile(src, dest)
        except OSError:
            return ""
        return dest

    def _remove_image(path: str) -> None:
        if path and path.startswith(tdb.TRAVEL_DIR) and os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass

    def _open_image(path: str) -> None:
        try:
            from platform_files import open_local
            open_local(path)
        except (OSError, AttributeError):
            show_tip("照片在：" + path)

    # ---------------- 数据聚合 ----------------
    def load_groups() -> list[dict]:
        """把日志按地点聚成组；顺带把解析过的经纬度缓存进库。"""
        groups: dict[str, dict] = {}
        for log in tdb.list_logs():
            lon, lat = log.get("lon"), log.get("lat")
            text = (log.get("city") or "").strip() or (log.get("title") or "").strip()
            hit = map_data.resolve(text) or map_data.resolve(log.get("title") or "")
            if lon is None or lat is None:
                if hit:
                    lon, lat = hit[1], hit[2]
                    tdb.update_log(log["id"], lon=lon, lat=lat)
            name = hit[0] if hit else (text or "未定位")
            g = groups.get(name)
            if g is None:
                g = groups[name] = {
                    "key": name, "name": name, "lon": lon, "lat": lat,
                    "logs": [], "photos": [], "cities": set(), "prov": None,
                    "latest": ""}
            g["logs"].append(log)
            if (log.get("city") or "").strip():
                g["cities"].add(log["city"].strip())
            if (log.get("visit_date") or "") > g["latest"]:
                g["latest"] = log.get("visit_date") or ""
            for ph in log.get("photos") or []:
                g["photos"].append({**ph, "date": log.get("visit_date") or "",
                                    "title": log.get("title") or "",
                                    "city": log.get("city") or ""})
        for g in groups.values():
            g["cities"] = sorted(g["cities"])
            g["prov"] = (map_data.province_of(g["lon"], g["lat"])
                         if g["lon"] is not None else None)
        return sorted(groups.values(),
                      key=lambda g: (g["lon"] is None, g["latest"]), reverse=False)

    def visited_provinces(groups: list[dict]) -> set[str]:
        return {g["prov"] for g in groups if g["prov"]}

    # ---------------- 中间：地图 ----------------
    map_holder = ft.Container(expand=True, alignment=ft.Alignment.CENTER)
    # ---------------- 中间：瓦片地图 ----------------
    MAP_BBOX = (73.5, 18.2, 135.1, 53.6)      # 一眼看全国的取景范围
    OVERLAY_MAX_ZOOM = 8.6                    # 再放大就不叠"去过"色块了
    TILE_MARGIN = 1                           # 多铺一圈瓦片，拖动时不容易露白

    map_holder = ft.Container(expand=True, alignment=ft.Alignment.CENTER)

    fs_holder = ft.Container(data="map_fullscreen", visible=False,
                             left=0, top=0, right=0, bottom=0,
                             bgcolor="#101820")
    page.overlay[:] = [c for c in page.overlay
                       if getattr(c, "data", None) != "map_fullscreen"]
    page.overlay.append(fs_holder)

    class _Surface:
        """一块地图的控件骨架（内嵌 / 全屏各一块）。

        关键点：手势层只创建一次。拖动时只改瓦片层和标记层的偏移，
        不重建控件树——否则 Flutter 的手势会在重建的一瞬间被取消，
        表现就是"地图拖不动"。
        """

        def __init__(self, full: bool):
            self.full = full
            self.render_view = None
            self.render_key = None
            self.tile_pool = {}
            self.bg = ft.Container(left=0, top=0, width=0, height=0)
            self.tiles = ft.Stack(left=0, top=0, width=0, height=0, controls=[])
            self.overlay_box = ft.Container(left=0, top=0, width=0, height=0)
            self.layer = ft.Stack(left=0, top=0, width=0, height=0,
                                  controls=[self.tiles, self.overlay_box])
            self.body = ft.Stack(width=0, height=0,
                                 controls=[self.bg, self.layer])
            self.gesture = ft.GestureDetector(
                content=self.body,
                on_scroll=lambda e: on_wheel(e),
                trackpad_scroll_causes_scale=False,
                on_scale_start=lambda e: on_scale_start(e),
                on_scale_update=lambda e: on_scale_update(e),
                on_scale_end=lambda e: on_scale_end(e),
                on_double_tap=lambda e: zoom_reset())
            self.marks = ft.Stack(left=0, top=0, width=0, height=0, controls=[])
            self.chrome = ft.Stack(left=0, top=0, width=0, height=0, controls=[])
            self.root = ft.Stack(width=0, height=0,
                                 controls=[self.gesture, self.marks, self.chrome])
            if full:
                self.shell = ft.Container(width=0, height=0, bgcolor="#101820",
                                          content=self.root)
            else:
                self.shell = ft.Container(
                    content=self.root, border_radius=20, shadow=card_shadow(),
                    border=ft.Border.all(1, theme.LINE),
                    clip_behavior=ft.ClipBehavior.ANTI_ALIAS)

        def place(self, w: int, h: int) -> None:
            self.w, self.h = w, h
            for c in (self.root, self.body, self.layer, self.tiles,
                      self.overlay_box, self.marks, self.chrome):
                c.width, c.height = w, h
            self.bg.width, self.bg.height = w, h
            if self.full:
                self.shell.width, self.shell.height = w, h

        def offset(self, dx: float, dy: float) -> None:
            """拖动过程中的临时平移。"""
            self.layer.left, self.layer.top = dx, dy
            self.marks.left, self.marks.top = dx, dy

    surfaces: dict[str, _Surface] = {}

    def _surf(full: bool | None = None) -> _Surface:
        key = "full" if (state["fs"] if full is None else full) else "inline"
        s = surfaces.get(key)
        if s is None:
            s = surfaces[key] = _Surface(key == "full")
        return s

    def _active_key() -> str:
        return "fs_view" if state["fs"] else "mapview"

    def _cur() -> tile_map.View | None:
        return state.get(_active_key())

    def _repaint() -> None:
        if state["fs"]:
            paint_fullscreen()
        else:
            paint_map(state["groups"])
        safe_update(_surf().shell)

    def schedule_repaint() -> None:
        # Coalesce high-frequency trackpad events instead of queuing full page redraws.
        if state["repaint_pending"]:
            return
        state["repaint_pending"] = True
        async def flush():
            await asyncio.sleep(1 / 30)
            state["repaint_pending"] = False
            if alive() and state["active"]:
                _repaint()
        page.run_task(flush)

    def _btn(icon, tip, on_click, dim=False) -> ft.Container:
        return ft.Container(
            width=34, height=34, border_radius=11, bgcolor=theme.CARD_BG,
            alignment=ft.Alignment.CENTER, ink=True, tooltip=tip,
            border=ft.Border.all(1, theme.LINE), on_click=on_click,
            opacity=0.4 if dim else 1.0,
            shadow=ft.BoxShadow(blur_radius=8, spread_radius=-3,
                                color="#3A7BA896", offset=ft.Offset(0, 2)),
            content=ft.Icon(icon, size=17, color=theme.TEXT_SUB))

    def set_layer(key: str) -> None:
        if state["layer"] == key:
            return
        state["layer"] = key
        _repaint()

    def _layer_chips() -> ft.Control:
        chips = []
        for key in tile_map.LAYER_KEYS:
            on = state["layer"] == key
            chips.append(ft.Container(
                height=30, padding=ft.Padding.symmetric(horizontal=13),
                border_radius=10, ink=True, alignment=ft.Alignment.CENTER,
                bgcolor=theme.ACCENT if on else theme.CARD_BG,
                border=ft.Border.all(1, theme.ACCENT if on else theme.LINE),
                on_click=lambda e, k=key: set_layer(k),
                content=ft.Text(tile_map.LAYER_NAMES[key], size=11.5,
                                color=theme.ON_ACCENT if on else theme.TEXT_SUB,
                                weight=ft.FontWeight.W_600 if on
                                else ft.FontWeight.W_400)))
        return ft.Container(
            padding=5, border_radius=13, bgcolor=theme.CARD_GLASS,
            border=ft.Border.all(1, theme.LINE),
            shadow=ft.BoxShadow(blur_radius=12, spread_radius=-4,
                                color="#3A7BA880", offset=ft.Offset(0, 3)),
            content=ft.Row(spacing=5, controls=chips))

    def zoom_apply(zoom: float, anchor=None) -> None:
        v = _cur()
        if v is None:
            return
        state[_active_key()] = v.zoomed(
            max(tile_map.MIN_ZOOM, min(tile_map.MAX_ZOOM, zoom)), anchor)
        _repaint()

    def zoom_step(direction: int) -> None:
        v = _cur()
        if v is not None:
            zoom_apply(v.zoom + direction)

    def zoom_reset() -> None:
        v = _cur()
        if v is None:
            return
        state[_active_key()] = tile_map.fit_view(v.width, v.height, MAP_BBOX)
        _repaint()

    def fit_footprints(e=None) -> None:
        v = _cur()
        points = [g for g in state["groups"] if g["lon"] is not None and g["lat"] is not None]
        if v is None or not points:
            return
        lons, lats = [g["lon"] for g in points], [g["lat"] for g in points]
        if len(points) == 1:
            state[_active_key()] = tile_map.View(v.width, v.height, lons[0], lats[0], 10)
        else:
            state[_active_key()] = tile_map.fit_view(v.width, v.height,
                (min(lons)-.15, min(lats)-.15, max(lons)+.15, max(lats)+.15), pad=.65)
        _repaint()

    def on_wheel(e) -> None:
        ft.context.disable_auto_update()
        v = _cur()
        if v is None:
            return
        d = getattr(e, "scroll_delta", 0) or 0
        dx = getattr(d, "x", 0) or 0
        dy = getattr(d, "y", d)
        try:
            dx, dy = float(dx), float(dy)
        except (TypeError, ValueError):
            return
        if not dx and not dy:
            return
        if state["scroll_mode"] == "pan":
            state[_active_key()] = v.shifted(-dx, -dy)
            schedule_repaint()
            return
        step = max(-1.0, min(1.0, -dy / 240.0))
        pos = getattr(e, "local_position", None)
        anchor = None
        if pos is not None and getattr(pos, "x", None) is not None:
            anchor = (pos.x, pos.y)
        state[_active_key()] = v.zoomed(v.zoom + step, anchor)
        schedule_repaint()

    def toggle_scroll_mode(e=None):
        state["scroll_mode"] = "zoom" if state["scroll_mode"] == "pan" else "pan"
        _repaint()

    def on_scale_start(e) -> None:
        ft.context.disable_auto_update()
        v = _cur()
        if v is None:
            return
        p = e.local_focal_point
        state["gesture"] = {"view": v, "anchor": (p.x, p.y)}

    def on_scale_update(e) -> None:
        ft.context.disable_auto_update()
        gesture = state.get("gesture")
        if not gesture:
            on_scale_start(e)
            gesture = state.get("gesture")
        if not gesture:
            return
        base, anchor = gesture["view"], gesture["anchor"]
        scale = max(.01, float(e.scale))
        p = e.local_focal_point
        # One scale recognizer handles both mouse dragging and trackpad pinch;
        # Flutter forbids registering competing pan + scale recognizers together.
        state[_active_key()] = base.zoomed(base.zoom + math.log2(scale), anchor).shifted(
            p.x - anchor[0], p.y - anchor[1])
        schedule_repaint()

    def on_scale_end(e) -> None:
        ft.context.disable_auto_update()
        state.pop("gesture", None)
        _surf().render_key = None
        _repaint()

    # ---------------- 全屏 ----------------
    def open_fullscreen(e=None) -> None:
        state["fs"] = True
        try:
            page.window.full_screen = True
        except Exception:
            pass
        fs_holder.visible = True
        paint_fullscreen()
        safe_update()
        page.run_task(_fs_watch)

    def close_fullscreen(e=None) -> None:
        state["fs"] = False
        fs_holder.visible = False
        try:
            page.window.full_screen = False
        except Exception:
            pass
        v = state.get("fs_view")
        if v is not None and state.get("map_w"):
            state["mapview"] = tile_map.View(state["map_w"], state["map_h"],
                                             v.lon, v.lat, v.zoom)
        paint_map(state["groups"])
        safe_update()

    async def _fs_watch() -> None:
        """全屏后窗口尺寸会变，盯着它重铺瓦片。"""
        while alive() and state["fs"]:
            await asyncio.sleep(0.4)
            if not state["fs"]:
                return
            w, h = int(page.width or 0), int(page.height or 0)
            v = state.get("fs_view")
            if w and h and v and (abs(v.width - w) > 2
                                  or abs(v.height - h) > 2):
                paint_fullscreen(w, h)
                safe_update()

    def paint_fullscreen(w: int | None = None, h: int | None = None) -> None:
        w = int(w or page.width or 1320)
        h = int(h or page.height or 900)
        v = state.get("fs_view")
        base = state.get("mapview")
        if v is None:
            v = (tile_map.View(w, h, base.lon, base.lat, base.zoom + 0.9)
                 if base else tile_map.fit_view(w, h, MAP_BBOX))
        elif abs(v.width - w) > 2 or abs(v.height - h) > 2:
            v = tile_map.View(w, h, v.lon, v.lat, v.zoom)
        state["fs_view"] = v
        _render(True)

    # ---------------- 地图内容 ----------------
    def _province_overlay(view: tile_map.View, w: int, h: int) -> ft.Control:
        lit = state.get("lit") or set()
        if not lit or view.zoom > OVERLAY_MAX_ZOOM:
            return ft.Container(width=w, height=h)
        return map_data.build_overlay(view, w, h, lit, theme.ACCENT,
                                      view.bbox())

    def _chrome(view: tile_map.View, w: int, h: int,
                full: bool) -> list[ft.Control]:
        lit = state.get("lit") or set()
        groups = state["groups"]
        left = 20 if full else 18
        out: list[ft.Control] = []

        title = ft.Container(
            padding=ft.Padding.only(left=13, right=15, top=9, bottom=9),
            border_radius=14, bgcolor=theme.CARD_GLASS,
            border=ft.Border.all(1, theme.LINE),
            shadow=ft.BoxShadow(blur_radius=12, spread_radius=-5,
                                color="#2E6E9A8C", offset=ft.Offset(0, 3)),
            content=ft.Row(spacing=9, controls=[
                ft.Container(width=4, height=30, border_radius=2,
                             gradient=ft.LinearGradient(
                                 begin=ft.Alignment.TOP_CENTER,
                                 end=ft.Alignment.BOTTOM_CENTER,
                                 colors=[theme.ACCENT,
                                         theme.with_alpha(theme.ACCENT, 0.35)])),
                ft.Column(spacing=1, controls=[
                    ft.Text("我的旅行地图", size=17 if full else 16,
                            weight=ft.FontWeight.W_800, color=theme.TEXT_MAIN),
                    ft.Text(f"{len(groups)} 个地方 · 已点亮 {len(lit)} 个省"
                            f" · {tile_map.LAYER_NAMES[state['layer']]}"
                            f" · 缩放 {view.zoom:.1f} 级",
                            size=11, color=theme.TEXT_SUB),
                ]),
            ]))
        out.append(ft.Container(left=left, top=16, content=title))

        btns = ft.Row(spacing=7, controls=[
            _btn(ft.Icons.OPEN_WITH if state["scroll_mode"] == "pan" else ft.Icons.ZOOM_IN,
                 "滚动：平移（点击切换缩放）" if state["scroll_mode"] == "pan" else "滚动：缩放（点击切换平移）",
                 toggle_scroll_mode),
            _btn(ft.Icons.ADD, "放大",
                 lambda e: zoom_step(1), view.zoom >= tile_map.MAX_ZOOM),
            _btn(ft.Icons.REMOVE, "缩小",
                 lambda e: zoom_step(-1), view.zoom <= tile_map.MIN_ZOOM),
            _btn(ft.Icons.CENTER_FOCUS_STRONG, "回到整幅地图",
                 lambda e: zoom_reset()),
            _btn(ft.Icons.MY_LOCATION, "查看全部足迹", fit_footprints, not groups),
            _btn(ft.Icons.FULLSCREEN_EXIT if full else ft.Icons.FULLSCREEN,
                 "退出全屏" if full else "全屏看地图",
                 lambda e: close_fullscreen() if full else open_fullscreen()),
        ])
        out.append(ft.Container(
            right=20 if full else 16, top=16 if w >= 700 else 88,
            content=ft.Column(spacing=8,
                              horizontal_alignment=ft.CrossAxisAlignment.END,
                              controls=[_layer_chips(), btns])))

        bar_width, label = tile_map.scale_bar(view)
        out.append(ft.Container(right=16, bottom=16, padding=8, border_radius=8,
            bgcolor=theme.CARD_GLASS, content=ft.Column(spacing=3, tight=True,
                horizontal_alignment=ft.CrossAxisAlignment.END, controls=[
                    ft.Text(label, size=10, color=theme.TEXT_MAIN),
                    ft.Container(width=bar_width, height=5,
                        border=ft.Border(left=ft.BorderSide(1, theme.TEXT_MAIN),
                                         bottom=ft.BorderSide(1, theme.TEXT_MAIN),
                                         right=ft.BorderSide(1, theme.TEXT_MAIN))),
                    ft.Text("高德地图 · 北 ↑", size=9, color=theme.TEXT_SUB),
                ])))

        if lit:
            out.append(ft.Container(
                left=left, bottom=18 if full else 16,
                content=ft.Container(
                    padding=ft.Padding.symmetric(horizontal=12, vertical=7),
                    border_radius=12, bgcolor=theme.CARD_GLASS,
                    border=ft.Border.all(1, theme.LINE),
                    shadow=ft.BoxShadow(blur_radius=10, spread_radius=-4,
                                        color="#3A7BA8B4",
                                        offset=ft.Offset(0, 3)),
                    content=ft.Row(spacing=14, controls=[
                        ft.Row(spacing=6, tight=True, controls=[
                            ft.Container(
                                width=12, height=12, border_radius=4,
                                bgcolor=theme.with_alpha(theme.ACCENT, 0.30),
                                border=ft.Border.all(
                                    1.2, theme.with_alpha(theme.ACCENT, 0.70))),
                            ft.Text("去过的省", size=10.5, color=theme.TEXT_SUB),
                        ]),
                        ft.Row(spacing=6, tight=True, controls=[
                            ft.Container(width=12, height=12, border_radius=4,
                                         bgcolor=theme.CARD_BG,
                                         border=ft.Border.all(1, theme.LINE)),
                            ft.Text("还没去", size=10.5, color=theme.TEXT_SUB),
                        ]),
                    ]))))

        if full:
            out.append(ft.Container(
                left=0, right=0, bottom=18, alignment=ft.Alignment.CENTER,
                content=ft.Container(
                    padding=ft.Padding.symmetric(horizontal=14, vertical=7),
                    border_radius=12, bgcolor=theme.CARD_GLASS,
                    border=ft.Border.all(1, theme.LINE),
                    content=ft.Text("双指滑动平移 · 捏合缩放 · "
                                    "双击回到整幅地图 · 右上角换图层",
                                    size=11, color=theme.TEXT_SUB))))

        if not groups:
            out.append(ft.Container(
                left=16, right=16, top=174 if w < 700 else 80, bottom=12,
                alignment=ft.Alignment.CENTER,
                content=ft.Container(
                    padding=ft.Padding.symmetric(horizontal=26, vertical=20),
                    border_radius=18, bgcolor=theme.CARD_GLASS,
                    border=ft.Border.all(1, theme.LINE),
                    shadow=ft.BoxShadow(blur_radius=18, spread_radius=-6,
                                        color="#3A7BA896",
                                        offset=ft.Offset(0, 6)),
                    content=ft.Column(
                        spacing=8, tight=True,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Container(
                                width=54, height=54, border_radius=27,
                                bgcolor=theme.with_alpha(theme.ACCENT, 0.12),
                                alignment=ft.Alignment.CENTER,
                                content=ft.Icon(ft.Icons.TRAVEL_EXPLORE,
                                                size=26, color=theme.ACCENT)),
                            ft.Text("还没有点亮任何地方", size=14.5,
                                    weight=ft.FontWeight.W_700, color=theme.TEXT_MAIN),
                            ft.Text("右边上传照片、写下地点，它就会钉到地图上",
                                    size=11.5, color=theme.TEXT_SUB),
                        ]))))
        return out

    def _render(full: bool) -> None:
        """把当前视口画进对应的控件骨架（控件对象本身不换）。"""
        v = state["fs_view"] if full else state.get("mapview")
        if v is None:
            return
        w, h = int(v.width), int(v.height)
        s = _surf(full)
        # Keep the existing map controls while panning within the buffered tiles.
        # Selection/data/zoom/layout changes still rebuild the visible content.
        key = (w, h, v.zoom, state['layer'], state['sel'], state['scroll_mode'],
               tuple((g['key'], g['lon'], g['lat'], tuple(p['image'] for p in g['photos']))
                     for g in state['groups']), tuple(sorted(state['lit'])))
        previous = s.render_view
        if previous is not None and key == s.render_key:
            dx, dy = v(previous.lon, previous.lat)
            dx -= w / 2
            dy -= h / 2
            if abs(dx) < min(96, v.tile / 2) and abs(dy) < min(96, v.tile / 2):
                s.offset(dx, dy)
                return
        s.render_view, s.render_key = v, key
        s.place(w, h)
        s.bg.bgcolor = tile_map.LAYER_BG[state["layer"]]
        s.tiles.controls = v.project_all(state["layer"], TILE_MARGIN, s.tile_pool)
        s.overlay_box.content = _province_overlay(v, w, h)
        s.offset(0, 0)
        s.marks.controls = _markers(state["groups"], v, w, h)
        s.chrome.controls = _chrome(v, w, h, full)
        if full:
            fs_holder.content = s.shell
        else:
            map_holder.content = s.shell

    def paint_map(groups: list[dict]) -> None:
        win_w = page.width or page.window.width or 1320
        # 内容区外框左右 44，地图内边距 24；使用客户区尺寸避免 DPI / 窗框偏差。
        avail = max(260, win_w - LEFT_W - (RIGHT_W if state["editor_open"] else 0) - 72)
        map_w = avail
        map_h = int(max(260, (page.height or 900) - 350))
        state["map_w"], state["map_h"] = map_w, map_h
        state["groups"] = groups
        state["lit"] = visited_provinces(groups)
        v = state.get("mapview")
        if v is None:
            v = tile_map.fit_view(map_w, map_h, MAP_BBOX)
        elif abs(v.width - map_w) > 2 or abs(v.height - map_h) > 2:
            v = tile_map.View(map_w, map_h, v.lon, v.lat, v.zoom)
        state["mapview"] = v
        _render(False)
        if state["fs"]:
            paint_fullscreen()
        if hint_text is not None:
            hint_text.value = ("双指滑动平移 · 捏合缩放 · 双击看全国" if state["scroll_mode"] == "pan"
                               else "滚动缩放 · 拖动平移 · 箭头按钮可切回双指平移")

    def _markers(groups: list[dict], proj, mw: int,
                 mh: int) -> list[ft.Control]:
        """把每个地点画成一枚圆形照片标记，并做一次简单避让。"""
        placed: list[list[float]] = []
        out: list[ft.Control] = []
        items = [g for g in groups if g["lon"] is not None]
        items.sort(key=lambda g: -len(g["photos"]))
        for g in items:
            x, y = proj(g["lon"], g["lat"])
            if not (-30 <= x <= mw + 30 and -30 <= y <= mh + 30):
                continue                      # 视野之外的标记不画
            for _ in range(14):
                if all((x - px) ** 2 + (y - py) ** 2 > 34 ** 2
                       for px, py in placed):
                    break
                y += 34
                if y > mh - 24:
                    y = proj(g["lon"], g["lat"])[1] - 34
            placed.append([x, y])
            out.append(_marker(g, x, y))
            if state["sel"] == g["key"]:
                out.append(ft.Container(
                    left=x - 72, top=y + 31, width=144,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Container(
                        padding=ft.Padding.symmetric(horizontal=12, vertical=4),
                        border_radius=12, bgcolor=theme.CARD_BG,
                        border=ft.Border.all(1.2, theme.ACCENT),
                        shadow=ft.BoxShadow(blur_radius=10, spread_radius=-3,
                                            color="#3A66909C",
                                            offset=ft.Offset(0, 3)),
                        content=ft.Text(g["name"], size=11.5,
                                        weight=ft.FontWeight.W_700,
                                        color=theme.ACCENT, max_lines=1,
                                        overflow=ft.TextOverflow.ELLIPSIS))))
        return out

    def _marker(g: dict, x: float, y: float) -> ft.Control:
        on = state["sel"] == g["key"]
        slot = 70
        size = 50 if on else 42
        photo = g["photos"][0]["image"] if g["photos"] else ""
        inner: ft.Control = (
            ft.Image(src=_uri(photo), fit=ft.BoxFit.COVER,
                     width=size - 6, height=size - 6, cache_width=144)
            if photo else
            ft.Icon(ft.Icons.LANDSCAPE_OUTLINED, size=size * 0.4,
                    color="#9AB2C6"))
        glow_size = size + 20
        stack: list[ft.Control] = []
        if on:
            stack.append(ft.Container(
                left=(slot - glow_size) / 2, top=(slot - glow_size) / 2,
                width=glow_size, height=glow_size,
                border_radius=glow_size / 2,
                bgcolor=theme.with_alpha(theme.ACCENT, 0.16)))
        stack.append(ft.Container(
            left=(slot - size) / 2, top=(slot - size) / 2,
            width=size, height=size, border_radius=size / 2,
            bgcolor=theme.CARD_BG,
            border=ft.Border.all(3, theme.ACCENT if on else theme.CARD_BG),
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            alignment=ft.Alignment.CENTER, content=inner,
            shadow=ft.BoxShadow(blur_radius=14 if on else 9,
                                spread_radius=-2,
                                color=theme.with_alpha("#26476B", 0.42),
                                offset=ft.Offset(0, 4))))
        stack.append(ft.Container(
            right=3, bottom=3, height=19,
            padding=ft.Padding.symmetric(horizontal=7), border_radius=10,
            bgcolor=theme.ACCENT if on else theme.CARD_BG,
            border=ft.Border.all(1.4,
                                 "#FFFFFF" if on else theme.ACCENT),
            shadow=ft.BoxShadow(blur_radius=7, spread_radius=-2,
                                color="#3A6690A0", offset=ft.Offset(0, 2)),
            alignment=ft.Alignment.CENTER,
            content=ft.Text(str(max(1, len(g["photos"]))), size=10.5,
                            weight=ft.FontWeight.W_800,
                            color=theme.ON_ACCENT if on else theme.ACCENT)))
        return ft.Container(
            left=x - slot / 2, top=y - slot / 2, width=slot, height=slot,
            on_click=lambda e, k=g["key"]: select_group(k),
            on_hover=lambda e, k=g["key"]: _hover_mark(k, e.data == "true"),
            ink=False,
            content=ft.Stack(controls=stack))

    def _hover_mark(key: str, on: bool) -> None:
        state["hover"] = key if on else None

    # ---------------- 左栏：地点小卡片 ----------------
    stats_text = ft.Text("", size=11.5, color=theme.TEXT_SUB)
    card_list = ft.ListView(spacing=12, expand=True, padding=ft.Padding.only(right=4))

    def place_card(g: dict) -> ft.Container:
        photos = g["photos"]
        total = len(photos)
        idx = state["idx"].get(g["key"], 0) % max(1, total)
        on = state["sel"] == g["key"]
        img = ft.Image(src="", fit=ft.BoxFit.COVER, expand=True, cache_width=640)
        sub = ft.Text("", size=11, color="#FFFFFF")
        dots = ft.Row(spacing=4, controls=[
            ft.Container(width=5, height=5, border_radius=3,
                         bgcolor=theme.ACCENT if i == idx else theme.LINE)
            for i in range(min(total, 8))])
        state["view"][g["key"]] = {"img": img, "sub": sub, "dots": dots,
                                   "n": total}
        _paint_carousel(g["key"])

        arrows = ft.Row(spacing=4, controls=[
            ft.Container(width=26, height=26, border_radius=13,
                         bgcolor="#40000000", ink=True, alignment=ft.Alignment.CENTER,
                         on_click=lambda e, k=g["key"]: _advance(k, -1),
                         content=ft.Icon(ft.Icons.CHEVRON_LEFT, size=16,
                                         color="#FFFFFF")),
            ft.Container(width=26, height=26, border_radius=13,
                         bgcolor="#40000000", ink=True, alignment=ft.Alignment.CENTER,
                         on_click=lambda e, k=g["key"]: _advance(k, 1),
                         content=ft.Icon(ft.Icons.CHEVRON_RIGHT, size=16,
                                         color="#FFFFFF")),
        ]) if total > 1 else ft.Container()

        thumb = ft.Container(
            height=114, border_radius=13, clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            bgcolor=theme.CARD_BG_SOFT,
            content=ft.Stack(controls=[
                ft.Container(left=0, right=0, top=0, bottom=0,
                             alignment=ft.Alignment.CENTER,
                             content=img if total else ft.Icon(ft.Icons.PHOTO_OUTLINED,
                                                               size=30, color=theme.TEXT_FAINT)),
                ft.Container(left=0, right=0, bottom=0, height=52,
                             gradient=ft.LinearGradient(
                                 begin=ft.Alignment.TOP_CENTER,
                                 end=ft.Alignment.BOTTOM_CENTER,
                                 colors=["#00000000", "#B0000000" if total else "#00000000"])),
                ft.Container(left=9, right=9, bottom=7, content=sub),
                ft.Container(right=7, top=7, content=arrows),
            ]))

        head = ft.Row(spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                      controls=[
            ft.Container(width=30, height=30, border_radius=10,
                         bgcolor=theme.with_alpha(theme.ACCENT, 0.14),
                         alignment=ft.Alignment.CENTER,
                         content=ft.Icon(ft.Icons.PLACE_OUTLINED, size=16,
                                         color=theme.ACCENT)),
            ft.Column(spacing=1, expand=True, controls=[
                ft.Text(g["name"], size=13.5, weight=ft.FontWeight.W_700,
                        color=theme.ACCENT if on else theme.TEXT_MAIN, max_lines=1,
                        overflow=ft.TextOverflow.ELLIPSIS),
                ft.Text(f"{total} 张照片"
                        + (f" · {' / '.join(g['cities'][:2])}" if g["cities"] else ""),
                        size=10.5, color=theme.TEXT_SUB, max_lines=1,
                        overflow=ft.TextOverflow.ELLIPSIS),
            ]),
            dots,
        ])

        return ft.Container(
            padding=10, border_radius=16,
            bgcolor=theme.with_alpha(theme.ACCENT, 0.06) if on else theme.CARD_BG,
            border=ft.Border.all(1.6 if on else 1,
                                 theme.ACCENT if on else theme.LINE),
            shadow=card_shadow() if on else None,
            on_click=lambda e, k=g["key"]: select_group(k),
            on_hover=lambda e, k=g["key"]: _hover_card(k, e.data == "true"),
            content=ft.Column(spacing=8, controls=[head, thumb] if total else [head,
                ft.Text((g['logs'][0].get('note') or '点开记录旅途中的片刻') if g.get('logs') else '点开记录旅途中的片刻',
                    size=11,color=theme.TEXT_SUB,max_lines=2,overflow=ft.TextOverflow.ELLIPSIS)]))

    def _paint_carousel(key: str) -> None:
        v = state["view"].get(key)
        if not v or not v["n"]:
            if v:
                v["sub"].value = "还没有照片，右边上传一张"
                v["sub"].color = theme.TEXT_SUB
                v["img"].src = ""
            return
        idx = state["idx"].get(key, 0) % v["n"]
        groups = state["groups"]
        g = next((x for x in groups if x["key"] == key), None)
        if not g:
            return
        ph = g["photos"][idx]
        v["img"].src = _uri(ph["image"])
        bits = [b for b in (ph.get("title"), _short_date(ph.get("date"))) if b]
        v["sub"].value = " · ".join(bits) or f"{idx + 1}/{v['n']}"
        for i, dot in enumerate(v["dots"].controls):
            dot.bgcolor = theme.ACCENT if i == idx else theme.LINE

    def _advance(key: str, delta: int) -> None:
        ft.context.disable_auto_update()
        v = state["view"].get(key)
        if not v or v["n"] <= 1:
            return
        state["idx"][key] = (state["idx"].get(key, 0) + delta) % v["n"]
        _paint_carousel(key)
        safe_update(card_list)

    def _hover_card(key: str, on: bool) -> None:
        ft.context.disable_auto_update()
        state["hover"] = key if on else None

    # ---------------- 选中 ----------------
    def select_group(key: str | None) -> None:
        if key == state['sel']:
            toggle_editor(True)
            return
        if form_dirty():
            confirm_discard(lambda: select_clean(key));return
        select_clean(key)

    def select_clean(key):
        state['pending']=[]
        paint_pending()
        state["sel"] = key
        state['editor_open']=True
        right_panel.visible=True
        g = next((x for x in state["groups"] if x["key"] == key), None)
        fill_form(g)
        paint_cards()
        paint_map(state["groups"])
        safe_update()

    def search_changed(e):
        ft.context.disable_auto_update()
        paint_cards()
        safe_update(card_list)

    search_input=ft.TextField(label='查找地点',prefix_icon=ft.Icons.SEARCH, text_size=12,
        border_radius=12,content_padding=10,height=42,border_color=theme.LINE,
        on_change=search_changed)

    def paint_cards() -> None:
        groups = state["groups"]
        cities = {c for g in groups for c in g["cities"]}
        stats_text.value = (f"{len(groups)} 个地点 · {len(cities)} 座城市"
                            f" · {sum(len(g['photos']) for g in groups)} 张照片")
        if not groups:
            card_list.controls = [ft.Container(
                padding=ft.Padding.only(top=12, left=4),
                content=ft.Text("从上方「记录旅程」开始，留下第一个地点", size=11,
                                color=theme.TEXT_FAINT))]
            return
        state["view"].clear()
        query=(search_input.value or '').strip().lower()
        filtered=[g for g in groups if not query or query in (g['name']+' '+' '.join(g['cities'])).lower()]
        card_list.controls = [place_card(g) for g in filtered]
        if not filtered:card_list.controls=[ft.Text('没有匹配地点，试试其他关键词',size=12,color=theme.TEXT_SUB)]

    # ---------------- 右栏：上传 + 编辑 ----------------
    photo_pick = ft.FilePicker()
    photo_pick.data = "travel_photos"
    if not any(getattr(s, "data", None) == "travel_photos" for s in page.services):
        page.services.append(photo_pick)

    title_input = ft.TextField(**FORM_FIELD, label=tr("地点"),
                               hint_text="如 西湖 / 鼓浪屿 / 大理")
    city_input = ft.TextField(**FORM_FIELD, label="城市（可不填）",
                              hint_text="如 杭州")
    date_input = ft.TextField(**FORM_FIELD, label=tr("日期"),
                              hint_text="点右边日历选", read_only=True, expand=True)
    note_input = ft.TextField(**FORM_FIELD, label="感想",
                              hint_text="路上的小事、当时的心情…",
                              multiline=True, min_lines=3, max_lines=5, height=92)
    locate_text = ft.Text("", size=10.5, color=theme.TEXT_FAINT, max_lines=2)
    pending_grid = ft.Row(spacing=8, wrap=True, controls=[])
    pending_hint = ft.Text("", size=11, color=theme.TEXT_SUB)
    saved_grid = ft.Row(spacing=8, wrap=True, controls=[])

    date_picker = ft.DatePicker(on_change=lambda e: (
        setattr(date_input, "value",
                calendar_date(e.control.value)),
        paint_locate(), page.update()))

    star_buttons: list[ft.IconButton] = []
    picked_rating = {"v": 5}

    def paint_rating() -> None:
        for i, btn in enumerate(star_buttons):
            btn.icon = (ft.Icons.STAR if i < picked_rating["v"]
                        else ft.Icons.STAR_BORDER)
            btn.icon_color = (theme.SOFT_LEMON if i < picked_rating["v"] else theme.STAR_OFF)

    def set_rating(e) -> None:
        picked_rating["v"] = int(e.control.data)
        paint_rating()
        safe_update()

    for i in range(5):
        star_buttons.append(ft.IconButton(
            ft.Icons.STAR_BORDER, icon_size=21, width=32, height=32, padding=0,
            tooltip=f"{i + 1} 星", data=i + 1, on_click=set_rating))
    rating_row = ft.Row(spacing=2, controls=star_buttons)

    def paint_locate() -> None:
        title = (title_input.value or "").strip()
        city = (city_input.value or "").strip()
        hit = map_data.resolve(city) or map_data.resolve(title)
        if hit:
            prov = map_data.province_of(hit[1], hit[2]) or ""
            locate_text.value = (f"定位到「{hit[0]}」{('·' + prov) if prov else ''}"
                                 f"  {hit[1]:.2f}°E {hit[2]:.2f}°N")
            locate_text.color = theme.MIST_BLUE_DEEP
        elif title or city:
            locate_text.value = "地图上没找到这个地名，换个说法试试（如只写城市名）"
            locate_text.color = theme.DANGER
        else:
            locate_text.value = "填好地点后会自动定位到地图上"
            locate_text.color = theme.TEXT_FAINT

    async def choose_photos(e=None) -> None:
        files = await photo_pick.pick_files(
            dialog_title="选旅行照片（可多选）",
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=IMG_EXTS, allow_multiple=True)
        if not files:
            return
        added = 0
        for f in files:
            path = _save_image(f.path)
            if path:
                state["pending"].append(path)
                added += 1
        paint_pending()
        if added:
            show_tip(f"加了 {added} 张照片，填好地点后点保存")
        safe_update()

    def paint_pending() -> None:
        items = state["pending"]
        pending_hint.value = (f"待保存 {len(items)} 张" if items
                              else "还没有选照片")
        pending_grid.controls = [_thumb(p, on_remove=_drop_pending)
                                 for p in items]

    def _drop_pending(path: str) -> None:
        if path in state["pending"]:
            state["pending"].remove(path)
        _remove_image(path)
        paint_pending()
        safe_update()

    def _thumb(path: str, on_remove=None, h: float = 62) -> ft.Container:
        return ft.Container(
            width=h * 1.35, height=h, border_radius=10,
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS, border=ft.Border.all(1, theme.LINE),
            content=ft.Stack(controls=[
                ft.Image(src=_uri(path), fit=ft.BoxFit.COVER, expand=True),
                ft.Container(right=2, top=2, width=18, height=18, border_radius=9,
                             bgcolor="#B0000000", alignment=ft.Alignment.CENTER,
                             ink=True,
                             on_click=lambda e, p=path: on_remove(p) if on_remove else None,
                             content=ft.Icon(ft.Icons.CLOSE, size=11,
                                             color="#FFFFFF")),
                ft.Container(left=0, right=0, bottom=0, height=18,
                             bgcolor="#50000000", alignment=ft.Alignment.CENTER,
                             ink=True, on_click=lambda e, p=path: _open_image(p),
                             content=ft.Icon(ft.Icons.ZOOM_OUT_MAP, size=11,
                                             color="#FFFFFF")),
            ]))

    def paint_saved(photos: list[dict]) -> None:
        saved_grid.controls = [
            _thumb(p["image"], on_remove=lambda path, pid=p["id"]: _drop_saved(pid),
                   h=58)
            for p in photos]

    def _drop_saved(pid: int) -> None:
        row = tdb.delete_photo(pid)
        if row:
            _remove_image(row.get("image") or "")
        show_tip("照片已删除")
        refresh()

    def form_signature():
        return (title_input.value or '',city_input.value or '',date_input.value or '',
                note_input.value or '',picked_rating['v'])

    def form_dirty():
        return bool(state['pending']) or form_signature()!=state.get('form_saved',form_signature())

    def confirm_discard(action):
        from notebook_navigation import after_dialog_closed
        page.show_dialog(ft.AlertDialog(modal=True,title=ft.Text('保留这段未保存的记录？'),
            content=ft.Text('你有尚未保存的文字或照片，可以继续编辑后保存。'),actions=[
                ft.TextButton(tr('继续编辑'),on_click=lambda e:after_dialog_closed(page,lambda:toggle_editor(True))),
                ft.TextButton('放弃修改并继续',on_click=lambda e:after_dialog_closed(page,action))]))

    def toggle_editor(opened=None):
        state['editor_open']=not state['editor_open'] if opened is None else opened
        right_panel.visible=state['editor_open']
        paint_map(state['groups']);safe_update()

    def new_record(e=None):
        def begin():
            state['pending']=[];clear_form();paint_pending();paint_cards();toggle_editor(True)
        if form_dirty():confirm_discard(begin)
        else:begin()

    def fill_form(g: dict | None) -> None:
        g = g or {}
        log = (g.get("logs") or [{}])[0]
        title_input.value = log.get("title") or ""
        city_input.value = log.get("city") or ""
        date_input.value = log.get("visit_date") or ""
        note_input.value = log.get("note") or ""
        picked_rating["v"] = int(log.get("rating") or 5)
        paint_rating()
        paint_locate()
        paint_saved(g.get("photos") or [])
        state["form_saved"]=form_signature()

    def clear_form() -> None:
        state["sel"] = None
        title_input.value = ""
        city_input.value = ""
        date_input.value = ""
        note_input.value = ""
        picked_rating["v"] = 5
        paint_rating()
        paint_locate()
        paint_saved([])
        state["form_saved"]=form_signature()

    def save_log(e=None) -> None:
        title = (title_input.value or "").strip()
        city = (city_input.value or "").strip()
        if not title and not city:
            show_tip("先写下这是哪儿")
            return
        hit = map_data.resolve(city) or map_data.resolve(title)
        fields = dict(
            title=title or (hit[0] if hit else ""),
            city=city,
            visit_date=(date_input.value or "").strip(),
            rating=picked_rating["v"],
            note=(note_input.value or "").strip(),
            image="",
            lon=hit[1] if hit else None,
            lat=hit[2] if hit else None,
        )
        sel = state["sel"]
        g = next((x for x in state["groups"] if x["key"] == sel), None)
        if g and g.get("logs"):
            log_id = g["logs"][0]["id"]
            old = tdb.get_log(log_id) or {}
            fields["image"] = old.get("image") or ""
            tdb.update_log(log_id, **fields)
            show_tip("已经更新")
        else:
            log_id = tdb.add_log(**fields)
            show_tip("已收进旅行日志")
        if state["pending"]:
            tdb.add_photos(log_id, state["pending"])
            state["pending"] = []
        state["view"].clear()
        state["idx"].clear()
        state["sel"] = hit[0] if hit else (title or city)
        refresh()

    def remove_log(e=None) -> None:
        sel = state["sel"]
        g = next((x for x in state["groups"] if x["key"] == sel), None)
        if not g:
            show_tip("先在左边选一个地方")
            return
        for log in g["logs"]:
            row = tdb.delete_log(log["id"])
            if row:
                _remove_image(row.get("image") or "")
                for ph in row.get("photos") or []:
                    _remove_image(ph.get("image") or "")
        show_tip(f"「{g['name']}」的记录已删除")
        state["sel"] = None
        state["view"].clear()
        state["idx"].clear()
        clear_form()
        refresh()

    # ---------------- 刷新 ----------------
    def refresh() -> None:
        state["groups"] = load_groups()
        paint_pending()
        paint_cards()
        paint_map(state["groups"])
        if state["sel"]:
            g = next((x for x in state["groups"] if x["key"] == state["sel"]), None)
            if g:
                fill_form(g)
        else:
            paint_locate()
            paint_saved([])
        safe_update()

    form_card = ft.Container(
        padding=12, border_radius=14, bgcolor=theme.CARD_BG,
        border=ft.Border.all(1, theme.LINE),
        content=ft.Column(spacing=9, controls=[
            ft.Row(spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                   controls=[
                icon_badge(ft.Icons.ADD_PHOTO_ALTERNATE_OUTLINED, 30,
                           theme.with_alpha(theme.ACCENT, 0.14), theme.ACCENT, 16),
                ft.Column(spacing=1, expand=True, controls=[
                    ft.Text("旅程记录", size=13.5,
                            weight=ft.FontWeight.W_700, color=theme.TEXT_MAIN),
                    ft.Text("同一地点自动归到一张卡片", size=10.5,
                            color=theme.TEXT_SUB, max_lines=1,
                            overflow=ft.TextOverflow.ELLIPSIS),
                ]),
                ft.IconButton(ft.Icons.CLOSE,tooltip="收起编辑（保留草稿）",icon_size=18,on_click=lambda e:toggle_editor(False)),
                ft.TextButton("清空", height=30, on_click=lambda e: (
                    clear_form(), safe_update())),
            ]),
            ft.FilledButton(
                "选择照片（可多选）", icon=ft.Icons.PHOTO_LIBRARY_OUTLINED,
                bgcolor=theme.ACCENT, color=theme.ON_ACCENT, height=38, elevation=0,
                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=11)),
                on_click=choose_photos),
            pending_hint,
            pending_grid,
            ft.Divider(height=1, color=theme.LINE),
            title_input,
            city_input,
            locate_text,
            ft.Row(spacing=8, controls=[
                date_input,
                ft.IconButton(ft.Icons.EVENT, icon_size=17,
                              icon_color=theme.MIST_BLUE_DEEP, tooltip="选择日期",
                              width=34, height=34, padding=0,
                              on_click=lambda e: open_calendar(page, date_picker, date_input.value)),
            ]),
            ft.Row(spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                   controls=[ft.Text("评分", size=12, color=theme.TEXT_SUB), rating_row]),
            note_input,
            ft.Row(spacing=8, controls=[
                ft.FilledButton(
                    tr("保存"), icon=ft.Icons.SAVE_OUTLINED, expand=True,
                    bgcolor=theme.ACCENT, color=theme.ON_ACCENT, height=38, elevation=0,
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=11)),
                    on_click=save_log),
                ft.TextButton("删除这个地方", icon=ft.Icons.DELETE_OUTLINE,
                              height=38, style=ft.ButtonStyle(color=theme.DANGER),
                              on_click=remove_log),
            ]),
            ft.Divider(height=1, color=theme.LINE),
            ft.Text("这个地方的照片", size=12, color=theme.TEXT_SUB),
            saved_grid,
        ]),
    )

    hint_text = ft.Text("滚轮缩放，放大地图会显示更多地名",
                        size=11, color=theme.TEXT_SUB, expand=True)
    hint_bar = ft.Container(
        padding=ft.Padding.symmetric(horizontal=14, vertical=9),
        border_radius=12, bgcolor=theme.CARD_BG_SOFT,
        border=ft.Border.all(1, theme.LINE),
        content=ft.Row(spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                       controls=[
            ft.Icon(ft.Icons.TOUCH_APP_OUTLINED, size=15, color=theme.TEXT_FAINT),
            hint_text,
        ]))

    center_area = ft.Container(
        expand=True,
        padding=ft.Padding.only(left=12, right=12, top=12, bottom=14),
        content=ft.Column(spacing=9, expand=True, controls=[
            ft.Row(spacing=8,controls=[
                ft.Text('足迹地图',size=16,weight=ft.FontWeight.W_600,color=theme.TEXT_MAIN),
                ft.Container(expand=True),
                ft.TextButton(tr('旅行手账'),icon=ft.Icons.MENU_BOOK_OUTLINED,on_click=lambda e:open_notebooks()),
                ft.IconButton(ft.Icons.EDIT_NOTE,tooltip='展开 / 收起记录',on_click=lambda e:toggle_editor()),
                ft.FilledButton('记录旅程',icon=ft.Icons.ADD,on_click=new_record,
                    bgcolor=theme.ACCENT,color=theme.ON_ACCENT)]),
            ft.Container(expand=True, alignment=ft.Alignment.CENTER,
                         content=map_holder),
            hint_bar,
        ]))

    left_panel = ft.Container(
        width=LEFT_W,
        padding=ft.Padding.only(left=14, right=8, top=16, bottom=16),
        content=ft.Column(spacing=11, expand=True, controls=[
            ft.Text('旅途收藏',size=16,weight=ft.FontWeight.W_600,color=theme.TEXT_MAIN),
            stats_text,
            search_input,
            ft.Divider(height=1,color=theme.LINE),
            card_list,
        ]))

    def open_notebooks():
        import travel_journal_view
        travel_journal_view.open_shelf(page, state['groups'], state['sel'])

    right_panel = ft.Container(
        width=RIGHT_W,visible=False,
        bgcolor=theme.CARD_BG_SOFT,
        border=ft.Border.only(left=ft.BorderSide(1, theme.LINE)),
        content=ft.ListView(spacing=12, padding=ft.Padding.all(14),
                            controls=[form_card]))

    # ---------------- 自动轮播 ----------------
    async def ticker() -> None:
        while alive():
            await asyncio.sleep(CAROUSEL_SECONDS)
            if not alive() or not state["active"] or state.get("hover"):
                continue
            changed = False
            for g in state.get("groups") or []:
                v = state["view"].get(g["key"])
                if v and v["n"] > 1:
                    state["idx"][g["key"]] = (state["idx"].get(g["key"], 0) + 1) % v["n"]
                    _paint_carousel(g["key"])
                    changed = True
            if changed:
                safe_update(card_list)

    page.run_task(ticker)

    fill_form(None)
    paint_locate()
    paint_pending()
    refresh()

    def on_show():
        state["active"] = True
        v = state.get("mapview")
        if v and (page.width or 1320) != state.get("window_width"):
            paint_map(state["groups"])
        state["window_width"] = page.width or 1320

    def on_hide():
        state["active"] = False
        if state["fs"]:
            close_fullscreen()

    return ft.Row(spacing=0, expand=True,
                  data={"on_resize": lambda: paint_map(state["groups"]),
                        "on_show": on_show, "on_hide": on_hide, "map_state": state},
                  controls=[left_panel, center_area, right_panel])

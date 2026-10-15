"""客行录 · 中国地图数据

    assets/map/china.json   省级边界 + 九段线（阿里云 DataV，已抽稀到 8000 多个点）
    assets/map/places.json  地名 → [经度, 纬度]（省 / 地级市 / 常用景点，900 多条）

坐标统一用经纬度（GCJ 近似 WGS84）。Projector 负责把经纬度换算成画布像素：
采用国内地图通行的等距圆柱投影（经纬度线性映射、保持高宽比），
形状和各家 App 里看到的中国地图一致。
"""

from __future__ import annotations

import functools
import json
import os
import sys

import flet as ft
import flet.canvas as cv


def _asset(rel: str) -> str:
    """资源路径：打包后从 _MEIPASS 读，开发时从项目目录读。"""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)


@functools.lru_cache(maxsize=1)
def china() -> dict:
    with open(_asset("assets/map/china.json"), encoding="utf-8") as f:
        return json.load(f)


@functools.lru_cache(maxsize=1)
def places() -> dict:
    with open(_asset("assets/map/places.json"), encoding="utf-8") as f:
        return json.load(f)


@functools.lru_cache(maxsize=1)
def bounds() -> tuple[float, float, float, float]:
    """整幅图（含九段线）的范围 (lon0, lat0, lon1, lat1)。"""
    data = china()
    lons: list[float] = []
    lats: list[float] = []
    for pv in data["provinces"]:
        for ring in pv["rings"]:
            for lon, lat in ring:
                lons.append(lon)
                lats.append(lat)
    return min(lons), min(lats), max(lons), max(lats)


MAIN_LAT_MIN = 18.2          # 主图下边界：海南岛以南的岛礁去插图里画
INSET_BBOX = (105.0, 3.0, 125.0, 22.5)   # 南海诸岛插图范围


@functools.lru_cache(maxsize=1)
def main_bbox() -> tuple[float, float, float, float]:
    """主图范围：只算纬度 18.2 以北的陆地，南海那一片丢给插图。"""
    data = china()
    lons: list[float] = []
    lats: list[float] = []
    for pv in data["provinces"]:
        for ring in pv["rings"]:
            if max(p[1] for p in ring) < MAIN_LAT_MIN:
                continue
            for lon, lat in ring:
                if lat >= MAIN_LAT_MIN:
                    lons.append(lon)
                    lats.append(lat)
    return min(lons), min(lats), max(lons), max(lats)


def _ring_split(ring: list) -> tuple[list, list]:
    """按纬度把一条环拆成（主图部分, 插图部分）。"""
    south = [p for p in ring if p[1] < MAIN_LAT_MIN]
    north = [p for p in ring if p[1] >= MAIN_LAT_MIN]
    if len(south) == len(ring):
        return [], ring
    if not south:
        return ring, []
    return north, ring


# ---------------- 地名解析 ----------------
_SUFFIXES = ("特别行政区", "维吾尔自治区", "壮族自治区", "回族自治区",
             "自治区", "自治州", "自治县", "地区", "盟", "省", "市", "县",
             "区", "镇", "乡", "街道")


def _strip_suffix(name: str) -> str:
    for s in _SUFFIXES:
        if name.endswith(s) and len(name) > len(s):
            return name[: -len(s)]
    return name


@functools.lru_cache(maxsize=512)
def resolve(text: str) -> tuple[str, float, float] | None:
    """把用户填的地名解析成 (规范名, 经度, 纬度)。

    顺序：原名精确匹配 → 去掉行政后缀匹配 → 取输入里能匹配到的最长地名
    （这样「杭州西湖」「云南大理古城」也能落到点上）。
    """
    raw = (text or "").strip().replace(" ", "")
    if not raw:
        return None
    table = places()

    for key in (raw, _strip_suffix(raw)):
        if key in table:
            lon, lat = table[key]
            return key, lon, lat

    best_key = ""
    for name, (lon, lat) in table.items():
        if len(name) >= 2 and name in raw and len(name) > len(best_key):
            best_key = name
    if best_key:
        lon, lat = table[best_key]
        return best_key, lon, lat

    # 反过来：用户只写了简称（如「西湖」而表里是「西湖区」）
    for name, (lon, lat) in table.items():
        if len(raw) >= 2 and raw in name:
            return name, lon, lat
    return None


def _in_ring(x: float, y: float, ring: list) -> bool:
    """射线法判断点是否在多边形内。"""
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if (yi > y) != (yj > y):
            if x < (xj - xi) * (y - yi) / (yj - yi) + xi:
                inside = not inside
        j = i
    return inside


@functools.lru_cache(maxsize=1024)
def province_of(lon: float, lat: float) -> str | None:
    """这个经纬度落在哪个省级行政区（用来点亮去过的省份）。"""
    for pv in china()["provinces"]:
        for ring in pv["rings"]:
            if len(ring) >= 3 and _in_ring(lon, lat, ring):
                return pv["name"]
    return None


# ---------------- 投影 ----------------
class Projector:
    """把经纬度换算成画布坐标，保持中国地图的高宽比。"""

    def __init__(self, width: float, height: float, pad: float = 8,
                 bbox: tuple[float, float, float, float] | None = None,
                 offset: tuple[float, float] = (0.0, 0.0)):
        lon0, lat0, lon1, lat1 = bbox or main_bbox()
        self.lon0, self.lat0, self.lon1, self.lat1 = lon0, lat0, lon1, lat1
        span_lon, span_lat = lon1 - lon0, lat1 - lat0
        ratio = span_lon / span_lat
        inner_w = max(10.0, width - pad * 2)
        inner_h = max(10.0, height - pad * 2)
        if inner_w / inner_h > ratio:          # 画布比地图宽 → 以高为准
            self.h = inner_h
            self.w = inner_h * ratio
        else:
            self.w = inner_w
            self.h = inner_w / ratio
        self.ox = offset[0] + (width - self.w) / 2
        self.oy = offset[1] + (height - self.h) / 2
        self.sx = self.w / span_lon
        self.sy = self.h / span_lat
        self.width = width
        self.height = height

    def __call__(self, lon: float, lat: float) -> tuple[float, float]:
        return (self.ox + (lon - self.lon0) * self.sx,
                self.oy + (self.lat1 - lat) * self.sy)

    def inside(self, x: float, y: float, margin: float = 6.0) -> bool:
        """点是否落在这张图的范围内（用来决定标记画在主图还是插图）。"""
        return (-margin <= x <= self.width + margin
                and -margin <= y <= self.height + margin)

    def shifted(self, dx: float, dy: float) -> "Projector":
        """复制一个只平移、不改变比例的投影器（画贴纸影子用）。"""
        out = Projector.__new__(Projector)
        out.__dict__.update(self.__dict__)
        out.ox += dx
        out.oy += dy
        return out


def _path_from_rings(rings: list, proj: Projector, paint: ft.Paint) -> cv.Path:
    elements: list[cv.Path.PathElement] = []
    for ring in rings:
        pts = [proj(lon, lat) for lon, lat in ring]
        if len(pts) < 3:
            continue
        elements.append(cv.Path.MoveTo(*pts[0]))
        for x, y in pts[1:]:
            elements.append(cv.Path.LineTo(x, y))
        elements.append(cv.Path.Close())
    return cv.Path(elements=elements, paint=paint)


def province_path(pv: dict, proj: Projector, paint: ft.Paint) -> cv.Path:
    """把一个省的所有环拼成一条 Path。"""
    return _path_from_rings(pv["rings"], proj, paint)


def mix(color: str, other: str, amount: float) -> str:
    """把两个颜色按比例混一下（amount 是 other 的占比）。"""
    a = color.lstrip("#")[-6:]
    b = other.lstrip("#")[-6:]
    out = []
    for i in (0, 2, 4):
        x = int(a[i:i + 2], 16)
        y = int(b[i:i + 2], 16)
        out.append(int(round(x + (y - x) * amount)))
    return "#%02X%02X%02X" % tuple(out)


@functools.lru_cache(maxsize=1)
def labels() -> list:
    """地图标注 [名称, 经度, 纬度, 层级]；层级 0=省 1=市 2=景点。"""
    try:
        with open(_asset("assets/map/labels.json"), encoding="utf-8") as f:
            return json.load(f)
    except OSError:
        return []


@functools.lru_cache(maxsize=1)
def _prov_boxes() -> dict:
    """每个省的经纬度外框，用来做视野裁剪。"""
    out = {}
    for pv in china()["provinces"]:
        lons = [p[0] for r in pv["rings"] for p in r]
        lats = [p[1] for r in pv["rings"] for p in r]
        if lons:
            out[pv["name"]] = (min(lons), min(lats), max(lons), max(lats))
    return out


def _alpha(color: str, a: float) -> str:
    """加上透明度（Flet 的颜色是 #AARRGGBB，alpha 在最前面）。"""
    return "#%02X%s" % (max(0, min(255, int(round(a * 255)))),
                        color.lstrip("#")[-6:])


def build_overlay(proj, width: float, height: float,
                  visited: set[str], accent: str,
                  bbox: tuple[float, float, float, float]) -> ft.Control:
    """在瓦片底图上叠一层「去过的省份」高亮。

    proj 是任意可调用投影（经纬度 → 控件坐标），所以能直接套瓦片地图的 View。
    """
    lon0, lat0, lon1, lat1 = bbox
    boxes = _prov_boxes()
    fill = ft.Paint(style=ft.PaintingStyle.FILL,
                    color=_alpha(mix(accent, "#FFFFFF", 0.30), 0.30),
                    anti_alias=True)
    line = ft.Paint(style=ft.PaintingStyle.STROKE,
                    color=_alpha(accent, 0.70), stroke_width=1.4,
                    anti_alias=True, stroke_join=ft.StrokeJoin.ROUND)
    shapes: list[cv.Shape] = []
    for pv in china()["provinces"]:
        if pv["name"] not in visited:
            continue
        bx = boxes.get(pv["name"])
        if bx and (bx[2] < lon0 or bx[0] > lon1
                   or bx[3] < lat0 or bx[1] > lat1):
            continue
        rings = []
        for r in pv["rings"]:
            rl = [p[0] for p in r]
            rt = [p[1] for p in r]
            if (max(rl) < lon0 or min(rl) > lon1
                    or max(rt) < lat0 or min(rt) > lat1):
                continue
            rings.append(r)
        if not rings:
            continue
        shapes.append(_path_from_rings(rings, proj, fill))
        shapes.append(_path_from_rings(rings, proj, line))
    canvas = cv.Canvas(shapes=shapes, width=width, height=height)
    return ft.Container(width=width, height=height, content=canvas)


def view_box(zoom: float, center: tuple[float, float] | None = None
             ) -> tuple[float, float, float, float]:
    """按缩放倍数从整幅图里取一个窗口，并限制不要跑出去太远。"""
    lon0, lat0, lon1, lat1 = main_bbox()
    span_lon, span_lat = lon1 - lon0, lat1 - lat0
    zoom = max(1.0, min(6.0, zoom))
    cx, cy = center if center else (lon0 + span_lon * 0.54,
                                    lat0 + span_lat * 0.46)
    half_lon, half_lat = span_lon / zoom / 2, span_lat / zoom / 2
    pad_lon, pad_lat = span_lon * 0.04, span_lat * 0.04
    cx = max(lon0 + half_lon - pad_lon, min(lon1 - half_lon + pad_lon, cx))
    cy = max(lat0 + half_lat - pad_lat, min(lat1 - half_lat + pad_lat, cy))
    if zoom <= 1.001:                     # 没放大就完整显示
        return lon0, lat0, lon1, lat1
    return cx - half_lon, cy - half_lat, cx + half_lon, cy + half_lat


def label_level(zoom: float) -> int:
    """缩放越大，显示的地名层级越多。"""
    if zoom >= 2.6:
        return 2
    if zoom >= 1.7:
        return 1
    return 0


CAPITALS = {
    "北京", "天津", "上海", "重庆", "石家庄", "太原", "呼和浩特", "沈阳",
    "长春", "哈尔滨", "南京", "杭州", "合肥", "福州", "南昌", "济南",
    "郑州", "武汉", "长沙", "广州", "南宁", "海口", "成都", "贵阳",
    "昆明", "拉萨", "西安", "兰州", "西宁", "银川", "乌鲁木齐", "香港",
    "澳门", "台北",
}


def _round_rect(x: float, y: float, w: float, h: float, r: float,
                paint: ft.Paint) -> cv.Path:
    """圆角矩形（画布没有现成的圆角矩形，用四段圆弧拼）。"""
    import math
    r = max(0.0, min(r, w / 2, h / 2))
    el: list[cv.Path.PathElement] = []
    corners = [(x + w - r, y + r, -90, 0), (x + w - r, y + h - r, 0, 90),
               (x + r, y + h - r, 90, 180), (x + r, y + r, 180, 270)]
    el.append(cv.Path.MoveTo(x + r, y))
    for cx, cy, a0, a1 in corners:
        steps = 6
        for i in range(steps + 1):
            a = math.radians(a0 + (a1 - a0) * i / steps)
            el.append(cv.Path.LineTo(cx + r * math.cos(a), cy + r * math.sin(a)))
    el.append(cv.Path.Close())
    return cv.Path(elements=el, paint=paint)


def build_map(width: float, height: float,
              visited: set[str] | None = None,
              accent: str = "#007AFF",
              zoom: float = 1.0,
              center: tuple[float, float] | None = None,
              show_labels: bool = True,
              sea_top: str = "#F1F9FE",
              sea_bottom: str = "#D5E9F8",
              land_top: str = "#FFFFFF",
              land_bottom: str = "#F3F9FF",
              border: str = "#DCE9F5",
              grid: str = "#E3EFF9",
              shadow: str = "#8FB6D6",
              ink: str = "#5A7A96",
              panel: str = "#8CFFFFFF",
              dash_color: str = "#7FA6C6",
              radius: float = 20,
              inset: bool = True) -> tuple[ft.Control, Projector]:
    """画中国地图，返回（控件, 主图投影器）。

    层次从下往上叠：海面渐变 → 经纬网 → 陆地投影 → 陆地渐变填充
    → 去过的省份（主题色渐变）→ 省界细线 → 地名 → 右下角南海诸岛。
    zoom / center 决定视野，labels 按层级逐步显现。
    """
    visited = visited or set()
    view = view_box(zoom, center)
    vx0, vy0, vx1, vy1 = view
    level = label_level(zoom)

    inset_w = min(146.0, width * 0.23) if inset else 0.0
    inset_h = min(168.0, height * 0.33) if inset else 0.0
    main_h = height - inset_h * 0.5 if inset else height
    ix, iy = width - inset_w - 16, height - inset_h - 14

    main = Projector(width, main_h, pad=10, bbox=view)
    ins = (Projector(inset_w, inset_h, pad=14, bbox=INSET_BBOX,
                     offset=(ix, iy)) if inset else None)

    shapes: list[cv.Shape] = []

    # 经纬网
    grid_paint = ft.Paint(style=ft.PaintingStyle.STROKE, color=grid,
                          stroke_width=0.9, anti_alias=True)
    lon = int(vx0 // 10 * 10) + 10
    while lon < vx1:
        x = main(lon, vy0)[0]
        shapes.append(cv.Path(
            elements=[cv.Path.MoveTo(x, 0), cv.Path.LineTo(x, height)],
            paint=grid_paint))
        lon += 10
    lat = int(vy0 // 5 * 5) + 5
    while lat < vy1:
        y = main(vx0, lat)[1]
        shapes.append(cv.Path(
            elements=[cv.Path.MoveTo(0, y), cv.Path.LineTo(width, y)],
            paint=grid_paint))
        lat += 5

    land_paint = ft.Paint(
        style=ft.PaintingStyle.FILL, anti_alias=True,
        gradient=ft.PaintLinearGradient(
            begin=ft.Alignment.TOP_CENTER, end=ft.Alignment.BOTTOM_CENTER,
            colors=[land_top, land_bottom]))
    hot_paint = ft.Paint(
        style=ft.PaintingStyle.FILL, anti_alias=True,
        gradient=ft.PaintLinearGradient(
            begin=ft.Alignment.TOP_LEFT, end=ft.Alignment.BOTTOM_RIGHT,
            colors=[mix(accent, "#FFFFFF", 0.58),
                    mix(accent, "#FFFFFF", 0.08)]))
    halo_paint = ft.Paint(style=ft.PaintingStyle.STROKE,
                          color=mix(shadow, sea_bottom, 0.80),
                          stroke_width=15, anti_alias=True,
                          stroke_join=ft.StrokeJoin.ROUND)
    border_paint = ft.Paint(style=ft.PaintingStyle.STROKE, color=border,
                            stroke_width=1.0, anti_alias=True,
                            stroke_join=ft.StrokeJoin.ROUND)
    dash_line = ft.Paint(style=ft.PaintingStyle.STROKE, color=dash_color,
                         stroke_width=1.8, anti_alias=True,
                         stroke_join=ft.StrokeJoin.ROUND,
                         stroke_cap=ft.StrokeCap.ROUND)

    halo_proj = main.shifted(0.0, 6.0 * min(zoom, 2.2))
    boxes = _prov_boxes()
    halo: list[cv.Shape] = []
    fills: list[cv.Shape] = []
    edges: list[cv.Shape] = []
    south_rings: list[list] = []

    for pv in china()["provinces"]:
        bx = boxes.get(pv["name"])
        if bx and (bx[2] < vx0 or bx[0] > vx1 or bx[3] < vy0 or bx[1] > vy1):
            continue                       # 视野外，不用画
        on = pv["name"] in visited
        north_rings, south = [], []
        for ring in pv["rings"]:
            rl = [p[0] for p in ring]
            rt = [p[1] for p in ring]
            if (max(rl) < vx0 or min(rl) > vx1
                    or max(rt) < vy0 or min(rt) > vy1):
                continue
            if max(rt) < MAIN_LAT_MIN:
                south.append(ring)
            else:
                north_rings.append([p for p in ring
                                    if p[1] >= MAIN_LAT_MIN - 0.05])
        south_rings.extend(south)
        if north_rings:
            halo.append(_path_from_rings(north_rings, halo_proj, halo_paint))
            fills.append(_path_from_rings(north_rings, main,
                                          hot_paint if on else land_paint))
            edges.append(_path_from_rings(north_rings, main, border_paint))

    shapes.extend(halo)
    shapes.extend(fills)
    shapes.extend(edges)

    # 地名
    if show_labels:
        # 先占住界面上的元素（标题、缩放按钮、图例、南海插图），地名不往上压
        placed: list[tuple[float, float, float, float]] = [
            (10, 6, 232, 74),                       # 标题
            (width - 62, 6, width - 6, 140),        # 缩放按钮
            (10, height - 62, 200, height - 6),     # 图例
        ]
        if ins is not None:
            placed.append((ix - 4, iy - 4, ix + inset_w + 4, iy + inset_h + 4))

        def _fits(r):
            return not any(r[0] < p[2] and r[2] > p[0]
                           and r[1] < p[3] and r[3] > p[1] for p in placed)

        boxes_lbl = _prov_boxes()
        # 大省先占位，小地方再往旁边挪一挪，尽量都能标出来
        order = sorted(
            labels(),
            key=lambda it: (it[3],
                            0 if (it[3] == 0 or it[0] in CAPITALS) else 1,
                            -(lambda b: (b[2] - b[0]) * (b[3] - b[1]))(
                                boxes_lbl.get(it[0], (0, 0, 0, 0)))))
        for name, lon_, lat_, lv in order:
            if lv > level:
                continue
            x, y = main(lon_, lat_)
            if not (4 < x < width - 4 and 4 < y < main_h - 4):
                continue
            size = 12.0 if lv == 0 else (10.0 if lv == 1 else 9.0)
            tw = len(name) * size * 1.12 + 4
            th = size * 1.45
            tries = ([(0, 0), (0, -16), (0, 16), (18, 0), (-18, 0),
                      (24, -14), (-24, 14)] if lv == 0
                     else [(0, 0), (0, -14), (0, 14)])
            spot = None
            for ox, oy in tries:
                rect = (x + ox - tw / 2, y + oy - th / 2,
                        x + ox + tw / 2, y + oy + th / 2)
                if _fits(rect):
                    spot = (x + ox, y + oy, rect)
                    break
            if spot is None:
                continue
            px, py, rect = spot
            placed.append(rect)
            lit = (any(v.startswith(name) for v in visited) if lv == 0
                   else province_of(lon_, lat_) in visited)
            shapes.append(cv.Text(
                x=px - tw / 2, y=py - th / 2, value=name,
                max_lines=1, text_align=ft.TextAlign.LEFT,
                style=ft.TextStyle(
                    size=size,
                    color="#FFFFFF" if lit else
                    ("#3C5A78" if lv == 0 else "#5E7C99"),
                    weight=ft.FontWeight.W_700 if lv == 0
                    else ft.FontWeight.W_500)))

    # 右下角：南海诸岛（圆角半透明面板，跟海面融在一起）
    if ins is not None:
        shapes.append(_round_rect(
            ix, iy, inset_w, inset_h, 12,
            ft.Paint(style=ft.PaintingStyle.FILL, color=panel,
                     anti_alias=True)))
        shapes.append(_round_rect(
            ix, iy, inset_w, inset_h, 12,
            ft.Paint(style=ft.PaintingStyle.STROKE, color="#C3DBEC",
                     stroke_width=0.9, anti_alias=True)))
        if south_rings:
            shapes.append(_path_from_rings(south_rings, ins, land_paint))
            shapes.append(_path_from_rings(south_rings, ins, border_paint))
        for ring in china().get("jiuduan", []):
            shapes.append(_path_from_rings([ring], ins, dash_line))
        shapes.append(cv.Text(
            x=ix + 9, y=iy + 6, value="南海诸岛", max_lines=1,
            style=ft.TextStyle(size=9, color="#A3BACD")))

    canvas = cv.Canvas(shapes=shapes, width=width, height=height)
    box = ft.Container(
        width=width, height=height, border_radius=radius,
        gradient=ft.LinearGradient(begin=ft.Alignment.TOP_CENTER,
                                   end=ft.Alignment.BOTTOM_CENTER,
                                   colors=[sea_top, sea_bottom]),
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS, content=canvas)
    return box, main


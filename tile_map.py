"""客行录 · 瓦片地图底图

用高德的公开瓦片拼出底图，Web Mercator 投影。三个图层：

    标准     —— 矢量底图：道路、地名、POI、地铁线
    卫星     —— 卫星影像 + 路网地名叠加
    路网公交 —— 只叠路网和地名（含地铁线、站名），配一层浅底

缩放 3~18 级。18 级时一块瓦片约 150 米见方，村里的路都看得清。
瓦片是边用边下、由 Flutter 自己缓存的，缩放平移不会重复下载。
"""

from __future__ import annotations

import math

import flet as ft

TILE = 256
MIN_ZOOM, MAX_ZOOM = 1.0, 18.0
# The provider returns empty tiles below level 3. Zoom out by scaling level-3
# tiles instead, so a world overview still has an actual base map.
MIN_Z, MAX_Z = 3, 18

LAYER_KEYS = ["std", "sat", "road"]
LAYER_NAMES = {"std": "标准", "sat": "卫星", "road": "路网公交"}
LAYER_BG = {"std": "#EDF1F6", "sat": "#1B2430", "road": "#F5F8FB"}


def _sub(x: int, y: int) -> int:
    """高德的服务器轮询编号。"""
    return (x + y) % 4 + 1


def _overlay(x: int, y: int, z: int) -> str:
    n = _sub(x, y)
    return (f"https://wprd0{n}.is.autonavi.com/appmaptile?lang=zh_cn"
            f"&size=1&style=8&x={x}&y={y}&z={z}")


def tile_srcs(layer: str, x: int, y: int, z: int) -> list[str]:
    """这一格的图片地址（可能有两张：底图 + 叠加层）。"""
    n = _sub(x, y)
    if layer == "sat":
        return [f"https://webst0{n}.is.autonavi.com/appmaptile?style=6"
                f"&x={x}&y={y}&z={z}", _overlay(x, y, z)]
    if layer == "road":
        return [_overlay(x, y, z)]
    return [f"https://webrd0{n}.is.autonavi.com/appmaptile?lang=zh_cn"
            f"&size=1&scale=1&style=8&x={x}&y={y}&z={z}"]


# ---------------- 投影 ----------------
def lonlat_to_tile(lon: float, lat: float, z: int) -> tuple[float, float]:
    """经纬度 → 瓦片坐标（带小数）。"""
    n = 2 ** z
    lat = max(-85.05112878, min(85.05112878, lat))
    r = math.radians(lat)
    return ((lon + 180.0) / 360.0 * n,
            (1.0 - math.log(math.tan(r) + 1.0 / math.cos(r)) / math.pi) / 2.0 * n)


def tile_to_lonlat(fx: float, fy: float, z: int) -> tuple[float, float]:
    n = 2 ** z
    lon = fx / n * 360.0 - 180.0
    lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * fy / n))))
    return lon, lat


class View:
    """当前视口：把经纬度换算成控件坐标，也能反算回来。"""

    def __init__(self, width: float, height: float,
                 lon: float, lat: float, zoom: float):
        self.width, self.height = width, height
        self.lon, self.lat = lon, lat
        self.zoom = max(MIN_ZOOM, min(MAX_ZOOM, zoom))
        self.z = max(MIN_Z, min(MAX_Z, int(round(self.zoom))))
        self.scale = 2 ** (self.zoom - self.z)     # 小数级缩放
        self.tile = TILE * self.scale
        self.cx, self.cy = lonlat_to_tile(lon, lat, self.z)

    def __call__(self, lon: float, lat: float) -> tuple[float, float]:
        fx, fy = lonlat_to_tile(lon, lat, self.z)
        return ((fx - self.cx) * self.tile + self.width / 2,
                (fy - self.cy) * self.tile + self.height / 2)

    def lonlat_at(self, x: float, y: float) -> tuple[float, float]:
        """控件坐标 → 经纬度（拖拽、以鼠标为中心缩放时用）。"""
        return tile_to_lonlat(self.cx + (x - self.width / 2) / self.tile,
                              self.cy + (y - self.height / 2) / self.tile,
                              self.z)

    def shifted(self, dx: float, dy: float) -> "View":
        """按屏幕位移平移，返回新的视口。"""
        lon, lat = self.lonlat_at(self.width / 2 - dx, self.height / 2 - dy)
        return View(self.width, self.height, lon, lat, self.zoom)

    def zoomed(self, new_zoom: float, anchor=None) -> "View":
        """以 anchor（控件坐标）为锚点缩放，锚点下的地物保持不动。"""
        new_zoom = max(MIN_ZOOM, min(MAX_ZOOM, new_zoom))
        if anchor is None:
            return View(self.width, self.height, self.lon, self.lat, new_zoom)
        alon, alat = self.lonlat_at(*anchor)
        nv = View(self.width, self.height, alon, alat, new_zoom)
        ax, ay = nv(alon, alat)
        clon, clat = nv.lonlat_at(nv.width / 2 + (ax - anchor[0]),
                                  nv.height / 2 + (ay - anchor[1]))
        return View(self.width, self.height, clon, clat, new_zoom)

    def tiles(self, margin: int = 0) -> list[tuple[int, int]]:
        """视口需要哪些瓦片。margin 是多铺几圈，拖动时不容易露白边。"""
        n = 2 ** self.z
        x0 = int(math.floor(self.cx - (self.width / 2) / self.tile)) - margin
        x1 = int(math.floor(self.cx + (self.width / 2) / self.tile)) + margin
        y0 = int(math.floor(self.cy - (self.height / 2) / self.tile)) - margin
        y1 = int(math.floor(self.cy + (self.height / 2) / self.tile)) + margin
        out = []
        for ty in range(max(0, y0), min(n - 1, y1) + 1):
            for tx in range(max(0, x0), min(n - 1, x1) + 1):
                out.append((tx, ty))
        return out

    def bbox(self) -> tuple[float, float, float, float]:
        """视口四角对应的 (lon0, lat0, lon1, lat1)。"""
        lon0, lat1 = self.lonlat_at(0, 0)
        lon1, lat0 = self.lonlat_at(self.width, self.height)
        return lon0, lat0, lon1, lat1

    def project_all(self, layer: str = "std",
                    margin: int = 0, pool: dict | None = None) -> list[ft.Control]:
        """铺瓦片。返回一堆绝对定位的 Image。"""
        out: list[ft.Control] = []
        for tx, ty in self.tiles(margin):
            left = (tx - self.cx) * self.tile + self.width / 2
            top = (ty - self.cy) * self.tile + self.height / 2
            for src in tile_srcs(layer, tx, ty, self.z):
                key = (src, tx, ty)
                image = pool.get(key) if pool is not None else None
                if image is None:
                    image = ft.Image(src=src, fit=ft.BoxFit.FILL,
                                     filter_quality=ft.FilterQuality.LOW,
                                     gapless_playback=True)
                    if pool is not None:
                        pool[key] = image
                image.left, image.top = left, top
                image.width = image.height = self.tile
                out.append(image)
        if pool is not None and len(pool) > 160:
            active = {id(c) for c in out}
            for key in list(pool):
                if id(pool[key]) not in active:
                    del pool[key]
                if len(pool) <= 160:
                    break
        return out


def scale_bar(view: View, max_width: float = 90) -> tuple[float, str]:
    """A readable 1/2/5 distance at the map's center latitude."""
    meters_per_pixel = 40075016.686 * math.cos(math.radians(view.lat)) / (TILE * 2 ** view.zoom)
    limit = meters_per_pixel * max_width
    base = 10 ** math.floor(math.log10(limit))
    distance = max(n * base for n in (1, 2, 5) if n * base <= limit)
    label = f"{distance / 1000:g} km" if distance >= 1000 else f"{distance:g} m"
    return distance / meters_per_pixel, label


def fit_view(width: float, height: float,
             bbox: tuple[float, float, float, float],
             pad: float = 0.94) -> View:
    """让 bbox 正好装进视口的初始视图。"""
    lon0, lat0, lon1, lat1 = bbox
    lo, hi = MIN_ZOOM, MAX_ZOOM
    for _ in range(28):
        mid = (lo + hi) / 2
        z = max(MIN_Z, min(MAX_Z, int(round(mid))))
        t = TILE * 2 ** (mid - z)
        w = (lonlat_to_tile(lon1, lat0, z)[0]
             - lonlat_to_tile(lon0, lat0, z)[0]) * t
        h = abs(lonlat_to_tile(lon0, lat1, z)[1]
                - lonlat_to_tile(lon0, lat0, z)[1]) * t
        if w <= width * pad and h <= height * pad:
            lo = mid
        else:
            hi = mid
    x0, y0 = lonlat_to_tile(lon0, lat0, 0)
    x1, y1 = lonlat_to_tile(lon1, lat1, 0)
    lon, lat = tile_to_lonlat((x0 + x1) / 2, (y0 + y1) / 2, 0)
    return View(width, height, lon, lat, lo)


def make_view(width: float, height: float, layer: str,
              lon: float | None = None, lat: float | None = None,
              zoom: float | None = None, bbox=None) -> View:
    """统一入口：给 bbox 就自动取景，否则按经纬度 + 缩放。"""
    if lon is None or lat is None or zoom is None:
        v = fit_view(width, height, bbox or (73.5, 18.2, 135.1, 53.6))
    else:
        v = View(width, height, lon, lat, zoom)
    v.layer = layer
    return v

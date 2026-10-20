"""
客行录 · 天气与定位

只用标准库 urllib，接口全部免费免密钥：
    whois.pconline.com.cn        国内 IP 定位（按运营商登记，中文城市/区县，最准）
    ip-api.com                   国外/备用 IP 定位（返回经纬度）
    geocoding-api.open-meteo.com  中文城市名搜索（本地地名库没有时兜底）
    api.open-meteo.com            实况 + 逐日天气预报（WMO 天气码）

城市搜索优先用随包内置的全国地名库 assets/cities_cn.json（省/市/区县 3700+ 条），
IP 定位再用经纬度就近吸附到同一个地名库，保证城市名和坐标一致。
联网失败时各函数返回 None / []，页面据此降级显示，不会卡住也不会崩。
"""

from __future__ import annotations

import json
import math
import os
import sys
import time
import urllib.parse
import urllib.request

import flet as ft

from database import DB_PATH

STORE_PATH = os.path.join(os.path.dirname(DB_PATH), "weather_city.json")

IP_API = ("http://ip-api.com/json/"
          "?lang=zh-CN&fields=status,country,regionName,city,lat,lon")
PCONLINE_API = "https://whois.pconline.com.cn/ipJson.jsp?json=true"
GEO_API = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_API = "https://api.open-meteo.com/v1/forecast"

CITIES_PATH = os.path.join(
    getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__))),
    "assets", "cities_cn.json")

TIMEOUT = 8
CACHE_TTL = 600          # 同一位置的天气 10 分钟内不再重复请求
IP_CACHE_TTL = 1800      # IP 定位 30 分钟内不重复请求
_cache: dict = {"key": None, "ts": 0.0, "data": None}
_ip_cache: dict = {"ts": 0.0, "data": None}
_cities: dict | None = None

_SUFFIXES = (
    "特别行政区", "维吾尔自治区", "壮族自治区", "回族自治区", "自治区",
    "自治州", "地区", "林区", "矿区", "特区", "县", "市", "区", "旗", "盟", "省",
)


def _load_cities() -> dict:
    """懒加载全国地名库：{名称: (经度, 纬度)}。"""
    global _cities
    if _cities is None:
        try:
            with open(CITIES_PATH, encoding="utf-8") as f:
                raw = json.load(f)
            _cities = {
                name: (float(v[0]), float(v[1]))
                for name, v in raw.items()
                if isinstance(v, list) and len(v) >= 2
            }
        except (OSError, ValueError, TypeError):
            _cities = {}
    return _cities


def _strip_suffix(name: str) -> str:
    """厦门市 / 阿克苏地区 / 广西壮族自治区 → 厦门 / 阿克苏 / 广西。"""
    result = name
    changed = True
    while changed:
        changed = False
        for suffix in _SUFFIXES:
            if len(result) > len(suffix) and result.endswith(suffix):
                result = result[:-len(suffix)]
                changed = True
                break
    return result


def _nearest_city(lat: float, lon: float) -> tuple[str, tuple[float, float]] | None:
    """把经纬度吸附到最近的地名（用于 IP 定位的坐标）。"""
    cities = _load_cities()
    if not cities:
        return None
    best, best_dist = None, float("inf")
    cos_lat = math.cos(math.radians(lat))
    for name, (clon, clat) in cities.items():
        dx = (clon - lon) * cos_lat
        dy = clat - lat
        dist = dx * dx + dy * dy
        if dist < best_dist:
            best_dist, best = dist, (name, (clon, clat))
    return best


# Open-Meteo 的 WMO 天气码 →（中文描述，图标）
WMO_CODES: dict[int, tuple[str, str]] = {
    0: ("晴", ft.Icons.WB_SUNNY),
    1: ("少云", ft.Icons.WB_SUNNY),
    2: ("多云", ft.Icons.WB_CLOUDY),
    3: ("阴", ft.Icons.CLOUD),
    45: ("雾", ft.Icons.FOGGY),
    48: ("雾凇", ft.Icons.FOGGY),
    51: ("毛毛雨", ft.Icons.GRAIN),
    53: ("细雨", ft.Icons.GRAIN),
    55: ("密集细雨", ft.Icons.GRAIN),
    56: ("雨凇", ft.Icons.GRAIN),
    57: ("强雨凇", ft.Icons.GRAIN),
    61: ("小雨", ft.Icons.WATER_DROP),
    63: ("中雨", ft.Icons.WATER_DROP),
    65: ("大雨", ft.Icons.WATER_DROP),
    66: ("冻雨", ft.Icons.WATER_DROP),
    67: ("强冻雨", ft.Icons.WATER_DROP),
    71: ("小雪", ft.Icons.SNOWING),
    73: ("中雪", ft.Icons.SNOWING),
    75: ("大雪", ft.Icons.SNOWING),
    77: ("米雪", ft.Icons.SNOWING),
    80: ("零星阵雨", ft.Icons.CLOUDY_SNOWING),
    81: ("阵雨", ft.Icons.CLOUDY_SNOWING),
    82: ("强阵雨", ft.Icons.CLOUDY_SNOWING),
    85: ("零星阵雪", ft.Icons.CLOUDY_SNOWING),
    86: ("强阵雪", ft.Icons.CLOUDY_SNOWING),
    95: ("雷阵雨", ft.Icons.THUNDERSTORM),
    96: ("雷阵雨伴冰雹", ft.Icons.THUNDERSTORM),
    99: ("强雷阵雨伴冰雹", ft.Icons.THUNDERSTORM),
}


def describe(code: int) -> tuple[str, str]:
    """天气码 →（中文描述，图标），未知码按「阴」处理。"""
    try:
        return WMO_CODES[int(code)]
    except (TypeError, ValueError, KeyError):
        return WMO_CODES[3]


def _get_json(url: str) -> dict | None:
    """GET 一个 JSON 接口，任何异常都吞掉返回 None。"""
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "Yingjianlu/1.0",
                          "Accept": "application/json"})
        from network_tls import https_context
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=https_context()) as resp:
            raw = resp.read()
            charset = (resp.headers.get_content_charset() or "utf-8").lower()
            # pconline 等国内接口返回 GBK，先按声明的编码解，失败再退回 gbk/utf-8。
            for encoding in (charset, "utf-8", "gbk"):
                try:
                    return json.loads(raw.decode(encoding))
                except (LookupError, UnicodeDecodeError):
                    continue
            return json.loads(raw.decode("utf-8", "replace"))
    except Exception:
        return None


def _locate_pconline() -> dict | None:
    """国内 IP：运营商登记地址，通常能精确到市/区县。"""
    data = _get_json(PCONLINE_API)
    if not isinstance(data, dict) or data.get("err"):
        return None
    city = (data.get("city") or "").strip()
    region = (data.get("region") or "").strip()
    province = (data.get("pro") or "").strip()
    cities = _load_cities()
    for candidate in (city, region):
        if candidate and candidate in cities:
            lon, lat = cities[candidate]
            return {"name": candidate, "region": province,
                    "lat": lat, "lon": lon}
    for candidate in (city, region):
        if not candidate:
            continue
        target = _strip_suffix(candidate)
        for name, (lon, lat) in cities.items():
            if _strip_suffix(name) == target:
                return {"name": name, "region": province,
                        "lat": lat, "lon": lon}
    return None


def _locate_ipapi() -> dict | None:
    """备用 IP 定位：返回经纬度，再就近吸附到地名库。"""
    data = _get_json(IP_API)
    if not data or data.get("status") != "success":
        return None
    if data.get("lat") is None or data.get("lon") is None:
        return None
    lat, lon = float(data["lat"]), float(data["lon"])
    hit = _nearest_city(lat, lon)
    if hit:
        name, (clon, clat) = hit
        return {"name": name, "region": data.get("regionName") or "",
                "lat": clat, "lon": clon}
    city = data.get("city") or data.get("regionName")
    if not city:
        return None
    return {"name": city, "region": data.get("regionName") or "",
            "lat": lat, "lon": lon}


def locate_ip() -> dict | None:
    """自动定位：优先国内运营商数据，失败再退回 ip-api；结果缓存 30 分钟。"""
    now = time.time()
    if _ip_cache["data"] and now - _ip_cache["ts"] < IP_CACHE_TTL:
        return dict(_ip_cache["data"])
    result = _locate_pconline() or _locate_ipapi()
    if result:
        _ip_cache.update(ts=now, data=result)
        return dict(result)
    return None


def search_city(name: str) -> list[dict]:
    """先查内置全国地名库（省/市/区县），没有再回退在线搜索。"""
    name = (name or "").strip()
    if not name:
        return []
    cities = _load_cities()
    if cities:
        q = name.lower()
        qs = _strip_suffix(q)
        scored = []
        for city, (lon, lat) in cities.items():
            cl = city.lower()
            cs = _strip_suffix(cl)
            if cl == q:
                rank = 0
            elif cs == qs:
                rank = 1
            elif cl.startswith(q):
                rank = 2
            elif q in cl:
                rank = 3
            else:
                continue
            scored.append((rank, len(city), city, lon, lat))
        if scored:
            scored.sort()
            return [{"name": c, "region": "", "country": "中国",
                     "lat": lat, "lon": lon}
                    for _, _, c, lon, lat in scored[:6]]
    url = f"{GEO_API}?{urllib.parse.urlencode({'name': name, 'count': 5, 'language': 'zh', 'format': 'json'})}"
    data = _get_json(url)
    out = []
    for item in (data or {}).get("results", []):
        admin = item.get("admin1") or ""
        if admin == item.get("name"):
            admin = ""
        out.append({
            "name": item.get("name", ""),
            "region": admin,
            "country": item.get("country", ""),
            "lat": float(item["latitude"]),
            "lon": float(item["longitude"]),
        })
    return out


def fetch(lat: float, lon: float) -> dict | None:
    """取实况 + 未来四天预报；10 分钟内直接走缓存。"""
    key = f"{lat:.3f},{lon:.3f}"
    if (_cache["key"] == key and _cache["data"]
            and time.time() - _cache["ts"] < CACHE_TTL):
        return _cache["data"]

    params = {
        "latitude": lat, "longitude": lon,
        "current": ("temperature_2m,apparent_temperature,relative_humidity_2m,"
                    "weather_code,wind_speed_10m"),
        "daily": "weather_code,temperature_2m_max,temperature_2m_min",
        "timezone": "auto", "forecast_days": 4,
    }
    data = _get_json(f"{FORECAST_API}?{urllib.parse.urlencode(params)}")
    cur = (data or {}).get("current") or {}
    daily = (data or {}).get("daily") or {}
    if cur.get("temperature_2m") is None:
        return None

    code = cur.get("weather_code") or 0
    text, icon = describe(code)
    days = []
    for i, date in enumerate(daily.get("time", [])[:4]):
        d_code = (daily.get("weather_code") or [0] * 4)[i]
        d_text, d_icon = describe(d_code)
        days.append({
            "date": date,
            "min": daily.get("temperature_2m_min", [None] * 4)[i],
            "max": daily.get("temperature_2m_max", [None] * 4)[i],
            "code": d_code, "text": d_text, "icon": d_icon,
        })

    result = {
        "temp": round(float(cur["temperature_2m"])),
        "feels": round(float(cur.get("apparent_temperature") or 0)),
        "humidity": cur.get("relative_humidity_2m"),
        "wind": cur.get("wind_speed_10m"),
        "code": code, "text": text, "icon": icon,
        "days": days,
    }
    _cache.update(key=key, ts=time.time(), data=result)
    return result


def load_city() -> dict | None:
    """读取用户手动选择的城市（没有则为 None，表示跟随 IP 自动定位）。"""
    try:
        with open(STORE_PATH, encoding="utf-8") as f:
            saved = json.load(f)
        if saved.get("name") and saved.get("lat") is not None:
            return saved
    except (OSError, ValueError):
        pass
    return None


def save_city(city: dict) -> None:
    try:
        with open(STORE_PATH, "w", encoding="utf-8") as f:
            json.dump(city, f, ensure_ascii=False)
    except OSError:
        pass


def clear_city() -> None:
    """恢复自动定位。"""
    try:
        os.remove(STORE_PATH)
    except OSError:
        pass

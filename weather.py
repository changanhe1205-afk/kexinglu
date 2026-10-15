"""客行录 · 天气与定位

只用标准库 urllib，接口全部免费免密钥：
    ip-api.com                    IP 定位（返回中文城市名 + 经纬度）
    geocoding-api.open-meteo.com  中文城市名搜索（可切换城市）
    api.open-meteo.com            实况 + 逐日天气预报（WMO 天气码）

联网失败时各函数返回 None / []，页面据此降级显示，不会卡住也不会崩。
"""

from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request

import flet as ft

from database import DB_PATH

STORE_PATH = os.path.join(os.path.dirname(DB_PATH), "weather_city.json")

IP_API = ("http://ip-api.com/json/"
          "?lang=zh-CN&fields=status,country,regionName,city,lat,lon")
GEO_API = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_API = "https://api.open-meteo.com/v1/forecast"

TIMEOUT = 8
CACHE_TTL = 600          # 同一位置的天气 10 分钟内不再重复请求
_cache: dict = {"key": None, "ts": 0.0, "data": None}

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
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def locate_ip() -> dict | None:
    """按公网 IP 猜测所在城市：{"name","region","lat","lon"}。"""
    data = _get_json(IP_API)
    if not data or data.get("status") != "success":
        return None
    city = data.get("city") or data.get("regionName")
    if not city or data.get("lat") is None:
        return None
    return {"name": city, "region": data.get("regionName") or "",
            "lat": float(data["lat"]), "lon": float(data["lon"])}


def search_city(name: str) -> list[dict]:
    """搜索中文城市名，返回候选 [{"name","region","lat","lon"}]（最多 5 条）。"""
    name = (name or "").strip()
    if not name:
        return []
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

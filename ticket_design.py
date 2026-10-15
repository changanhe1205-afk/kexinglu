"""票面独立于应用主题：统一坐标、字号与等比缩放，保存每张机票的样式。"""
from __future__ import annotations

import hashlib
import math
import re
import flet as ft
import flet.canvas as cv
from ticket_money import cny_price

AIR_STYLES = {
    "classic": "经典登机牌",
    "minimal": "黑白简约",
    "midnight": "午夜航空",
    "rose": "樱粉纸票",
    "digital": "电子登机牌",
}
RAIL_RATIO = 85 / 54


def normalize_style(value: str | None) -> str:
    return value if value in AIR_STYLES else "classic"


def dimensions(vehicle: str, style: str = "classic") -> tuple[float, float]:
    if vehicle != "飞机":
        return 600, 600 / RAIL_RATIO
    return (420, 540) if normalize_style(style) == "digital" else (720, 300)


class Paper:
    def __init__(self, width, natural_width, natural_height, bg, ink, sub, radius=8):
        self.scale = width / natural_width
        self.width, self.height = width, natural_height * self.scale
        self.bg, self.ink, self.sub, self.radius = bg, ink, sub, radius
        self.layers = []

    def box(self, x, y, w, h, bg=None, line=None, radius=0):
        s = self.scale
        self.layers.append(ft.Container(left=x*s, top=y*s, width=w*s, height=h*s,
            bgcolor=bg, border=ft.Border.all(max(.6, s), line) if line else None,
            border_radius=radius*s))

    def text(self, value, x, y, w, size=16, color=None, bold=False, align=ft.TextAlign.LEFT,
             lines=1, font="Microsoft YaHei UI"):
        s = self.scale
        self.layers.append(ft.Container(left=x*s, top=y*s, width=w*s,
            content=ft.Text(str(value or "—"), size=size*s, font_family=font,
                weight=ft.FontWeight.W_600 if bold else ft.FontWeight.W_400,
                color=color or self.ink, text_align=align, max_lines=lines,
                overflow=ft.TextOverflow.ELLIPSIS)))

    def icon(self, icon, x, y, size=20, color=None):
        s = self.scale
        self.layers.append(ft.Container(left=x*s, top=y*s,
            content=ft.Icon(icon, size=size*s, color=color or self.ink)))

    def line_art(self, points, color, thickness=1.5):
        s = self.scale
        self.layers.append(cv.Canvas(width=self.width, height=self.height, shapes=[
            cv.Path(elements=[cv.Path.MoveTo(points[0][0]*s, points[0][1]*s)] +
                    [cv.Path.LineTo(x*s,y*s) for x,y in points[1:]],
                    paint=ft.Paint(color=color, stroke_width=thickness*s,
                                   style=ft.PaintingStyle.STROKE, anti_alias=True))]))

    def dash(self, x, y, width, color):
        for at in range(0, int(width), 9):
            self.box(x+at, y, min(4, width-at), .8, color)

    def barcode(self, seed, x, y, width, height, color=None):
        # 纪念条纹，不编码乘车凭据或证件信息。
        digest = hashlib.sha256(str(seed).encode()).digest()
        step = width / 64
        for i in range(64):
            self.box(x+i*step, y, step*(.35 if digest[i % 32] & 1 else .7), height,
                     color or self.ink)

    def finish(self, kind):
        return ft.Container(width=self.width, height=self.height,
            data={"ticket_design": kind, "aspect": self.width/self.height},
            bgcolor=self.bg, border_radius=self.radius*self.scale,
            border=ft.Border.all(.8, "#26000000"),
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            shadow=ft.BoxShadow(blur_radius=24, spread_radius=-8,
                               color="#26000000", offset=ft.Offset(0, 10)),
            content=ft.Stack(controls=self.layers))


def _station(value, fallback):
    value = str(value or fallback).strip()
    return value[:-1] if value.endswith("站") else value


def _pinyin(value):
    from pypinyin import lazy_pinyin
    return " ".join(x.capitalize() for x in lazy_pinyin(value))


def _mask(value):
    value = str(value or "").strip()
    return value[:4] + "*" * max(4, len(value)-7) + value[-3:] if len(value) > 7 else "—"


def _seat(value, vehicle):
    text = str(value or "").strip()
    kinds = ("优选一等座", "商务座", "特等座", "一等座", "二等座", "高级软卧", "软卧", "硬卧", "软座", "硬座", "无座")
    kind = next((v for v in kinds if v in text), "二等座" if vehicle == "高铁" else "硬座")
    return text.replace(kind, "").strip() or "—", kind


def rail_ticket(t: dict, width=600, back=False) -> ft.Container:
    vehicle = t.get("vehicle") or "高铁"
    blue = vehicle == "高铁"
    bg, tint = ("#E9F3F9", "#DAEBF6") if blue else ("#F8E9E7", "#F0DAD6")
    p = Paper(width, 600, 600/RAIL_RATIO, bg, "#25313A", "#606F78", 7)
    p.box(0, 0, 600, 9, tint)
    p.box(0, 346, 600, 36, tint)
    p.dash(24, 345, 552, "#96ABB6" if blue else "#C0A09C")
    p.text("客行录 · 行程留念", 28, 354, 300, 11, p.sub)
    p.text(f"NO. {int(t.get('id') or 0):08d}", 410, 354, 162, 11, p.sub, align=ft.TextAlign.RIGHT)
    start, end = _station(t.get("from_city"), "出发站"), _station(t.get("to_city"), "到达站")
    if back:
        p.text("旅程备忘", 28, 28, 544, 22, bold=True)
        p.text(f"{start}  →  {end}    {t.get('code') or ''}", 28, 77, 544, 18)
        p.text(" · ".join(v for v in [t.get("depart_date"), t.get("depart_time"), t.get("passenger")] if v),
               28, 112, 544, 14, p.sub)
        p.box(28, 154, 544, 1, tint)
        p.text(t.get("note") or "还没有添加旅程备注。", 28, 179, 544, 17, lines=5)
        return p.finish("rail-back")
    p.text(f"KXL {int(t.get('id') or 0):08d}", 28, 24, 250, 14, "#A15454")
    gate = str(t.get("gate") or "—")
    p.text("检票口 " + gate, 370, 24, 202, 13, p.sub, align=ft.TextAlign.RIGHT)
    # 两站与车次共用一条基线；整段站名排版，不逐字拉开字距。
    for name, x, align in [(start, 28, ft.TextAlign.LEFT), (end, 388, ft.TextAlign.RIGHT)]:
        size = min(29, max(16, 178 / max(1, len(name))))
        p.text(name, x, 75, 184, size, bold=True, align=align)
        p.text(_pinyin(name), x, 116, 184, 10.5, p.sub, align=align)
    p.text(t.get("code"), 220, 78, 160, 22, bold=True, align=ft.TextAlign.CENTER)
    p.box(253, 118, 82, 1.3, p.ink)
    p.icon(ft.Icons.ARROW_RIGHT_ALT, 318, 107, 23)
    date = str(t.get("depart_date") or "日期待补")
    p.text(f"{date}  {t.get('depart_time') or '--:--'} 开", 28, 165, 330, 17)
    seat, kind = _seat(t.get("seat"), vehicle)
    p.text(seat, 373, 165, 199, 17, align=ft.TextAlign.RIGHT)
    price = str(t.get("price") or "—").lstrip("¥￥")
    try:
        price = f"{float(price):.2f}"
    except ValueError:
        pass
    p.text("¥ " + price, 28, 203, 250, 20)
    p.text(kind, 373, 205, 199, 16, align=ft.TextAlign.RIGHT)
    p.text("乘客  " + (t.get("passenger") or "旅客"), 28, 249, 280, 16)
    p.text(_mask(t.get("passenger_id")) if t.get("passenger_id") else "", 310, 249, 220, 15)
    p.box(28, 286, 420, 38, line="#A8BEC9" if blue else "#C8A9A3", radius=3)
    p.text("出发、抵达，以及这一路的记忆。", 39, 295, 399, 12, p.sub)
    p.barcode(t.get("id"), 482, 272, 90, 50)
    return p.finish("rail-blue" if blue else "rail-rose")


POSTER_THEMES = {
    "CA": ("山河，皆为序章", "从一座城出发，把辽阔留在心里。", "#8D2937", "mountain"),
    "MU": ("把城市，读成风景", "街角、天际线，还有抵达后的第一杯咖啡。", "#253F70", "city"),
    "CZ": ("向温暖处飞行", "让下一段故事，带一点南方的阳光。", "#176B8B", "coast"),
    "HU": ("把假期，交给海风", "从云端到海岸，慢一点也很好。", "#983D37", "coast"),
    "MF": ("沿着海岸，慢慢走", "收藏一片蓝，和一段自在的时光。", "#245E87", "coast"),
    "3U": ("下一站，山间烟火", "山川有回响，街巷有滋味。", "#9E3F35", "mountain"),
    "ZH": ("向新的天际线", "给日常留白，让远方发生。", "#8C3345", "city"),
    "FM": ("城市之间，有故事", "把短暂的停留，写成长久的记忆。", "#324E77", "city"),
    "9C": ("轻装，去看世界", "下一次出发，从一个小小的心愿开始。", "#426F42", "mountain"),
    "HO": ("愿每次抵达，都如意", "见想见的人，看惦记的风景。", "#89354A", "city"),
    "GJ": ("江南，值得慢读", "在山水之间，留下一页自己的故事。", "#807047", "mountain"),
    "KN": ("出发就有新故事", "把平常的一天，交给不一样的风景。", "#76425D", "city"),
    "GS": ("去赴一场远方之约", "从城市到山海，沿途都有惊喜。", "#925247", "city"),
    "SC": ("山海之间，遇见你", "沿着海风，寻找生活的另一种节奏。", "#365F80", "coast"),
    "TV": ("向高处，见辽阔", "把雪山的轮廓，收进旅行的这一页。", "#865E49", "mountain"),
    "PN": ("自由，是下一站", "走出熟悉的街道，找到自己的方向。", "#5D4C7F", "mountain"),
}


def airline_poster(t, style, width, palette):
    """Original destination-poster advertising treatment, not official offers."""
    code = (t.get("code") or "").strip().upper()
    headline, copy, brand, motif = POSTER_THEMES.get(code[:2],
        ("每次出发，都有新章", "把一路风景，留给未来的自己。", "#37596A", "mountain"))
    bg, ink, sub, tint = palette
    nw, nh = dimensions("飞机", style)
    p = Paper(width, nw, nh, bg, ink, sub, 16 if style == "digital" else 9)
    portrait = style == "digital"
    hw, hh = (nw, 312) if portrait else (490, nh)
    hero = tint if style in ("minimal", "rose") else brand
    fg = ink if style in ("minimal", "rose") else "#FFFFFF"
    faint = sub if style in ("minimal", "rose") else "#CFFFFFFF"
    p.box(0, 0, hw, hh, hero)
    p.text(t.get("_airline") or "飞行纪念", 28, 22, hw-56, 13, fg, bold=True)
    p.text("JOURNEY COLLECTION", 28, 52, hw-56, 9, faint)
    p.text(headline.replace("，", "\n"), 28, 80, hw-56, 30, fg, bold=True, lines=2)
    p.text(copy, 28, 166, hw-56, 11, faint, lines=2)
    # Fine line landscape, drawn from geometry rather than stock airline artwork.
    if motif == "mountain":
        p.line_art([(0,254),(78,216),(122,239),(191,199),(261,252),(344,217),(hw,264)], faint, 1.2)
        p.line_art([(0,275),(97,246),(170,271),(257,232),(336,258),(hw,240)], faint, .7)
    elif motif == "coast":
        for row in range(3):
            p.line_art([(x,231+row*15+math.sin(x/53)*7) for x in range(0,int(hw)+1,8)], faint, .9)
    else:
        points=[(0,262),(42,262),(42,230),(79,230),(79,250),(115,250),(115,211),
                (148,211),(148,262),(183,262),(183,236),(231,236),(231,205),
                (262,205),(262,257),(310,257),(310,227),(349,227),(349,262),(hw,262)]
        p.line_art(points, faint, 1.1)
    p.text("原创旅行海报 / 客行录", 28, hh-25, hw-56, 8, faint)
    x, y, w = (28, 334, nw-56) if portrait else (515, 24, nw-540)
    p.text("这一程 · 留给自己", x, y, w, 12, sub)
    p.text(t.get("to_city") or "下一站", x, y+30, w, 22, ink, bold=True, lines=2)
    p.text(f"{code or '航班待补'}  /  {t.get('depart_date') or '日期待补'}", x, y+88, w, 10, sub)
    p.box(x, y+113, w, .8, tint)
    p.text(t.get("note") or "收藏这张票根，也收藏抵达时的心情。", x, y+129, w, 12, ink,
           lines=3 if portrait else 5)
    p.text("FLIGHT MEMORIES", x, nh-25, w, 8, sub)
    return p.finish("air-"+style+"-back")


def boarding_pass(t: dict, style="classic", width=720, back=False) -> ft.Container:
    style = normalize_style(style)
    palettes = {
        "classic": ("#FFFEFA", "#203B60", "#718095", "#EAF0F7"),
        "minimal": ("#FFFFFF", "#22252B", "#717780", "#F0F1F3"),
        "midnight": ("#192537", "#EEF3FC", "#B1C0D6", "#273A53"),
        "rose": ("#FFF8F9", "#6D3849", "#9C6F7C", "#F3E0E6"),
        "digital": ("#F8FBFF", "#244567", "#708296", "#E4EEF8"),
    }
    bg, ink, sub, tint = palettes[style]
    nw, nh = dimensions("飞机", style)
    p = Paper(width, nw, nh, bg, ink, sub, 16 if style=="digital" else 9)
    code = str(t.get("code") or "—").upper()
    start, end = t.get("_from_code") or "—", t.get("_to_code") or "—"
    passenger = t.get("passenger") or "—"
    date, time = t.get("depart_date") or "—", t.get("depart_time") or "—"
    if back:
        return airline_poster(t, style, width, palettes[style])

    def field(label, value, x, y, w, size=18):
        p.text(label, x, y, w, 10, sub)
        p.text(value, x, y+19, w, size, bold=True)

    if style == "digital":
        p.box(0, 0, 420, 63, tint)
        p.text("登机牌", 28, 20, 250, 19, bold=True)
        p.text(code, 268, 23, 124, 16, bold=True, align=ft.TextAlign.RIGHT)
        p.text(start, 28, 97, 142, 41, bold=True)
        p.icon(ft.Icons.FLIGHT_TAKEOFF, 196, 117, 27, sub)
        p.text(end, 250, 97, 142, 41, bold=True, align=ft.TextAlign.RIGHT)
        p.text(t.get("from_city"), 28, 151, 174, 12, sub, lines=2)
        p.text(t.get("to_city"), 222, 151, 170, 12, sub, align=ft.TextAlign.RIGHT, lines=2)
        p.box(28, 209, 364, 1, tint)
        field("乘客 PASSENGER", passenger, 28, 235, 175)
        field("日期 DATE", date, 222, 235, 170, 16)
        field("出发 DEPARTURE", time, 28, 308, 110, 26)
        field("登机口 GATE", t.get("gate"), 164, 308, 96, 26)
        field("座位 SEAT", t.get("seat"), 284, 308, 108, 26)
        p.dash(28, 393, 364, sub)
        p.barcode(code+date, 50, 427, 320, 44)
        p.text(cny_price(t.get('price')), 28, 479, 364, 14, ink, align=ft.TextAlign.CENTER)
        p.text("客行录 · 行程留念", 28, 503, 364, 10, sub, align=ft.TextAlign.CENTER)
    elif style == "minimal":
        p.text("BOARDING PASS", 30, 23, 340, 13, bold=True)
        p.text(code, 540, 20, 150, 21, bold=True, align=ft.TextAlign.RIGHT)
        p.text(start, 28, 63, 225, 57, bold=True)
        p.icon(ft.Icons.ARROW_FORWARD, 338, 91, 29)
        p.text(end, 463, 63, 227, 57, bold=True, align=ft.TextAlign.RIGHT)
        p.text(t.get("from_city"), 30, 138, 310, 12, sub)
        p.text(t.get("to_city"), 380, 138, 310, 12, sub, align=ft.TextAlign.RIGHT)
        p.box(30, 171, 660, 1, "#C9CDD2")
        field("乘客", passenger, 30, 195, 155)
        field("出发日期", date, 199, 195, 151, 16)
        field("出发时间", time, 370, 195, 98)
        field("登机口", t.get("gate"), 479, 195, 89)
        field("座位", t.get("seat"), 587, 195, 103)
        p.text("客行录 · 行程留念", 30, 272, 330, 10, sub)
        p.text(cny_price(t.get('price')), 400, 268, 290, 14, ink, align=ft.TextAlign.RIGHT)
    else:
        p.box(0, 0, 720, 51, tint)
        p.text(t.get("_airline") or "登机牌", 26, 15, 390, 17, bold=True)
        p.text("BOARDING PASS", 543, 18, 151, 12, bold=True)
        p.box(520, 51, 200, 249, tint)
        for y in range(60, 292, 10):
            p.box(520, y, .8, 4, sub)
        p.text(start, 26, 76, 195, 43, bold=True)
        p.icon(ft.Icons.FLIGHT_TAKEOFF, 246, 93, 26, sub)
        p.text(end, 295, 76, 197, 43, bold=True, align=ft.TextAlign.RIGHT)
        p.text(t.get("from_city"), 26, 133, 214, 11, sub)
        p.text(t.get("to_city"), 278, 133, 214, 11, sub, align=ft.TextAlign.RIGHT)
        field("乘客 PASSENGER", passenger, 26, 174, 193, 16)
        field("航班 FLIGHT", code, 239, 174, 116, 16)
        field("日期 DATE", date, 365, 174, 133, 14)
        p.barcode(code+date, 26, 250, 240, 24)
        p.text(cny_price(t.get('price')), 290, 233, 204, 14, ink, align=ft.TextAlign.RIGHT)
        p.text("客行录 · 行程留念", 321, 260, 173, 9, sub, align=ft.TextAlign.RIGHT)
        field("出发 DEPARTURE", time, 547, 76, 147, 25)
        field("登机口 GATE", t.get("gate"), 547, 145, 147, 25)
        field("座位 SEAT", t.get("seat"), 547, 214, 147, 25)
    return p.finish("air-"+style)

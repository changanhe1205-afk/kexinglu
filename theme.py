"""客行录 · 视觉主题

集中管理配色、渐变、阴影与复用组件，全部模块共用山野绿、纸白与暖金的视觉语言。
主题（背景色 / 主题色）可在「我的」页修改，写入 data/settings.json，
模块全局变量即时生效——页面重建后自动应用。
"""

from __future__ import annotations

import json
import os
import sys

import flet as ft

from database import DB_PATH as _DB_PATH

SETTINGS_PATH = os.path.join(os.path.dirname(_DB_PATH), "settings.json")


def res(rel: str) -> str:
    """资源路径：打包成 exe 后从 _MEIPASS 读，开发时从项目目录读。"""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)

# ---------------- 主配色 ----------------
MIST_BLUE = "#548675"        # 松绿：主色，用于标题栏、按钮、强调
MIST_BLUE_DEEP = "#386858"   # 松绿加深：用于强调文字、次级按钮
MIST_BLUE_SOFT = "#E0EBE3"   # 松绿浅色：用于浅背景、封面渐变起点
SOFT_LEMON = "#D6B775"       # 暖金：点缀色，用于评分星星、"添加"按钮

# ---------------- 点缀色 ----------------
BLUSH_PINK = "#C88F8F"       # 樱粉：浪漫分类、柔和强调
BLUSH_PINK_SOFT = "#F5E8E5"
MINT_GREEN = "#86AF92"       # 薄荷绿：成功、家人分类
MINT_GREEN_SOFT = "#E5EFE5"
LAVENDER = "#A49BB9"         # 薰衣草紫：同学分类
LAVENDER_SOFT = "#EEEAF2"
APRICOT = "#CBA77F"          # 杏橙：工作分类 / 搜索命中高亮
APRICOT_SOFT = "#F3EBDD"
SKY_CYAN = "#739CA1"         # 天青：其他分类
SKY_CYAN_SOFT = "#E5EEED"
DANGER = "#BE7170"           # 柔和的删除红
DANGER_SOFT = "#F8E9E6"

# ---------------- 中性色（纸白与墨绿） ----------------
BG = "#F7F6F2"               # 纸白底色
BG_DEEP = "#EBEDE5"          # 渐变末端底色
CARD_BG = "#FFFFFF"          # 卡片底色
CARD_BG_SOFT = "#F3F4EE"     # 次级卡片底
TEXT_MAIN = "#243B34"        # 墨绿主文字
TEXT_SUB = "#697A71"         # 灰绿次要文字
TEXT_FAINT = "#859289"       # 占位 / 极弱文字
LINE = "#DDE3DA"             # 分割线、卡片描边（发丝级）
LINE_SOFT = "#EBEEE6"        # 更浅的分割线
ACCENT = "#387363"           # 山野绿：主按钮、选中态
SHADOW = "#14243B34"         # 卡片阴影（前两位是透明度）
SHADOW_DEEP = "#29243B34"    # 较重阴影（悬浮）
STAR_OFF = "#D2D9CD"         # 未点亮的星星
SEARCH_HIT = "#AC7544"       # 搜索命中的关键字颜色

RADIUS = 18                  # 统一卡片圆角

# ---------------- 字体 ----------------
# 不指定字体时 Flutter 会拿 Roboto 去渲染，中文字符只能逐字回退到系统字体，
# 加粗（W_700 / W_800）就变成"伪粗体"，笔画粗细不匀、还会出现缺口。
# 显式指定微软雅黑（自带 Regular / Bold 两套字重），中英文就统一了。
FONT_FAMILY = "Microsoft YaHei UI"
FONT_FALLBACK = ["Microsoft YaHei", "PingFang SC", "Noto Sans SC",
                 "Source Han Sans SC", "SimHei", "sans-serif"]


def with_alpha(color: str, alpha: float) -> str:
    """给任意色值叠一个透明度，返回 Flet 的 #AARRGGBB。

    alpha 取 0~1；color 支持 "#RRGGBB" 与已带透明度的 "#AARRGGBB"。
    """
    hex_part = color.lstrip("#")
    if len(hex_part) == 8:            # 已经是 AARRGGBB，丢掉原来的透明度
        hex_part = hex_part[2:]
    a = max(0, min(255, int(round(alpha * 255))))
    return f"#{a:02X}{hex_part.upper()}"

# ---------------- 分类视觉 ----------------
# 每个分类对应一组（主色，浅底色），循环取用，让分类更有辨识度。
CATEGORY_COLORS = [
    (MIST_BLUE, MIST_BLUE_SOFT),
    (BLUSH_PINK, BLUSH_PINK_SOFT),
    (MINT_GREEN, MINT_GREEN_SOFT),
    (LAVENDER, LAVENDER_SOFT),
    (APRICOT, APRICOT_SOFT),
    (SKY_CYAN, SKY_CYAN_SOFT),
]
CATEGORY_ICONS = {
    "朋友": ft.Icons.FAVORITE_BORDER,
    "家人": ft.Icons.HOLIDAY_VILLAGE_OUTLINED,
    "同学": ft.Icons.SCHOOL_OUTLINED,
    "工作": ft.Icons.WORK_OUTLINE,
    "其他": ft.Icons.CHAT_BUBBLE_OUTLINE,
    "未分类": ft.Icons.BOOKMARK_BORDER,
    "全部": ft.Icons.INBOX_OUTLINED,
}


def category_colors(name: str) -> tuple[str, str]:
    """按分类名稳定地取一组颜色（同名永远同色）。"""
    name = name or "未分类"
    total = sum(ord(ch) for ch in name)
    return CATEGORY_COLORS[total % len(CATEGORY_COLORS)]


# ---------------- 液态玻璃（macOS 风格浅色磨砂） ----------------
GLASS_BAR = "#BCF7F6F2"       # 顶栏 / 导航：浅色磨砂（72% 透明）
GLASS_PILL = "#0A000000"      # 玻璃上的极浅灰药丸
GLASS_BORDER = "#1A000000"    # 发丝级描边
GLASS_TEXT_DIM = "#697A71"    # 玻璃上的次级文字

# 内容页（首页以外）铺在背景图上的柔化纱罩：背景图退成一层淡淡的色调，
# 浅色卡片因此有了干净的落点，文字对比度也稳定。
VEIL = "#EFF7F6F2"            # 约 87% 不透明：背景图案退成一抹色调
VEIL_BLUR = 42                # 纱罩背后的模糊半径

# 浅色玻璃卡片：比纯白轻一点，能透出背后纱罩的色调
CARD_GLASS = "#F4FFFEFA"
CARD_GLASS_SOFT = "#D9F7F8F2"
CARD_GLASS_LINE = "#18243B34"


def glass_surface() -> dict:
    """给 Container 用的 macOS 磨砂参数：浅色半透明底 + 背景模糊。"""
    return dict(bgcolor=GLASS_BAR, blur=ft.Blur(30, 30))


def glass_card(*controls, padding: float = 20, spacing: float = 14,
               radius: float = RADIUS) -> ft.Container:
    """浅色磨砂卡片：半透明白底 + 背景模糊 + 发丝描边 + 柔和投影。

    内容页统一用它，卡片之间才有一致的厚度感。
    """
    return ft.Container(
        padding=padding, border_radius=radius, bgcolor=CARD_GLASS,
        border=ft.Border.all(1, CARD_GLASS_LINE), blur=ft.Blur(24, 24),
        shadow=card_shadow(),
        content=ft.Column(spacing=spacing, controls=list(controls)),
    )


# 完整主题：页面底色、表面、文字、边框、强调色、首页与玻璃均由同一套数据派生。
THEMES = {
    "classic": dict(name="经典雾蓝", accent="#4C78A8", bg="#F3F5F8", deep="#E7ECF3",
                    card="#FFFFFF", soft="#F7F9FC", text="#202B3A", sub="#627084", line="#DDE3EB",
                    dark=False, home="#182539", background="assets/home_bg.jpg"),
    "graphite": dict(name="石墨灰", accent="#576373", bg="#F2F3F5", deep="#E5E7EB",
                     card="#FFFFFF", soft="#F7F7F8", text="#252A31", sub="#646C78", line="#DCDDE2",
                     dark=False, home="#222831", background="assets/home_bg.jpg"),
    "sand": dict(name="暖砂", accent="#996D48", bg="#F6F2ED", deep="#ECE4DA",
                 card="#FFFCF8", soft="#F5EFE7", text="#392F29", sub="#79695B", line="#E4D9CB",
                 dark=False, home="#352920", background="assets/bg_warm.jpg"),
    "lilac": dict(name="浅紫", accent="#8068A8", bg="#F3F1F7", deep="#E7E2F0",
                  card="#FDFBFF", soft="#F3EFF8", text="#322B40", sub="#746980", line="#DFD8E9",
                  dark=False, home="#292337", background="assets/home_bg.jpg"),
    "midnight": dict(name="午夜蓝", accent="#8BB2E5", bg="#141C2A", deep="#0E1623",
                     card="#1D293B", soft="#233147", text="#E7EDF7", sub="#AFBED3", line="#34435A",
                     dark=True, home="#0B1629", background="assets/home_bg.jpg"),
    "carbon": dict(name="深色石墨", accent="#B6BEC9", bg="#1A1C20", deep="#101215",
                   card="#25282E", soft="#2C3037", text="#EBEDF1", sub="#B0B5BE", line="#41454F",
                   dark=True, home="#15171C", background="assets/home_bg.jpg"),
    "sea": dict(name="海盐青",accent="#3D7B83",bg="#EFF5F4",deep="#DCE9E7",
                card="#FAFDFC",soft="#E8F1EF",text="#233A3E",sub="#617B7C",line="#CDDEDB",
                dark=False,home="#173C48",background="assets/backgrounds/sea.svg"),
    "sage": dict(name="鼠尾草",accent="#587765",bg="#F1F4EE",deep="#DFE7DA",
                 card="#FCFDF9",soft="#EAF0E5",text="#2D3B31",sub="#687966",line="#D4DECE",
                 dark=False,home="#263E34",background="assets/backgrounds/forest.svg"),
    "clay": dict(name="陶土暖白",accent="#A36B54",bg="#F7F2EE",deep="#ECDFD6",
                 card="#FFFDF9",soft="#F5EBE3",text="#42332D",sub="#836F64",line="#E4D6CC",
                 dark=False,home="#493A32",background="assets/backgrounds/dunes.svg"),
    "plum": dict(name="暮色紫",accent="#C0A9D0",bg="#25212D",deep="#1A1722",
                 card="#302B3A",soft="#393243",text="#EFE8F3",sub="#C0B1CA",line="#51455E",
                 dark=True,home="#282435",background="assets/backgrounds/sunset.svg"),
    "ocean": dict(name="深海青",accent="#8CC8C0",bg="#14292D",deep="#0D1E24",
                  card="#1D363C",soft="#274149",text="#E6F2F0",sub="#A7C2C2",line="#39555B",
                  dark=True,home="#102630",background="assets/backgrounds/stars.svg"),
    "coffee": dict(name="可可夜色",accent="#D2B28E",bg="#2B2622",deep="#1D1917",
                   card="#38312B",soft="#443B33",text="#F3ECE3",sub="#C1B1A0",line="#5A4C40",
                   dark=True,home="#2A2520",background="assets/backgrounds/paper.svg"),
}
THEME_ID = "classic"
DARK = False


def mix(color: str, base: str, amount: float) -> str:
    a, b = color[-6:], base[-6:]
    return "#" + "".join(f"{round(int(a[i:i+2],16)*amount + int(b[i:i+2],16)*(1-amount)):02X}"
                         for i in (0, 2, 4))


def _apply(preset: str, accent: str | None = None) -> None:
    p = THEMES.get(preset, THEMES["classic"])
    ac = accent or p["accent"]
    dark = p["dark"]
    values = dict(THEME_ID=preset if preset in THEMES else "classic", DARK=dark,
                  BG=p["bg"], BG_DEEP=p["deep"], CARD_BG=p["card"], CARD_BG_SOFT=p["soft"],
                  TEXT_MAIN=p["text"], TEXT_SUB=p["sub"], TEXT_FAINT=p["sub"],
                  LINE=p["line"], LINE_SOFT=mix(p["line"], p["card"], .5), ACCENT=ac,
                  ON_ACCENT="#142033" if dark else "#FFFFFF",
                  MIST_BLUE=ac, MIST_BLUE_DEEP=ac,
                  MIST_BLUE_SOFT=mix(ac, p["card"], .16 if dark else .10),
                  VEIL=with_alpha(p["bg"], .96), GLASS_BAR=with_alpha(p["card"], .82),
                  GLASS_BORDER=p["line"], GLASS_TEXT_DIM=p["sub"],
                  GLASS_PILL=with_alpha(ac, .10),
                  CARD_GLASS=with_alpha(p["card"], .97),
                  CARD_GLASS_SOFT=with_alpha(p["soft"], .94), CARD_GLASS_LINE=p["line"],
                  SHADOW="#24000000" if dark else "#120F172A",
                  SHADOW_DEEP="#48000000" if dark else "#200F172A",
                  STAR_OFF=p["line"], SOFT_LEMON="#D5AF61", SEARCH_HIT="#E6B47A" if dark else "#9B652C",
                  HOME_BG=p["home"], HOME_BACKGROUND=p["background"], HOME_TEXT="#F5F7FB",
                  HOME_SUB="#CCD3DE", HOME_FAINT="#B7C2D2",
                  HOME_ACCENT=mix(ac, "#FFFFFF", .55),
                  HOME_SURFACE=with_alpha(p["home"], .55),
                  HOME_SURFACE_SOFT=with_alpha(p["home"], .40),
                  HOME_HOVER=with_alpha(mix(ac, p["home"], .28), .70),
                  HOME_LINE="#30FFFFFF",
                  HOME_SHADE=[with_alpha(p["home"], .30), with_alpha(p["home"], .50)],
                  DOCK_HOME=with_alpha(p["home"], .60))
    # 功能色保留语义，浅底跟随当前表面，深色模式不留下浅色块。
    for name, color in {"BLUSH_PINK":"#BA758B", "MINT_GREEN":"#579477",
                        "LAVENDER":"#9280B4", "APRICOT":"#BB8A56", "SKY_CYAN":"#578B9C",
                        "DANGER":"#C26168"}.items():
        fg = mix(color, "#FFFFFF", .65) if dark else color
        values[name] = fg
        values[name + "_SOFT"] = mix(fg, p["card"], .16 if dark else .12)
    globals().update(values)
    globals()["CATEGORY_COLORS"] = [(globals()[n], globals()[n+"_SOFT"])
                                   for n in ("MIST_BLUE", "BLUSH_PINK", "MINT_GREEN", "LAVENDER", "APRICOT", "SKY_CYAN")]


def load_theme_settings() -> None:
    try:
        with open(SETTINGS_PATH, encoding="utf-8") as f:
            saved = json.load(f)
        if not isinstance(saved, dict):
            saved = {}
    except (OSError, ValueError):
        saved = {}
    # v2 只有强调色，不能作为完整外观使用；升级回到原布局对应的经典雾蓝。
    preset = saved.get("preset", "classic")
    if not isinstance(preset, str):
        preset = "classic"
    accent = saved.get("accent") if saved.get("version") == 3 else None
    if not isinstance(accent, str) or len(accent) != 7 or not accent.startswith("#"):
        accent = None
    else:
        try:
            int(accent[1:], 16)
        except ValueError:
            accent = None
    _apply(preset, accent)


def set_theme(bg: str | None = None, bg_deep: str | None = None,
              accent: str | None = None, preset: str | None = None) -> None:
    """原子保存完整主题；调用后各页从 theme 模块读取新令牌。"""
    _apply(preset or THEME_ID, accent if accent is not None else (None if preset else ACCENT))
    if bg:
        globals()["BG"] = bg
        globals()["VEIL"] = with_alpha(bg, .96)
    if bg_deep:
        globals()["BG_DEEP"] = bg_deep
    os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
    temp = SETTINGS_PATH + ".tmp"
    with open(temp, "w", encoding="utf-8") as f:
        json.dump({"version": 3, "preset": THEME_ID, "accent": ACCENT}, f, ensure_ascii=False)
    os.replace(temp, SETTINGS_PATH)


BG_PRESETS = [(p["name"], p["bg"], p["deep"]) for p in THEMES.values()]
ACCENT_PRESETS = [(p["name"], p["accent"]) for p in THEMES.values()]
load_theme_settings()


# ---------------- 渐变 / 阴影 ----------------
def blue_gradient(begin: str | None = None, end: str | None = None) -> ft.LinearGradient:
    """主色渐变：顶部导航、手机标题栏用。"""
    return ft.LinearGradient(
        begin=ft.Alignment.TOP_LEFT, end=ft.Alignment.BOTTOM_RIGHT,
        colors=[begin or MIST_BLUE, end or MIST_BLUE_DEEP],
    )


def soft_gradient(colors: list[str]) -> ft.LinearGradient:
    return ft.LinearGradient(
        begin=ft.Alignment.TOP_CENTER, end=ft.Alignment.BOTTOM_CENTER, colors=colors,
    )


def card_shadow(strong: bool = False) -> ft.BoxShadow:
    return ft.BoxShadow(
        blur_radius=26 if strong else 16,
        spread_radius=-6 if strong else -3,
        color=SHADOW_DEEP if strong else SHADOW,
        offset=ft.Offset(0, 10 if strong else 6),
    )


# ---------------- 复用组件 ----------------
def badge(text: str, bg: str | None = None, fg: str | None = None, size: int = 11) -> ft.Container:
    """小圆角标签：用于展示"电影 / 剧集""题材"等信息。"""
    return ft.Container(
        padding=ft.Padding.symmetric(horizontal=9, vertical=3),
        border_radius=20,
        bgcolor=bg or MIST_BLUE_SOFT,
        content=ft.Text(text, size=size, color=fg or MIST_BLUE_DEEP, weight=ft.FontWeight.W_500),
    )


def icon_badge(icon: str, size: int = 38, bg: str | None = None,
               color: str | None = None, icon_size: int = 19) -> ft.Container:
    """圆角方形图标徽章：卡片标题、空状态等场景用。"""
    return ft.Container(
        width=size, height=size, border_radius=size * 0.3,
        bgcolor=bg or MIST_BLUE_SOFT, alignment=ft.Alignment.CENTER,
        content=ft.Icon(icon, size=icon_size, color=color or MIST_BLUE_DEEP),
    )


def count_pill(count: int, bg: str | None = None, fg: str | None = None) -> ft.Container:
    """数字小药丸：分类、会话条数。"""
    return ft.Container(
        width=max(22, 14 + len(str(count))*7), height=20, padding=ft.Padding.symmetric(horizontal=7),
        border_radius=10, bgcolor=bg or MIST_BLUE_SOFT, alignment=ft.Alignment.CENTER,
        content=ft.Text(str(count), size=10, weight=ft.FontWeight.W_700, color=fg or MIST_BLUE_DEEP),
    )


def empty_state(icon: str, title: str, subtitle: str = "",
                color: str | None = None) -> ft.Container:
    """统一的空状态：柔光底图标 + 标题 + 副文案。"""
    color = color or MIST_BLUE
    return ft.Container(
        expand=True, alignment=ft.Alignment.CENTER,
        padding=ft.Padding.all(30),
        content=ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=10,
            controls=[
                ft.Stack(
                    width=110, height=110,
                    controls=[
                        ft.Container(width=110, height=110, border_radius=55,
                                     bgcolor=with_alpha(color, 0.08)),
                        ft.Container(width=78, height=78, border_radius=39,
                                     bgcolor=with_alpha(color, 0.14),
                                     alignment=ft.Alignment.CENTER,
                                     margin=ft.Margin.all(16),
                                     content=ft.Icon(icon, size=38, color=color)),
                    ],
                ),
                ft.Text(title, size=16, weight=ft.FontWeight.W_600, color=TEXT_MAIN),
                ft.Text(subtitle, size=12, color=TEXT_SUB, text_align=ft.TextAlign.CENTER),
            ],
        ),
    )


# 客行录品牌排版：展示文字用宋体，交互控件保持清晰的无衬线。
DISPLAY_FONT = FONT_FAMILY
BRASS = "#D6B775"


def app_theme() -> ft.Theme:
    return ft.Theme(
        color_scheme_seed=ACCENT, font_family=FONT_FAMILY,
        color_scheme=ft.ColorScheme(primary=ACCENT, on_primary=ON_ACCENT,
                                   secondary=ACCENT, on_secondary=ON_ACCENT,
                                   primary_container=MIST_BLUE_SOFT, on_primary_container=TEXT_MAIN,
                                   on_surface_variant=TEXT_SUB,
                                   surface=CARD_BG, on_surface=TEXT_MAIN,
                                   outline=LINE),
    )


def module_frame(title: str, subtitle: str, icon, body: ft.Control) -> ft.Container:
    """模块共用的页眉与纸白工作区，保留内部各自的完整业务交互。"""
    return ft.Container(
        expand=True, padding=ft.Padding.only(left=22, right=22, top=8, bottom=8),
        content=ft.Column(spacing=16, expand=True, controls=[
            ft.Row(spacing=12, controls=[
                icon_badge(icon, 42, with_alpha(ACCENT, .10), ACCENT, 21),
                ft.Column(spacing=3, controls=[
                    ft.Text(title, size=23, weight=ft.FontWeight.W_600, color=TEXT_MAIN),
                    ft.Text(subtitle, size=12, color=TEXT_SUB),
                ]),
            ]),
            ft.Container(expand=True, border_radius=16, bgcolor=CARD_GLASS,
                         border=ft.Border.all(1, LINE),
                         clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                         content=body),
        ]))


def toast(content, **kwargs) -> ft.SnackBar:
    """通知浮在导航之上，避免覆盖导航标签和点击区域。"""
    return ft.SnackBar(content=content, behavior=ft.SnackBarBehavior.FLOATING,
                       margin=ft.Margin.only(left=24, right=24, bottom=108),
                       shape=ft.RoundedRectangleBorder(radius=14),
                       duration=2800, **kwargs)


def brand_mark(size: float = 32, color: str | None = None) -> ft.Image:
    """单色「录」字变形标记，透明边界，跟随主题着色。"""
    return ft.Image(src=res("assets/app-mark.svg"), width=size, height=size,
                    color=color or ACCENT, fit=ft.BoxFit.CONTAIN)

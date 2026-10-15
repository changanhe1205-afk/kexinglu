"""客行录 · 聊天长图导出

用 Pillow 把一段对话画成一张长图（PNG）。做法是"先量后画"两遍：
    第一遍：按字体逐字换行，算出每个气泡和时间分隔的高度，累加出画布总高度
    第二遍：真正往画布上画（背景 → 标题栏 → 逐条消息）

常用参数集中在下面的常量区，改这里的数字就能整体调整出图风格。
"""

from __future__ import annotations

import os
from typing import Optional

from PIL import Image, ImageDraw, ImageFont, ImageOps

from theme import (
    BG, MIST_BLUE, MIST_BLUE_DEEP, MIST_BLUE_SOFT, SOFT_LEMON, TEXT_MAIN, TEXT_SUB,
)

# ---------------- 出图参数 ----------------
CANVAS_WIDTH = 750        # 画布宽度，手机聊天截图的手感
PADDING = 28              # 左右留白
TOP_BAR_HEIGHT = 108      # 顶部标题栏高度
AVATAR_SIZE = 76          # 圆形头像尺寸
AVATAR_GAP = 14           # 头像和气泡之间的间距
BUBBLE_PAD_X = 24         # 气泡内文字左右内边距
BUBBLE_PAD_Y = 18         # 气泡内文字上下内边距
BUBBLE_RADIUS = 22        # 气泡圆角
BUBBLE_GAP = 20           # 相邻气泡的间距
TIME_GAP = 26             # 时间分隔的上下留白
TOP_PADDING = 24          # 标题栏和第一条消息之间的距离
BOTTOM_PADDING = 40       # 底部留白

FONT_SIZE = 28            # 正文
TIME_FONT_SIZE = 21       # 时间文字
TITLE_FONT_SIZE = 34      # 标题栏昵称
LINE_HEIGHT = 42          # 正文行高

COLOR_TEXT = TEXT_MAIN
COLOR_TIME_TEXT = "#FFFFFF"
COLOR_TIME_PILL = (46, 58, 78, 110)   # 时间文字下面的深色小胶囊，配任何背景都看得清
# 我的气泡两套配色：lemon = 柔柠黄（默认），mist = 雾霭蓝
THEMES = {
    "lemon": {"bubble": SOFT_LEMON, "text": TEXT_MAIN},
    "mist": {"bubble": MIST_BLUE, "text": "#FFFFFF"},
}
COLOR_BUBBLE_OTHER = "#FFFFFF"
COLOR_SHADOW = (46, 62, 92, 22)

# Windows 自带的中文字体，按顺序找一个存在的
FONT_CANDIDATES = [
    r"C:\Windows\Fonts\msyh.ttc",       # 微软雅黑
    r"C:\Windows\Fonts\msyhbd.ttc",     # 微软雅黑粗体
    r"C:\Windows\Fonts\simhei.ttf",     # 黑体
    r"C:\Windows\Fonts\simsun.ttc",     # 宋体
]


def _find_font_path() -> Optional[str]:
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            return path
    return None


def load_font(size: int) -> ImageFont.FreeTypeFont:
    """加载指定字号的中文字体，找不到系统字体时退回 Pillow 默认字体。"""
    path = _find_font_path()
    try:
        if path:
            return ImageFont.truetype(path, size)
    except OSError:
        pass
    return ImageFont.load_default()


# ---------------- 排版辅助 ----------------
def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    """按字符换行：中英文混排也能用，遇到 \\n 强制换行。"""
    lines: list[str] = []
    for paragraph in str(text).split("\n"):
        current = ""
        for char in paragraph:
            trial = current + char
            width = font.getlength(trial)
            if max_width and width > max_width and current:
                lines.append(current)
                current = char
            else:
                current = trial
        lines.append(current)
    return lines


def circle_avatar(src: str, size: int = AVATAR_SIZE) -> Image.Image:
    """把任意图片裁成正方形再套圆形遮罩，得到头像。没有图片时画一个色块 + 首字。"""
    if src and os.path.exists(src):
        try:
            img = Image.open(src).convert("RGBA")
            img = ImageOps.fit(img, (size, size), method=Image.LANCZOS)
        except OSError:
            return _default_avatar("？", size)

        mask = Image.new("L", (size, size), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
        out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        out.paste(img, (0, 0), mask)
        return out

    return _default_avatar("影", size)


def _default_avatar(char: str, size: int) -> Image.Image:
    """默认头像：雾霭蓝圆底 + 中间白字。"""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse((0, 0, size, size), fill=MIST_BLUE)
    font = load_font(int(size * 0.5))
    draw.text((size / 2, size / 2), char, font=font, fill="#FFFFFF", anchor="mm")
    return img


# ---------------- 主流程 ----------------
def render_chat(conversation: dict, messages: list[dict]) -> Image.Image:
    """把会话渲染成一张完整的长图（不落盘，方便预览/后续处理）。"""
    font = load_font(FONT_SIZE)
    time_font = load_font(TIME_FONT_SIZE)
    title_font = load_font(TITLE_FONT_SIZE)

    palette = THEMES.get((conversation.get("theme") or "lemon"), THEMES["lemon"])
    my_bubble_color = palette["bubble"]
    my_text_color = palette["text"]

    my_avatar = circle_avatar(conversation.get("my_avatar") or "")
    other_avatar = circle_avatar(conversation.get("avatar") or "")

    # ---- 第一遍：算尺寸 ----
    # 先算出可画正文的最大宽度
    max_text_width = CANVAS_WIDTH - PADDING * 2 - AVATAR_SIZE - AVATAR_GAP - BUBBLE_PAD_X * 2 - 30

    blocks: list[dict] = []
    total_height = TOP_BAR_HEIGHT + TOP_PADDING
    last_date = ""
    for msg in messages:
        content = (msg.get("content") or "").strip()
        if not content:
            continue

        # 换天时自动画一条日期分隔（比手动勾选更省心）
        msg_date = (msg.get("msg_date") or "").strip()
        if msg_date and msg_date != last_date:
            blocks.append({"kind": "date", "text": msg_date})
            total_height += TIME_FONT_SIZE + TIME_GAP * 2
            last_date = msg_date

        # 时间分隔
        if msg.get("show_time") and (msg.get("time_label") or "").strip():
            blocks.append({"kind": "time", "text": msg["time_label"].strip()})
            total_height += TIME_FONT_SIZE + TIME_GAP * 2

        lines = wrap_text(content, font, max_text_width)
        text_width = int(max(font.getlength(line) for line in lines))
        text_height = LINE_HEIGHT * len(lines)

        bubble_w = text_width + BUBBLE_PAD_X * 2
        bubble_h = text_height + BUBBLE_PAD_Y * 2
        blocks.append({
            "kind": "bubble",
            "side": int(msg.get("side") or 0),
            "lines": lines,
            "width": bubble_w,
            "height": bubble_h,
        })
        total_height += bubble_h + BUBBLE_GAP

    total_height += BOTTOM_PADDING
    total_height = max(total_height, TOP_BAR_HEIGHT + 400)

    # ---- 画布与背景 ----
    canvas = Image.new("RGBA", (CANVAS_WIDTH, total_height), BG)
    _paint_background(canvas, conversation.get("background") or "")

    draw = ImageDraw.Draw(canvas)

    # ---- 顶部标题栏 ----
    draw.rectangle((0, 0, CANVAS_WIDTH, TOP_BAR_HEIGHT), fill=MIST_BLUE)
    draw.text((34, TOP_BAR_HEIGHT / 2), "<", font=title_font, fill="#FFFFFF", anchor="lm")
    title = (conversation.get("name") or "聊天记录").strip()
    draw.text((CANVAS_WIDTH / 2, TOP_BAR_HEIGHT / 2 - 10), title,
              font=title_font, fill="#FFFFFF", anchor="mm")
    subtitle = (conversation.get("subtitle") or "").strip()
    if subtitle:
        small_font = load_font(20)
        draw.text((CANVAS_WIDTH / 2, TOP_BAR_HEIGHT / 2 + 20), subtitle,
                  font=small_font, fill="#E3EBF7", anchor="mm")

    # ---- 第二遍：逐个画 ----
    y = TOP_BAR_HEIGHT + TOP_PADDING
    for block in blocks:
        if block["kind"] in ("time", "date"):
            text = block["text"]
            width = int(time_font.getlength(text)) + 28
            left = (CANVAS_WIDTH - width) / 2
            draw.rounded_rectangle(
                (left, y + TIME_GAP - 6, left + width, y + TIME_GAP + TIME_FONT_SIZE + 6),
                radius=10, fill=COLOR_TIME_PILL,
            )
            draw.text((CANVAS_WIDTH / 2, y + TIME_GAP + TIME_FONT_SIZE / 2), text,
                      font=time_font, fill=COLOR_TIME_TEXT, anchor="mm")
            y += TIME_FONT_SIZE + TIME_GAP * 2
            continue

        is_me = block["side"] == 0
        bubble_w, bubble_h = block["width"], block["height"]

        if is_me:
            # 我：气泡靠右，头像在最右侧
            bubble_x = CANVAS_WIDTH - PADDING - AVATAR_SIZE - AVATAR_GAP - bubble_w
            avatar_x = CANVAS_WIDTH - PADDING - AVATAR_SIZE
        else:
            bubble_x = PADDING + AVATAR_SIZE + AVATAR_GAP
            avatar_x = PADDING

        # 轻微阴影，让气泡浮起来
        draw.rounded_rectangle(
            (bubble_x, y + 3, bubble_x + bubble_w, y + bubble_h + 3),
            radius=BUBBLE_RADIUS, fill=COLOR_SHADOW,
        )
        draw.rounded_rectangle(
            (bubble_x, y, bubble_x + bubble_w, y + bubble_h),
            radius=BUBBLE_RADIUS,
            fill=my_bubble_color if is_me else COLOR_BUBBLE_OTHER,
        )

        text_color = my_text_color if is_me else COLOR_TEXT
        text_y = y + BUBBLE_PAD_Y + (LINE_HEIGHT - FONT_SIZE) / 2
        for line in block["lines"]:
            draw.text((bubble_x + BUBBLE_PAD_X, text_y + FONT_SIZE / 2), line,
                      font=font, fill=text_color, anchor="lm")
            text_y += LINE_HEIGHT

        canvas.alpha_composite(my_avatar if is_me else other_avatar,
                               (int(avatar_x), int(y + (bubble_h - AVATAR_SIZE) / 2)))
        y += bubble_h + BUBBLE_GAP

    return canvas


def _paint_background(canvas: Image.Image, background_path: str) -> None:
    """有背景图就竖向平铺，没有就保持纯色底。"""
    if not background_path or not os.path.exists(background_path):
        return
    try:
        bg = Image.open(background_path).convert("RGBA")
    except OSError:
        return

    # 按宽度等比缩放，再竖向重复铺满（避免被拉伸变形）
    ratio = CANVAS_WIDTH / bg.width
    new_height = max(1, int(bg.height * ratio))
    bg = bg.resize((CANVAS_WIDTH, new_height), Image.LANCZOS)

    y = 0
    while y < canvas.height:
        canvas.alpha_composite(bg, (0, y))
        y += new_height


def export_chat(conversation: dict, messages: list[dict], save_path: str) -> str:
    """导出聊天长图到指定路径，返回实际保存的路径。"""
    img = render_chat(conversation, messages)
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    img = img.convert("RGB")     # PNG 用 RGB 体积更小
    img.save(save_path, "PNG")
    return save_path

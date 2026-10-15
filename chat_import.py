"""客行录 · 聊天记录文本解析（导入微信 / QQ）

微信和 QQ 都不提供官方的本地导出，最通用的办法是：
在聊天窗口里选中一批消息 → 复制 → 粘贴到这里（或直接选择导出的 .txt 文件），
本模块把它解析成结构化消息。

支持的常见格式：

  微信（PC 多选复制）
      阿岚 20:14
      今天这部电影真的很好看
      我 20:15
      我也这么觉得

  微信（跨天复制，中间夹独立日期行）
      2026年5月1日 星期四
      阿岚 20:14
      …

  QQ（PC 复制 / 导出 txt）
      阿岚 2026-05-01 20:14:32
      今天这部电影真的很好看
      2026-05-01 20:14:32 阿岚
      …

  QQ 导出的 txt（带消息对象头部，时间在前）
      消息对象:阿岚;QQ号:10001
      2026-05-01 20:14:32 阿岚(10001)
      今天这部电影真的很好看

  微信合并转发的聊天记录（单行 "昵称: 内容"）
      阿岚: 今天这部电影真的很好看
      我: 我也这么觉得

解析策略：逐行判断是不是"消息头"（昵称 + 时间），是就开一条新消息，
不是就把内容接到上一条消息；独立成行的日期用于给后面的消息定日期。
"""

from __future__ import annotations

import os
import re
from datetime import datetime

# 时间：20:14 或 20:14:32
_TIME = r"(?P<time>\d{1,2}:\d{2}(?::\d{2})?)"
# 日期：2026-05-01 / 2026/5/1 / 2026年5月1日
_DATE = r"(?P<date>\d{4}[-/.年]\d{1,2}[-/.月]\d{1,2}日?)"
# 只有月日：5月1日 / 05-01
_DATE_SHORT = r"(?P<shortdate>\d{1,2}[-/.月]\d{1,2}日?)"

# 按优先级匹配：越具体的放前面
HEADER_PATTERNS = [
    # 昵称 日期 时间（QQ 常见）
    re.compile(rf"^(?P<name>.+?)\s+{_DATE}\s+{_TIME}\s*$"),
    # 日期 时间 昵称（QQ 导出 txt 常见）
    re.compile(rf"^{_DATE}\s+{_TIME}\s+(?P<name>.+?)\s*$"),
    # 昵称 时间（微信最常见，不带日期）
    re.compile(rf"^(?P<name>.+?)\s+{_TIME}\s*$"),
    # 时间 昵称（QQ 导出、日期行分开时常见）
    re.compile(rf"^{_TIME}\s+(?P<name>.+?)\s*$"),
]

# 独立成行的日期分隔：
#   2026年5月1日 星期四  /  2026-05-01 周四  /  —— 2026/05/01 ——
DATE_LINE_PATTERNS = [
    re.compile(rf"^{_DATE}\s*(?:周|星期|周\s*)?[一二三四五六日天]?\s*$"),
    re.compile(rf"^[\s\-—=*·:：]*{_DATE}[\s\-—=*·:：周一二三四五六日天]*$"),
    re.compile(rf"^{_DATE_SHORT}\s*(?:周|星期)?[一二三四五六日天]?\s*$"),
]

# 合并转发：昵称: 内容（昵称 1~16 位、不含空白和冒号）
MERGED_LINE = re.compile(r"^(?P<name>[^:：\s][^:：]{0,15})[:：]\s*(?P<content>.+)$")

# QQ 号尾巴：阿岚(10001)、阿岚<10001>
_QQ_TAIL = re.compile(r"[(<<]\d{5,12}[>)>]\s*$")

# QQ 导出 txt 的元信息
_QQ_PEER = re.compile(r"消息对象[:：]\s*([^;；\n]+)")

# 需要忽略的系统提示行（出现即整行跳过）
SYSTEM_HINTS = (
    "以下是新消息", "以上为历史消息", "该消息已撤回", "撤回了一条消息",
    "你已添加了", "现在可以开始聊天了", "拍了拍", "消息分组", "消息记录",
    "开启了朋友验证", "对方正在输入", "对方已成功接收", "请使用最新版手机",
    "================================================================",
)

# 读文件时依次尝试的编码（QQ 导出通常是 GBK，微信复制一般是 UTF-8）
_ENCODINGS = ("utf-8-sig", "utf-8", "gb18030", "gbk", "big5", "latin-1")


def read_chat_file(path: str) -> str:
    """读取聊天记录文件，自动尝试多种常见编码。

    QQ 导出的 .bak 有两种：老版本导出的是明文文本（GBK 编码，只是后缀不同），
    新版本的是加密二进制备份——后者检测出来直接报错并给出操作指引。
    """
    with open(path, "rb") as f:
        raw = f.read()
    # 加密二进制备份特征：开头一段就有大量 \x00 / 不可解码字节
    head = raw[:4096]
    if head and head.count(b"\x00") / len(head) > 0.01:
        raise ValueError(
            "这个 .bak 是 QQ 的加密备份格式，无法直接读取。\n"
            "请在 QQ「消息管理器」里右键联系人 → 导出聊天记录，"
            "或多选消息后直接复制粘贴到下方文本框。")
    for enc in _ENCODINGS:
        try:
            text = raw.decode(enc)
            break
        except (UnicodeDecodeError, LookupError):
            continue
    else:
        text = raw.decode("utf-8", errors="ignore")
    # 兜底：解码后仍大面积乱码（替换字符 U+FFFD），按加密备份处理
    if text.count("") / max(len(text), 1) > 0.05:
        raise ValueError(
            "这个 .bak 是 QQ 的加密备份格式，无法直接读取。\n"
            "请在 QQ「消息管理器」里右键联系人 → 导出聊天记录，"
            "或多选消息后直接复制粘贴到下方文本框。")
    return text


def _normalize_date(raw: str, default_year: int | None = None) -> str:
    """把 2026年5月1日 / 2026/5/1 统一成 2026-05-01。"""
    if not raw:
        return ""
    text = (raw.replace("年", "-").replace("月", "-").replace("日", "")
               .replace("/", "-").replace(".", "-"))
    parts = [p for p in text.split("-") if p]
    try:
        if len(parts) >= 3:
            year, month, day = parts[0], parts[1], parts[2]
            return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
        if len(parts) == 2 and default_year:
            month, day = parts
            return f"{default_year:04d}-{int(month):02d}-{int(day):02d}"
    except ValueError:
        return ""
    return ""


def _normalize_time(raw: str) -> str:
    """20:14:32 → 20:14。"""
    parts = (raw or "").split(":")
    if len(parts) < 2:
        return ""
    try:
        return f"{int(parts[0]):02d}:{int(parts[1]):02d}"
    except ValueError:
        return ""


def _clean_name(name: str) -> str:
    """清理昵称上的 QQ 号尾巴和首尾空白。"""
    name = (name or "").strip()
    name = _QQ_TAIL.sub("", name).strip()
    return name


def _parse_date_line(line: str, default_year: int | None) -> str:
    """如果这一行是独立日期，返回标准日期，否则返回空串。"""
    for pattern in DATE_LINE_PATTERNS:
        match = pattern.match(line)
        if match:
            data = match.groupdict()
            raw = data.get("date") or data.get("shortdate") or ""
            date = _normalize_date(raw, default_year)
            if date:
                return date
    return ""


def _looks_like_merged(text: str) -> bool:
    """判断整段文本是不是"昵称: 内容"的合并转发格式。

    要求：没有任何带时间的消息头，且至少出现 3 行单行昵称格式、
    昵称有重复（避免把普通对话里的冒号误判成昵称）。
    """
    names: list[str] = []
    has_time_header = False
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        # 只要任何一种"昵称 + 时间"消息头出现，就不是合并转发格式
        #（否则 20:14 里的冒号会被误判成"昵称: 内容"）
        if any(p.match(stripped) for p in HEADER_PATTERNS):
            has_time_header = True
        match = MERGED_LINE.match(stripped)
        if match:
            names.append(match.group("name").strip())
    if has_time_header or len(names) < 3:
        return False
    return len(set(names)) < len(names)          # 有昵称重复才认


def parse_chat_text(text: str, my_name: str = "") -> list[dict]:
    """把粘贴进来的聊天文本解析成消息列表。

    返回：[{name, side, content, date, time, show_time, time_label}, ...]
        side: 0 = 我，1 = 对方
    """
    text = text or ""
    this_year = datetime.now().year

    # 合并转发格式走单独的轻量解析
    if _looks_like_merged(text):
        return _parse_merged(text, my_name)

    raw_lines = [line.rstrip() for line in text.splitlines()]
    messages: list[dict] = []
    current: dict | None = None
    last_dt: datetime | None = None
    # 独立日期行 / 上一条消息会携带日期；微信复制常常只有时间，日期沿用上文
    fallback_date = datetime.now().strftime("%Y-%m-%d")

    for line in raw_lines:
        stripped = line.strip()
        if not stripped:
            continue
        if any(hint in stripped for hint in SYSTEM_HINTS):
            continue

        # 独立日期行：更新上下文日期，不产生消息
        date_only = _parse_date_line(stripped, this_year)
        if date_only:
            fallback_date = date_only
            continue

        # 判断是不是"消息头"
        header = None
        for pattern in HEADER_PATTERNS:
            match = pattern.match(stripped)
            if match:
                header = match
                break

        if header:
            name = _clean_name(header.group("name"))
            if not name:
                continue
            time_text = _normalize_time(header.group("time"))
            groups = header.groupdict()
            date_text = (_normalize_date(groups.get("date") or "", this_year)
                         or fallback_date)
            fallback_date = date_text
            current = {"name": name, "content": "", "date": date_text, "time": time_text}
            messages.append(current)
        elif current is not None:
            # 普通内容行，接到上一条消息上
            current["content"] = (
                (current["content"] + "\n" + stripped).strip()
                if current["content"] else stripped
            )

    # 过滤掉只有头没有内容的行，并判断左右、是否加时间分隔
    result: list[dict] = []
    for msg in messages:
        content = (msg["content"] or "").strip()
        if not content:
            continue

        name = msg["name"]
        is_me = bool(my_name) and (
            name.strip() == my_name.strip() or name.strip() in ("我", "me", "Me", "本人")
        )

        # 时间分隔：第一条、跨天、或和上一条相隔超过 5 分钟时自动显示
        show_time = False
        time_label = msg["time"]
        hour, minute = (msg["time"].split(":") + ["0"])[:2] if msg["time"] else ("0", "0")
        try:
            current_dt = datetime(
                *(int(p) for p in (msg["date"] or fallback_date).split("-")),
                int(hour), int(minute),
            )
        except ValueError:
            current_dt = None

        if current_dt is not None:
            if last_dt is None:
                show_time = True
            else:
                gap = (current_dt - last_dt).total_seconds()
                if msg["date"] and last_dt.date() != current_dt.date():
                    show_time = True
                    time_label = f"{current_dt.strftime('%m-%d')} {msg['time']}"
                elif gap > 300:
                    show_time = True
            last_dt = current_dt

        result.append({
            "name": name,
            "side": 0 if is_me else 1,
            "content": content,
            "date": msg["date"],
            "time": msg["time"],
            "time_label": time_label,
            "show_time": show_time,
        })

    return result


def _parse_merged(text: str, my_name: str) -> list[dict]:
    """解析微信合并转发格式：每行 "昵称: 内容"，时间信息缺失则按今天处理。"""
    date = datetime.now().strftime("%Y-%m-%d")
    result: list[dict] = []
    for line in text.splitlines():
        stripped = line.strip()
        match = MERGED_LINE.match(stripped)
        if not match:
            continue
        name = _clean_name(match.group("name"))
        content = match.group("content").strip()
        if not name or not content:
            continue
        is_me = bool(my_name) and (
            name == my_name.strip() or name in ("我", "me", "Me", "本人")
        )
        result.append({
            "name": name,
            "side": 0 if is_me else 1,
            "content": content,
            "date": date,
            "time": "",
            "time_label": "",
            "show_time": False,
        })
    return result


def guess_peer_name(parsed: list[dict], my_name: str = "") -> str:
    """从解析结果里猜一个"对方昵称"（出现最多的非自己名字）。"""
    counter: dict[str, int] = {}
    for msg in parsed:
        name = msg["name"]
        if my_name and name == my_name:
            continue
        if name in ("我", "me", "Me", "本人"):
            continue
        counter[name] = counter.get(name, 0) + 1
    if not counter:
        return ""
    return max(counter.items(), key=lambda kv: kv[1])[0]


def summarize(parsed: list[dict], my_name: str = "") -> dict:
    """统计解析结果：消息数、参与人、对方昵称、日期范围、我的/对方条数。"""
    names: list[str] = []
    dates = sorted({m.get("date") for m in parsed if m.get("date")})
    mine = sum(1 for m in parsed if int(m.get("side") or 1) == 0)
    for msg in parsed:
        name = msg.get("name") or ""
        if name and name not in names:
            names.append(name)
    return {
        "count": len(parsed),
        "names": names,
        "peer": guess_peer_name(parsed, my_name),
        "date_from": dates[0] if dates else "",
        "date_to": dates[-1] if dates else "",
        "mine": mine,
        "other": len(parsed) - mine,
    }


def read_text_from_path(path: str) -> str:
    """供界面调用：选择本地文件后读取内容（兼容 .txt）。"""
    if not path or not os.path.exists(path):
        return ""
    return read_chat_file(path)

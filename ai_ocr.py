"""客行录 · 截图 AI 识别

调用 OpenAI 兼容的「视觉对话」接口，把第三方 App（12306 / 航旅纵横 /
航司或铁路微信助手等）的机票火车票截图识别成票根信息。

- 默认对接智谱开放平台 glm-4v-flash（免费），也支持任何 OpenAI 兼容接口
  （如通义 qwen-vl、OpenAI gpt-4o-mini 等），改 base_url / model 即可。
- 配置明文保存在 data/ai_config.json（本地应用，不出本机）。
"""

from __future__ import annotations

import base64
import json
import mimetypes
import os
import re
import urllib.error
import urllib.request

from database import DB_PATH

CONFIG_PATH = os.path.join(os.path.dirname(DB_PATH), "ai_config.json")

DEFAULTS = {
    "base_url": "https://open.bigmodel.cn/api/paas/v4",
    "api_key": "",
    "model": "glm-4v-flash",
}

PROMPT = """你是票务信息识别助手。请从这张机票或火车票截图中提取信息，
严格只输出一个 JSON 对象，不要输出任何其他文字或代码块标记：
{"vehicle": "飞机/高铁/火车", "from_city": "出发地（城市、机场或车站）",
 "to_city": "目的地", "depart_date": "YYYY-MM-DD", "depart_time": "HH:MM",
 "arrive_time": "HH:MM", "code": "航班号或车次", "seat": "座位或舱位",
 "gate": "登机口或检票口", "price": "票价（只留数字，如 145.0）",
 "passenger": "乘客姓名", "passenger_id": "证件号（识别不到就留空）",
 "note": "备注（可留空）"}
要求：
1. 识别不到的字段填空字符串。
2. vehicle 判断：机票/航班=飞机；G/D/C 字头车次=高铁；其他车次=火车。
3. 日期补全年份；相对日期（如"明天"）结合截图推算，推算不出留空。
4. 时间只保留 HH:MM。"""


def load_config() -> dict:
    cfg = dict(DEFAULTS)
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            saved = json.load(f)
        for key in DEFAULTS:
            if saved.get(key):
                cfg[key] = str(saved[key]).strip()
    except (OSError, ValueError):
        pass
    return cfg


def save_config(cfg: dict) -> None:
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    data = {k: str(cfg.get(k, "")).strip() for k in DEFAULTS}
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _extract_json(text: str) -> dict:
    """从模型回复里抠出 JSON（容忍 ```json 代码块等包裹）。"""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("AI 没有返回可解析的结果，请重试或换一张更清晰的截图")
    info = json.loads(match.group(0))
    if not isinstance(info, dict):
        raise ValueError("AI 返回的格式不对，请重试")
    return info


def recognize_ticket(image_path: str, cfg: dict | None = None) -> dict:
    """识别一张票面截图，返回规范化后的票根字段（全部是字符串）。"""
    cfg = cfg or load_config()
    if not cfg.get("api_key"):
        raise ValueError("还没有配置 AI 密钥，请先在「AI 识别设置」里填写")
    if not os.path.exists(image_path):
        raise ValueError("截图文件不存在")

    mime = mimetypes.guess_type(image_path)[0] or "image/png"
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")

    payload = {
        "model": cfg["model"],
        "messages": [{
            "role": "user",
            "content": [
                {"type": "image_url",
                 "image_url": {"url": f"data:{mime};base64,{b64}"}},
                {"type": "text", "text": PROMPT},
            ],
        }],
        "temperature": 0.1,
    }
    url = cfg["base_url"].rstrip("/") + "/chat/completions"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {cfg['api_key']}",
        },
        method="POST",
    )
    try:
        from network_tls import https_context
        with urllib.request.urlopen(req, timeout=90, context=https_context()) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = json.loads(exc.read().decode("utf-8")).get("error", {}).get(
                "message", "")
        except Exception:
            pass
        raise ValueError(f"接口返回 {exc.code}：{detail or '请检查密钥和模型名'}") from exc
    except urllib.error.URLError as exc:
        raise ValueError(f"连不上 AI 接口：{exc.reason}") from exc

    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError("AI 返回内容为空，请稍后重试") from exc

    info = _extract_json(content)

    vehicle = str(info.get("vehicle") or "").strip()
    if vehicle not in ("飞机", "高铁", "火车"):
        vehicle = "飞机"
    date = str(info.get("depart_date") or "").strip()
    match = re.search(r"\d{4}[-/年]\d{1,2}[-/月]\d{1,2}", date)
    if match:
        parts = re.findall(r"\d+", match.group(0))
        date = f"{parts[0]}-{int(parts[1]):02d}-{int(parts[2]):02d}"
    else:
        date = ""

    def clean(key: str) -> str:
        return str(info.get(key) or "").strip()

    return {
        "vehicle": vehicle,
        "from_city": clean("from_city"),
        "to_city": clean("to_city"),
        "depart_date": date,
        "depart_time": clean("depart_time")[:5],
        "arrive_time": clean("arrive_time")[:5],
        "code": clean("code"),
        "seat": clean("seat"),
        "gate": clean("gate"),
        "price": clean("price"),
        "passenger": clean("passenger"),
        "passenger_id": clean("passenger_id"),
        "note": clean("note"),
    }

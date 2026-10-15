"""Run with .venv314/Scripts/python.exe tests/desktop_design_smoke.py.

Native Flet UI smoke test. Uses an isolated temporary data directory; never
edits the user's database, profile, theme or background choices.
"""
import asyncio
import ctypes
from ctypes import wintypes
import inspect
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
temp = tempfile.TemporaryDirectory(prefix="kexinglu-qa-")
import config
config._cache = {"data_dir": temp.name}
config.CONFIG_PATH = str(Path(temp.name) / "config.json")

import flet as ft
from flet.controls.base_control import BaseControl
from PIL import ImageGrab
import main as app
import food_db
import theme

passed = False

OUT = ROOT / "design" / "verification"
OUT.mkdir(parents=True, exist_ok=True)


def walk(root):
    seen, stack = set(), [root]
    while stack:
        obj = stack.pop()
        if isinstance(obj, BaseControl):
            if id(obj) in seen:
                continue
            seen.add(id(obj))
            yield obj
            stack.extend(vars(obj).values())
        elif isinstance(obj, (list, tuple)):
            stack.extend(obj)
        elif isinstance(obj, dict):
            stack.extend(obj.values())


async def click(control):
    result = control.on_click(SimpleNamespace(control=control))
    if inspect.isawaitable(result):
        await result


def has_text(control, text):
    return any(isinstance(c, ft.Text) and c.value == text for c in walk(control))


def nav(page, label):
    return next(c for c in walk(page) if isinstance(c, ft.Container)
                and c.tooltip == label and c.on_click)


async def screenshot(page, name):
    page.update()
    await asyncio.sleep(1.0)
    user32 = ctypes.windll.user32
    handle = user32.FindWindowW(None, "客行录")
    assert handle, "Native application window not found"
    rect = wintypes.RECT()
    # DWM returns physical pixels even on a 150% / 200% scaled desktop.
    ctypes.windll.dwmapi.DwmGetWindowAttribute(handle, 9, ctypes.byref(rect), ctypes.sizeof(rect))
    ImageGrab.grab(bbox=(rect.left, rect.top, rect.right, rect.bottom)).save(OUT / f"{name}.png")


async def run(page):
    import ticket_db as tdb
    import ticket_design
    import json
    try:
        app.main(page)
        page.window.left = 35
        page.window.top = 35
        page.update()
        await asyncio.sleep(2)
        assert has_text(page, "每日一句")
        assert not has_text(page, "把沿途的日常，写成自己的故事。")
        await screenshot(page, "home-classic")
        for key, palette in theme.THEMES.items():
            await click(nav(page, "我的"))
            tile = next(c for c in walk(page) if isinstance(c, ft.Container)
                        and c.tooltip == "应用主题：" + palette["name"])
            await click(tile)
            assert theme.THEME_ID == key and page.bgcolor == palette["bg"]
            assert page.theme.color_scheme.surface == palette["card"]
            assert page.theme_mode == (ft.ThemeMode.DARK if palette["dark"] else ft.ThemeMode.LIGHT)
            assert json.loads(Path(theme.SETTINGS_PATH).read_text())["preset"] == key
            for label in ["旅行日志", "旅程票根", "食光小记", "影视收藏"]:
                await click(nav(page, label))
                controls = list(walk(page))
                assert any(isinstance(c, ft.Text) and c.color == palette["text"] for c in controls), (key, label, "text")
                fields = [c for c in controls if isinstance(c, ft.TextField)]
                assert fields, (key, label)
                for field in fields:
                    color = field.color or (field.text_style.color if field.text_style else None)
                    if color is not None:
                        assert color == palette["text"], (key, label, field.label, color)
                assert any(isinstance(c, ft.Container) and c.bgcolor in (palette["card"], theme.CARD_GLASS) for c in controls), (key, label, "surface")
                if key in ("classic", "midnight"):
                    await screenshot(page, key + "-" + {"旅行日志":"travel", "旅程票根":"ticket", "食光小记":"food", "影视收藏":"movie"}[label])
            await click(nav(page, "首页"))
            assert any(isinstance(c, ft.Container) and c.bgcolor == theme.HOME_SURFACE for c in walk(page))
            await screenshot(page, "home-" + key)
            print("PASS full theme across all pages:", key, flush=True)
        await click(nav(page, "我的"))
        await screenshot(page, "themes-dark")
        tile = next(c for c in walk(page) if isinstance(c, ft.Container) and c.tooltip == "应用主题：经典雾蓝")
        await click(tile)
        await screenshot(page, "themes")
        rail = tdb.add_ticket(vehicle="高铁", from_city="北京南", to_city="上海虹桥", code="G103",
            depart_date="2026-10-04", depart_time="08:00", seat="二等座 02车08F号", passenger="林晓", price="553", gate="A12")
        train = tdb.add_ticket(vehicle="火车", from_city="乌鲁木齐", to_city="呼和浩特东", code="Z21",
            depart_date="2026-10-04", depart_time="19:36", seat="硬卧 06车12号", passenger="林晓", price="325.50", gate="3")
        air = tdb.add_ticket(vehicle="飞机", from_city="北京首都国际机场", to_city="上海虹桥国际机场", code="CA1831",
            depart_date="2026-10-04", depart_time="09:30", seat="12A", passenger="林晓", gate="C18", style="classic")
        async def select_route(route):
            ctl = next(c for c in walk(page) if isinstance(c, ft.Container) and c.on_click and has_text(c, route))
            await click(ctl)
        await click(nav(page, "旅程票根"))
        for route, name in [("北京南 → 上海虹桥", "rail"), ("乌鲁木齐 → 呼和浩特东", "train")]:
            await select_route(route)
            await screenshot(page, name)
            card = next(c for c in walk(page) if isinstance(c, ft.Container) and isinstance(c.data, dict) and str(c.data.get("ticket_design", "")).startswith("rail-"))
            assert abs(card.width/card.height-ticket_design.RAIL_RATIO) < .0001
            gesture = next(c for c in walk(page) if isinstance(c, ft.GestureDetector) and c.on_tap)
            result=gesture.on_tap(SimpleNamespace(control=gesture))
            if inspect.isawaitable(result): await result
            await screenshot(page, name + "-back")
        await select_route("北京首都国际机场 → 上海虹桥国际机场")
        for style in ticket_design.AIR_STYLES:
            picker = next(c for c in walk(page) if isinstance(c, ft.Dropdown) and c.label == "飞机票面样式")
            picker.value = style
            picker.on_select(SimpleNamespace(control=picker))
            await screenshot(page, "air-" + style)
            save = next(c for c in walk(page) if isinstance(c, ft.FilledButton) and c.content == "更新当前票根")
            await click(save)
            assert tdb.get_ticket(air)["style"] == style
        await click(nav(page, "首页"))
        await click(nav(page, "旅程票根"))
        await select_route("北京首都国际机场 → 上海虹桥国际机场")
        picker = next(c for c in walk(page) if isinstance(c, ft.Dropdown) and c.label == "飞机票面样式")
        assert picker.value == "digital"
        print("PASS railway ratio, flip, five plane styles and persisted selection", flush=True)
        page.window.width = 1080
        page.window.height = 700
        await asyncio.sleep(.8)
        await screenshot(page, "air-digital-min")
        await select_route("乌鲁木齐 → 呼和浩特东")
        await screenshot(page, "train-min")
        await click(nav(page, "首页"))
        await screenshot(page, "home-min")
        global passed
        passed = True
        print("SMOKE_RESULT: ALL_OK", flush=True)
    except Exception:
        import traceback
        traceback.print_exc()
        print("SMOKE_RESULT: FAIL", flush=True)
    finally:
        await page.window.destroy()


if __name__ == "__main__":
    ft.run(run)
    temp.cleanup()
    sys.exit(0 if passed else 1)

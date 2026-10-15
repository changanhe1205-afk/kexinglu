"""客行录 · 安装包打包脚本

把 dist\\客行录 里的程序打成一个能双击安装的 setup.exe。
用之前先跑一遍 build.py，保证 dist 里是新版程序。

用法（用 .venv314 里的 Python 运行）：
    D:\\Yingjianlu\\.venv314\\Scripts\\python.exe build_installer.py

产物：dist\\installer\\客行录-安装程序-<版本号>.exe

关于 Inno Setup：
    本机装在 D:\\Tools\\InnoSetup（便携模式，不需要管理员权限）。
    换电脑时到 https://jrsoftware.org/isdl.php 装一份，
    或者把 InnoSetup 目录整个拷过去，再用 INNO_SETUP_DIR 环境变量指过去。
"""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ISS = ROOT / "installer.iss"
APP_DIR = ROOT / "dist" / "客行录"
OUT_DIR = ROOT / "dist" / "installer"


def find_iscc() -> str | None:
    """按顺序找 ISCC.exe：环境变量 → 常见安装位置 → PATH。"""
    candidates = []
    env_dir = os.getenv("INNO_SETUP_DIR")
    if env_dir:
        candidates.append(Path(env_dir) / "ISCC.exe")
    for base in (r"D:\Tools\InnoSetup",
                 r"C:\Program Files (x86)\Inno Setup 6",
                 r"C:\Program Files\Inno Setup 6"):
        candidates.append(Path(base) / "ISCC.exe")
    for c in candidates:
        if c.is_file():
            return str(c)
    from shutil import which
    return which("ISCC")


def main() -> int:
    if not APP_DIR.is_dir():
        print(f"找不到 {APP_DIR}，请先运行：python build.py")
        return 1
    if not (APP_DIR / "客行录.exe").is_file():
        print(f"{APP_DIR} 里没有 客行录.exe，请重新运行：python build.py")
        return 1
    if not ISS.is_file():
        print(f"找不到脚本 {ISS}")
        return 1

    iscc = find_iscc()
    import re
    from release_integrity import verify_manifest
    version = re.search(r'#define AppVersion "([^"]+)"', ISS.read_text(encoding='utf-8-sig')).group(1)
    try:
        verify_manifest(APP_DIR, version)
    except (OSError, ValueError, KeyError) as error:
        print(f"拒绝打包旧版或不完整的程序：{error}")
        return 1
    if not iscc:
        print("没找到 Inno Setup 的 ISCC.exe。")
        print("装一份：https://jrsoftware.org/isdl.php")
        print("已经装在别处的话，设置环境变量 INNO_SETUP_DIR 指向那个目录。")
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print("编译安装包：", iscc, ISS)
    proc = subprocess.run([iscc, str(ISS)], cwd=str(ROOT))
    if proc.returncode != 0:
        print(f"编译失败，ISCC 退出码 {proc.returncode}")
        return proc.returncode

    made = sorted(OUT_DIR.glob("*.exe"))
    print("\n安装包已生成：")
    for f in made:
        size = f.stat().st_size / 1024 / 1024
        print(f"  {f}  ({size:.1f} MB)")
    print("\n双击这个 exe 就能安装，装完开始菜单 / 桌面会有快捷方式。")
    print("用户数据在 %LOCALAPPDATA%\\客行录，卸载不会删。")
    return 0


if __name__ == "__main__":
    sys.exit(main())

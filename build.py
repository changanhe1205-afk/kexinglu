"""客行录 · 打包脚本

用法（用 .venv314 里的 Python 运行）：
    D:\\Yingjianlu\\.venv314\\Scripts\\python.exe build.py            # 正常打包，无控制台窗口
    D:\\Yingjianlu\\.venv314\\Scripts\\python.exe build.py debug       # 带控制台窗口，方便看报错
    D:\\Yingjianlu\\.venv314\\Scripts\\python.exe build.py onefile     # 打成单个 exe（启动更慢）

产物：dist\\客行录\\客行录.exe（onefile 模式下是 dist\\客行录.exe）

注意：
1. 打包机上需要先 pip install pyinstaller（.venv314 已装）
2. --collect-all 会把 flet 桌面运行时、Pillow 的资源一起打进去
3. 打包后数据目录自动改到 %LOCALAPPDATA%\\客行录，不受安装目录权限影响
"""

import sys
from pathlib import Path

try:
    import PyInstaller.__main__ as pyinstaller
except ImportError:
    sys.exit("缺少 PyInstaller，请先在 .venv314 里执行：python -m pip install pyinstaller")

APP_NAME = "客行录"
ENTRY = str(Path(__file__).with_name("main.py"))
IS_DEBUG = "debug" in sys.argv
IS_ONEFILE = "onefile" in sys.argv

# Provision at build time. End users must never need GitHub to open the app.
import flet_desktop
client_dir = flet_desktop.ensure_client_cached() / "flet"
for required in ("flet.exe", "flutter_windows.dll", "data/icudtl.dat", "data/app.so"):
    if not (client_dir / required).is_file():
        sys.exit(f"桌面运行组件缺失，停止打包：{client_dir / required}")

args = [
    ENTRY,
    f"--name={APP_NAME}",
    "--noconfirm",
    "--clean",
    f"--runtime-hook={Path(__file__).with_name('packaged_startup.py')}",
    f"--icon={Path(__file__).with_name('assets') / 'app.ico'}",
    "--add-data=assets;assets",   # 导航 Logo 用 assets/app.png
    "--console" if IS_DEBUG else "--windowed",   # debug 模式保留控制台，方便排错
    "--collect-all=flet",        # flet 桌面运行时资源
    "--collect-all=PIL",         # Pillow：聊天长图导出用
    "--collect-all=pypinyin",    # 拼音字典数据（票根姓名转拼音用）
    "--collect-all=certifi",     # 不依赖目标机器已有的公共根证书
    f"--add-data={client_dir};flet_desktop/app/flet",
]

# 环境里额外装了桌面运行时包时一并收集
for optional in ("flet_desktop", "flet-desktop"):
    try:
        __import__(optional.replace("-", "_"))
        args.append(f"--collect-all={optional}")
    except ImportError:
        pass

if IS_ONEFILE:
    args.append("--onefile")

print("PyInstaller 参数：", " ".join(args))
pyinstaller.run(args)
if not IS_ONEFILE:
    from release_integrity import write_manifest
    write_manifest(Path(__file__).parent / 'dist' / APP_NAME)
print("打包完成，程序在 dist 目录下。")

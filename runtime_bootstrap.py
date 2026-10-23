"""Resolve the packaged desktop host without a download or a per-user cache."""
import os
from pathlib import Path
import sys


def configure_desktop_runtime():
    if not getattr(sys, "frozen", False) or sys.platform not in ("win32", "linux", "darwin"):
        return None
    if sys.platform == "darwin":
        client = Path(sys._MEIPASS) / "flet_desktop/app/Flet.app"
        if not (client / "Contents/MacOS/Flet").is_file():
            raise RuntimeError("Bundled Mac client is missing")
        os.environ["FLET_VIEW_PATH"] = str(client.parent)
        return client
    client = Path(sys._MEIPASS) / "flet_desktop" / "app" / "flet"
    required = (("flet.exe", "flutter_windows.dll", "data/icudtl.dat", "data/app.so")
                if sys.platform == "win32" else ("flet", "lib/libflutter_linux_gtk.so", "data/icudtl.dat"))
    missing = [name for name in required if not (client / name).is_file()]
    if missing:
        raise RuntimeError("客行录运行组件不完整，请重新安装完整安装包。缺少：" + ", ".join(missing))
    # Flet 1.x only auto-discovers bundled archives, not extracted executables.
    # An explicit path avoids silently downloading a second host on a new PC.
    os.environ["FLET_VIEW_PATH"] = str(client)
    return client


def bind_bundled_runtime():
    """Make even Flet's fallback resolver local-only in distributed builds."""
    client = configure_desktop_runtime()
    if client is None:
        return None
    import flet_desktop

    def local_client():
        # Revalidate in case installation files have been removed since startup.
        return configure_desktop_runtime().parent

    flet_desktop.ensure_client_cached = local_client
    return client

"""PyInstaller's first runtime hook: diagnostics, TLS, then local host binding."""
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import sys
import tempfile

from app_version import VERSION


def initialize():
    log_path = None
    logger = logging.getLogger("kexinglu.startup")
    logger.setLevel(logging.INFO)
    for base in (os.environ.get("LOCALAPPDATA"), tempfile.gettempdir()):
        if not base:
            continue
        try:
            candidate = Path(base) / "客行录" / "startup.log"
            candidate.parent.mkdir(parents=True, exist_ok=True)
            handler = RotatingFileHandler(candidate, maxBytes=512_000, backupCount=2, encoding="utf-8")
            handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
            logger.addHandler(handler)
            log_path = candidate
            break
        except OSError:
            continue

    def report_failure(kind, error, traceback):
        logger.error("Startup failed", exc_info=(kind, error, traceback))
        if sys.platform != "win32":
            print(f"客行录启动失败，请查看日志：{log_path}\n{error}", file=sys.stderr)
            return
        import ctypes
        ctypes.windll.user32.MessageBoxW(
            None,
            f"客行录 {VERSION} 未能启动。\n请将以下日志发给开发者：\n{log_path or '日志无法写入'}\n\n"
            f"程序位置：{sys.executable}\n错误：{error}",
            f"客行录 {VERSION} · 启动诊断", 0x10)

    sys.excepthook = report_failure
    logger.info("version=%s executable=%s python=%s", VERSION, sys.executable, sys.version)

    # Run before framework runtime hooks/imports. Keep certificate verification on.
    import ssl
    from network_tls import https_context
    ssl._create_default_https_context = https_context

    if "--test-tls-failure" in sys.argv:
        # Explicit QA mode: reproduce the friend's failure without weakening TLS.
        import urllib.request
        import urllib.error
        original = urllib.request.urlopen

        def fail_https(url, *args, **kwargs):
            address = getattr(url, "full_url", str(url))
            if address.lower().startswith("https:"):
                logger.info("TEST_TLS_FAILURE injected")
                raise urllib.error.URLError(ssl.SSLCertVerificationError(
                    1, "[SSL: CERTIFICATE_VERIFY_FAILED] unable to get local issuer certificate"))
            return original(url, *args, **kwargs)

        urllib.request.urlopen = fail_https
        logger.info("TEST_TLS_FAILURE enabled")
        try:
            urllib.request.urlopen("https://startup-test.invalid/")
        except urllib.error.URLError:
            logger.info("TEST_TLS_FAILURE probe passed")

    from runtime_bootstrap import bind_bundled_runtime
    client = bind_bundled_runtime()
    logger.info("bundled_host=%s", client)


initialize()

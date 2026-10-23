"""Offline startup check using disposable runner data, never user records."""
import os, subprocess, tempfile, time, signal
from pathlib import Path
app=Path("dist/Kexinglu.app/Contents/MacOS/Kexinglu").resolve()
with tempfile.TemporaryDirectory(prefix="kexinglu-qa-") as home:
    env=dict(os.environ, HOME=home, APPDATA=home, LOCALAPPDATA=home, HTTPS_PROXY="http://127.0.0.1:9", HTTP_PROXY="http://127.0.0.1:9", NO_PROXY="localhost,127.0.0.1")
    with Path("dist/macos-startup.log").open("w") as log:
        p=subprocess.Popen([str(app)],env=env,stdout=log,stderr=log,start_new_session=True)
        try:
            time.sleep(20)
            if p.poll() is not None: raise RuntimeError(f"Application exited: {p.returncode}")
            processes=subprocess.check_output(["ps","-axo","command"],text=True)
            if "Flet.app/Contents/MacOS/Flet" not in processes: raise RuntimeError("Native Flet client did not launch")
            print("PASS: packaged Python host and native client running after 20 seconds; UI interaction not verified")
        finally:
            try: os.killpg(p.pid,signal.SIGTERM)
            except ProcessLookupError: pass

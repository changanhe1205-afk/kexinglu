"""Launch final bundle with an isolated HOME and ensure a native window exists."""
import os
from pathlib import Path
import subprocess
import time

app=Path('dist/kexinglu/kexinglu').resolve()
env=dict(os.environ, FLET_DESKTOP_SKIP_CACHE_CLEANUP='1',
         HTTPS_PROXY='http://127.0.0.1:9', HTTP_PROXY='http://127.0.0.1:9', NO_PROXY='localhost,127.0.0.1')
log=Path('dist/linux-smoke.txt')
with log.open('w') as output:
    process=subprocess.Popen([str(app)],stdout=output,stderr=output,env=env,start_new_session=True)
    try:
        for _ in range(45):
            time.sleep(1)
            if process.poll() is not None:
                raise RuntimeError(f'Packaged app exited: {process.returncode}')
            windows=subprocess.check_output(['xwininfo','-root','-tree'],text=True)
            if '客行录' in windows:
                time.sleep(8)
                if process.poll() is not None:
                    raise RuntimeError('App exited after opening window')
                from PIL import ImageGrab
                ImageGrab.grab().save('dist/linux-smoke.png')
                output.write('\nPASS: packaged native window opened with isolated HOME.\n')
                output.flush()
                break
        else:
            raise RuntimeError('No native application window after 45 seconds')
    except Exception:
        output.flush()
        print(log.read_text(),flush=True)
        for path in Path('/tmp/客行录').glob('startup.log*'):
            print(path.read_text(),flush=True)
        raise
    finally:
        import signal
        try: os.killpg(process.pid,signal.SIGTERM)
        except ProcessLookupError: pass
print(log.read_text())

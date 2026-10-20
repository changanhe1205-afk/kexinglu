"""Open local exports with the platform default application, without a shell."""
import os
from pathlib import Path
import subprocess
import sys


def open_local(path):
    target = str(Path(path).resolve(strict=True))
    if sys.platform == 'win32':
        os.startfile(target)
    else:
        subprocess.Popen(['open' if sys.platform == 'darwin' else 'xdg-open', target],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

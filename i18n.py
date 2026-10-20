"""Explicit UI string localization. Stored record content is never rewritten."""
import json
import sys
from pathlib import Path
import config

LANGUAGES={'zh':'简体中文','zh-TW':'繁體中文','en':'English','ja':'日本語'}
_catalog=json.loads((Path(getattr(sys,'_MEIPASS',Path(__file__).parent))/'assets/ui-locales.json').read_text('utf-8'))
def tr(text):
    return _catalog.get(text,{}).get(config.get('language','zh'),text)

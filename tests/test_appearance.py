"""Theme persistence and old ticket database upgrade, isolated in subprocesses."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class AppearanceTests(unittest.TestCase):
    def test_theme_survives_new_process(self):
        with tempfile.TemporaryDirectory() as folder:
            setup = f"import config; config._cache={{'data_dir':{folder!r}}}; import theme; "
            for name in ('classic', 'graphite', 'sand', 'lilac', 'midnight', 'carbon', 'sea', 'sage', 'clay', 'plum', 'ocean', 'coffee'):
                subprocess.run([sys.executable, '-c', setup + f"theme.set_theme(preset={name!r})"], cwd=ROOT, check=True)
                subprocess.run([sys.executable, '-c', setup + f"assert theme.THEME_ID == {name!r}; assert theme.BG == theme.THEMES[{name!r}]['bg']"], cwd=ROOT, check=True)

    def test_old_ticket_styles_upgrade_without_losing_record(self):
        with tempfile.TemporaryDirectory() as folder:
            code = f'''
import config
config._cache = {{'data_dir': {folder!r}}}
import database
with database.get_conn() as conn:
    conn.execute("CREATE TABLE tickets (id INTEGER PRIMARY KEY, vehicle TEXT, from_city TEXT, to_city TEXT, depart_date TEXT, depart_time TEXT, arrive_time TEXT, code TEXT, seat TEXT, passenger TEXT, note TEXT, image TEXT, created_at TEXT)")
    conn.execute("INSERT INTO tickets (id,vehicle,from_city,to_city,code) VALUES (1,'飞机','北京','上海','CA1831')")
import ticket_db
record = ticket_db.get_ticket(1)
assert record['code'] == 'CA1831' and record['style'] == 'rose'
ticket_db.update_ticket(1, **{{k: record.get(k, '') for k in ticket_db.FIELDS if k != 'style'}}, style='digital')
assert ticket_db.get_ticket(1)['style'] == 'digital'
ticket_db.init_db()
assert ticket_db.get_ticket(1)['style'] == 'digital'
'''
            subprocess.run([sys.executable, '-c', code], cwd=ROOT, check=True)

if __name__ == '__main__':
    unittest.main()

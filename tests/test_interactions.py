"""Regression checks for local calendar dates and map projection/cache math."""
from datetime import datetime, date, timedelta, timezone
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from date_utils import calendar_date, open_calendar
import tile_map

class InteractionTests(unittest.TestCase):
    def test_datepicker_utc_transport_keeps_local_day(self):
        for day in (5, 7, 1):
            local = datetime(2026, 10, day).astimezone()
            wire = local.astimezone(timezone.utc)
            self.assertEqual(calendar_date(wire), f'2026-10-{day:02d}')
        self.assertEqual(calendar_date(date(2026, 10, 5)), '2026-10-05')
        self.assertEqual(calendar_date(datetime(2026, 10, 7)), '2026-10-07')
        self.assertEqual(calendar_date(None), '')

    def test_open_calendar_reselects_existing_date(self):
        from types import SimpleNamespace
        picker = SimpleNamespace(value=None)
        shown = []
        page = SimpleNamespace(show_dialog=shown.append)
        open_calendar(page, picker, '2026-10-07')
        self.assertEqual(picker.value, date(2026,10,7))
        self.assertEqual(shown, [picker])

    def test_zoom_keeps_anchor_and_clamps(self):
        view = tile_map.View(640, 480, 116, 35, 7)
        anchor = (240, 180)
        lon, lat = view.lonlat_at(*anchor)
        zoomed = view.zoomed(8, anchor)
        x, y = zoomed(lon,lat)
        self.assertAlmostEqual(x,anchor[0],places=6)
        self.assertAlmostEqual(y,anchor[1],places=6)
        self.assertEqual(view.zoomed(100).zoom,tile_map.MAX_ZOOM)

    def test_fit_includes_north_and_south_with_padding(self):
        v=tile_map.fit_view(608,525,(116.25,30.12,120.3,40.05),pad=.65)
        for lon,lat in ((116.25,30.12),(120.3,40.05)):
            x,y=v(lon,lat)
            self.assertTrue(608*.17 <= x <= 608*.83)
            self.assertTrue(525*.17 <= y <= 525*.83)

    def test_tile_pool_reuses_visible_images(self):
        view=tile_map.View(640,480,116,35,7)
        pool={}
        before=view.project_all('std',1,pool)
        after=view.shifted(5,5).project_all('std',1,pool)
        self.assertTrue(set(map(id,before)) & set(map(id,after)))
        width,label=tile_map.scale_bar(view)
        self.assertTrue(0 < width <= 90)
        self.assertIn('km',label)

if __name__=='__main__': unittest.main()

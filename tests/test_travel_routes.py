import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import database
import travel_routes as routes

class RouteTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        root=Path(self.temp.name)
        for key,value in [('BASE_DIR',str(root)),('POSTER_DIR',str(root/'posters')),('DB_PATH',str(root/'test.db'))]:
            p=patch.object(database,key,value);p.start();self.addCleanup(p.stop)
        self.points=[routes.parse_line('北京'),routes.parse_line('上海')]

    def test_modes_and_new_never_overwrites(self):
        a=routes.save_route('air','',self.points)
        b=routes.save_route('air','第二次',self.points)
        routes.save_route('rail','',self.points)
        self.assertNotEqual(a,b)
        routes.save_route('air','修改',self.points,a)
        self.assertEqual(len(routes.list_routes('air')),2)
        self.assertEqual(len(routes.list_routes('rail')),1)
        with self.assertRaises(ValueError):routes.save_route('rail','越界修改',self.points,a)
        routes.delete_route('rail',a)
        self.assertEqual(len(routes.list_routes('air')),2)
        routes.delete_route('air',a)
        self.assertEqual(len(routes.list_routes('air')),1)

    def test_explicit_coordinates_and_exact_names(self):
        self.assertEqual(routes.parse_line('观音机场 | 117.555，34.059')['lon'],117.555)
        with self.assertRaises(ValueError):routes.parse_line('北京不存在的机场')
        with self.assertRaises(ValueError):routes.parse_line('不存在')
        for coords in ['nan,0','181,0','0,86','0,inf']:
            with self.assertRaises(ValueError):routes.validate_points([self.points[0],routes.parse_line('测试 | '+coords)])
        with self.assertRaises(ValueError):routes.validate_points([self.points[0]]*2)
        self.assertEqual(len(routes.validate_points([routes.parse_line('东京 | 139.69,35.68'),routes.parse_line('洛杉矶 | -118.24,34.05')])),2)

if __name__=='__main__':unittest.main()

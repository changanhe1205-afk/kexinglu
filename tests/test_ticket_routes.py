import unittest
from copy import deepcopy
import ticket_routes as r

class TicketRouteTests(unittest.TestCase):
    def test_airport_aliases_and_ambiguous_input(self):
        for name in ('观音机场','徐州观音','徐州观音国际机场T2','ＸＵＺ'):
            self.assertEqual(r.endpoint(name,'air')['lon'],r.endpoint('XUZ','air')['lon'])
        self.assertIsNone(r.endpoint('北京未知机场','air'))
        self.assertIsNone(r.endpoint('国际机场','air'))

    def test_airport_names_codes_and_world(self):
        a=r.endpoint('徐州观音国际机场','air');b=r.endpoint('XUZ','air')
        self.assertEqual(a['lon'],b['lon']);self.assertFalse(a['approximate'])
        self.assertTrue(117<a['lon']<118 and 33<a['lat']<35)
        self.assertLess(r.endpoint('LAX','air')['lon'],0)
        self.assertEqual(r.endpoint('NRT · 东京成田国际机场','air')['lon'],r.endpoint('东京成田国际机场','air')['lon'])
    def test_rail_tickets_and_station_city(self):
        records=[dict(id=1,vehicle='高铁',from_city='北京南站',to_city='上海虹桥'),dict(id=2,vehicle='火车',from_city='北京',to_city='上海')]
        routes,missing=r.from_tickets(records,'rail')
        self.assertEqual(len(routes),2);self.assertFalse(missing)
        self.assertTrue(all(not p['approximate'] for p in routes[0]['points']))
    def test_saved_railway_station_regression(self):
        pairs=[('余姚北','枣庄'),('独山东','贵阳北'),('枣庄','济南西'),('重庆西','独山东'),('成都东','都匀东'),('厦门北','福州南'),('贵阳北','杭州东')]
        records=[dict(id=i,vehicle='高铁',from_city=a,to_city=b) for i,(a,b) in enumerate(pairs)]
        original=deepcopy(records)
        routes,missing=r.from_tickets(records,'rail')
        self.assertEqual(len(routes),7);self.assertFalse(missing);self.assertEqual(records,original)
        self.assertEqual(r.endpoint(' 余姚北站 ','rail')['lon'],121.164)
        self.assertAlmostEqual(r.endpoint('枣庄','rail')['lat'],34.780764)
        self.assertNotEqual(r.endpoint('北京南','rail')['lon'],r.endpoint('北京','rail')['lon'])
        self.assertIsNone(r.endpoint('不存在的高铁站','rail'))

    def test_no_writes_and_unknown_not_guessed(self):
        records=[dict(id=1,vehicle='飞机',from_city='北京未知机场',to_city='LAX')];original=deepcopy(records)
        routes,missing=r.from_tickets(records,'air')
        self.assertFalse(routes);self.assertEqual(len(missing),1);self.assertEqual(records,original)
    def test_edit_delete_derived_without_stale_records(self):
        records=[dict(id=1,vehicle='飞机',from_city='XUZ',to_city='PEK')]
        first=r.from_tickets(records,'air')[0][0]['points'][-1]
        records[0]['to_city']='LAX'
        self.assertNotEqual(r.from_tickets(records,'air')[0][0]['points'][-1],first)
        self.assertEqual(r.from_tickets([],'air'),([],[]))

if __name__=='__main__':unittest.main()

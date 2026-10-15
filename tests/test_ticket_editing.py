import unittest
from ticket_money import amount_text,cny_price


class TicketFareTests(unittest.TestCase):
    def test_cny_normalization_and_legacy_forms(self):
        for raw in ('680','CNY 680.00','cny680','￥680.0','人民币680元'):
            self.assertEqual(amount_text(raw),'680.00')
            self.assertEqual(cny_price(raw),'CNY 680.00')
        self.assertEqual(cny_price('1,234.5'),'CNY 1234.50')
        self.assertEqual(cny_price(0),'CNY 0.00')
        self.assertEqual(cny_price(''),'CNY —')

    def test_bad_prices_do_not_silently_become_numbers(self):
        for raw in ('NaN','Infinity','-1','12.345','abc'):
            with self.assertRaises(ValueError):amount_text(raw)
        self.assertEqual(cny_price('USD 300'),'USD 300')

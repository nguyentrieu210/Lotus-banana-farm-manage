import unittest
from datetime import date, datetime

from lotus_farm import print_kit as pk


class PrintKit(unittest.TestCase):
    def test_amount_in_words_reads_vietnamese_accounting_style(self):
        cases = {
            0: 'Không đồng chẵn.',
            21: 'Hai mươi mốt đồng chẵn.',
            15: 'Mười lăm đồng chẵn.',
            105: 'Một trăm linh năm đồng chẵn.',
            1005: 'Một nghìn không trăm linh năm đồng chẵn.',
            19_500_000: 'Mười chín triệu năm trăm nghìn đồng chẵn.',
            1_000_000_000: 'Một tỷ đồng chẵn.',
            2_001_000_025: 'Hai tỷ không trăm linh một triệu không trăm hai mươi lăm đồng chẵn.',
            2_000_001_025: 'Hai tỷ không trăm linh một nghìn không trăm hai mươi lăm đồng chẵn.',
            1_200_000_000_000: 'Một nghìn hai trăm tỷ đồng chẵn.',
        }
        for value, text in cases.items():
            with self.subTest(value=value):
                self.assertEqual(pk.amount_in_words_vi(value), text)
        self.assertEqual(pk.number_in_words_vi(-54), 'âm năm mươi bốn')
        self.assertEqual(pk.number_in_words_vi(19_499_999.6), 'mười chín triệu năm trăm nghìn')

    def test_number_money_and_dates_use_one_style(self):
        self.assertEqual(pk.number(19_500_000), '19.500.000')
        self.assertEqual(pk.number(3.5), '3,5')
        self.assertEqual(pk.number(None), '0')
        self.assertEqual(pk.number(float('nan')), '0')
        self.assertEqual(pk.money(1.0), '1 ₫')
        self.assertEqual(pk.money(19_500_000.4), '19.500.000 ₫')
        self.assertEqual(pk.vn_date('2026-10-20'), '20/10/2026')
        self.assertEqual(pk.vn_date(date(2026, 1, 5)), '05/01/2026')
        self.assertEqual(pk.vn_datetime('2026-10-20 07:31:47.123'), '20/10/2026 07:31')
        self.assertEqual(pk.vn_datetime(datetime(2026, 10, 20, 7, 5)), '20/10/2026 07:05')
        self.assertEqual(pk.vn_date(None), '')

    def test_status_watermark_units_and_garden_label(self):
        self.assertEqual((pk.status_label(0), pk.status_label(1), pk.status_label(2)), ('Nháp', 'Đã duyệt', 'Đã hủy'))
        self.assertEqual((pk.watermark(0), pk.watermark(1), pk.watermark(2)), ('BẢN NHÁP', None, 'ĐÃ HỦY'))
        self.assertEqual(pk.unit('Nos'), 'Cái')
        self.assertEqual(pk.unit('Thùng 12kg'), 'Thùng 12kg')
        self.assertEqual(pk.garden_label('Dự án chuối Thuận Phú'), 'VƯỜN CHUỐI Thuận Phú')


if __name__ == '__main__':
    unittest.main()

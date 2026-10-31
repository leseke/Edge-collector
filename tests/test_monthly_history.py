import io
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts'))
import monthly_history as m

URL = 'https://promoklocki.pl/lego-icons-10312-klub-jazzowy-h22044'

def rows(points):
    return iter([(1,['Date','Price','url'])] + [(i+2,[month,price,URL]) for i,(month,price) in enumerate(points)])

class MonthlyTests(unittest.TestCase):
    def test_real_scope_preserved_and_zero_not_free_product(self):
        series, counts = m.normalize(rows([('2023-01','100'),('2023-02','0')]))
        self.assertIsNone(series[0]['points'][1]['price_pln'])
        self.assertEqual(counts['zero_coded_missing_prices'],1)
        report=m.summarize(series,counts)
        self.assertEqual(report['currency'],'PLN')
        self.assertFalse(report['completed_sales_verified'])
        self.assertFalse(report['linked_to_daily_stock_estimator'])

    def test_repeated_rows_do_not_inflate_history(self):
        series,c=m.normalize(rows([('2023-01','100'),('2023-01','100')]))
        self.assertEqual(len(series[0]['points']),1)
        self.assertEqual(c['duplicate_rows'],1)

    def test_conflicting_duplicate_rejected(self):
        with self.assertRaises(ValueError):m.normalize(rows([('2023-01','100'),('2023-01','101')]))

    def test_gap_and_missing_price_prevent_complete_window(self):
        for points in [[('2023-01','100'),('2023-02','0'),('2023-03','100'),('2023-04','100')],
                       [('2023-01','100'),('2023-02','100'),('2023-04','100'),('2023-05','100')]]:
            series,c=m.normalize(rows(points))
            self.assertEqual(m.summarize(series,c)['coverage']['complete_four_consecutive_month_windows'],0)

    def test_exact_consecutive_window(self):
        series,c=m.normalize(rows([(f'2023-0{i}','100') for i in range(1,5)]))
        self.assertEqual(m.summarize(series,c)['coverage']['complete_four_consecutive_month_windows'],1)

    def test_invalid_price_and_period_rejected(self):
        for month,price in [('2023-07','100'),('2023-00','100'),('2023-01','NaN'),('2023-01','-1')]:
            with self.assertRaises(ValueError):m.normalize(rows([(month,price)]))

    def test_unpinned_source_bytes_rejected(self):
        with self.assertRaises(ValueError):m.verify(b'not the published workbook')

    def test_formulas_are_not_observed_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'a.xlsx'
            with zipfile.ZipFile(p,'w') as z:
                z.writestr('xl/worksheets/sheet1.xml','<worksheet xmlns="'+m.N[1:-1]+'"><sheetData><row r="1"><c r="A1"><f>1+1</f><v>2</v></c></row></sheetData></worksheet>')
            with self.assertRaises(ValueError):list(m.xlsx_rows(p))

if __name__ == '__main__':unittest.main()

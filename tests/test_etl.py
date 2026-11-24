import csv
import io
import tempfile
import unittest
import zipfile
from decimal import Decimal
from pathlib import Path
from etl.clean import clean
from etl.classify import classify
from etl.extract import sheets, COLUMNS
from etl.load_fact import copy_rows

class RulesTest(unittest.TestCase):
    def raw(self, **changes):
        row = dict(zip(COLUMNS,['100','00123',' Item ','2','2010-12-01 08:00:00','1.25','12345.0','UK']))
        row.update(changes)
        return row

    def test_all_sign_combinations(self):
        for invoice in ['100','C100']:
            for q in [-1,0,1]:
                for price in [Decimal('-1'),Decimal('0'),Decimal('1')]:
                    if q==0 or price<=0 or (invoice.startswith('C') and q>0):
                        with self.assertRaises(ValueError): classify(invoice,q,price)
                    else:
                        kind,amount=classify(invoice,q,price)
                        expected='RETURN_CANCELLATION' if invoice.startswith('C') else 'SALE' if q>0 else 'ADJUSTMENT'
                        self.assertEqual((kind,amount),(expected,q*price))

    def test_normalization_and_exact_money(self):
        row=clean(self.raw(Price='0.1234'))
        self.assertEqual(row[3],'00123')
        self.assertEqual(row[5],'12345')
        self.assertEqual(row[-2],Decimal('.2468'))
        self.assertEqual(clean(self.raw(**{'Customer ID':''}))[5],None)
        self.assertEqual(clean(self.raw(Invoice=' c100 ',Quantity='-2'))[-1],'RETURN_CANCELLATION')

    def test_invalid_fields(self):
        for change in [dict(Quantity='text'),dict(Quantity='1.5'),dict(Price='NaN'),dict(Price='0.00001'),
                       dict(InvoiceDate='nonsense'),dict(StockCode=''),dict(Country=''),
                       {'Customer ID':'1.2'},dict(Quantity='2147483648'),dict(Price='100000000')]:
            with self.subTest(change=change),self.assertRaises(ValueError): clean(self.raw(**change))

    def test_copy_preserves_empty_null_and_special_characters(self):
        class Cursor:
            def copy_expert(self,sql,buf): self.text=buf.read()
        cur=Cursor()
        copy_rows(cur,'tmp','a,b,c',[(None,'','a,"b\n雪')])
        self.assertTrue(cur.text.startswith(',"",'))
        self.assertEqual(list(csv.reader(io.StringIO(cur.text)))[0],['','','a,"b\n雪'])

    def test_reconcile_checks_independent_python_totals(self):
        from etl.reconcile import reconcile
        class Cursor:
            def execute(self, sql): pass
            def fetchone(self): return (2, True)
            def fetchall(self): return [('SALE', Decimal('2.50'), Decimal('2.50'))]
        cur=Cursor()
        self.assertEqual(reconcile(cur,3,2,1,0,{'SALE':Decimal('2.5')})['rows_existing'],2)
        with self.assertRaises(ValueError): reconcile(cur,3,2,1,0,{'SALE':Decimal('2.6')})
        with self.assertRaises(ValueError): reconcile(cur,4,2,1,0,{'SALE':Decimal('2.5')})

    def test_reconcile_empty_batch(self):
        from etl.reconcile import reconcile
        class Cursor:
            def execute(self, sql): pass
            def fetchone(self): return (0, None)
            def fetchall(self): return []
        self.assertTrue(reconcile(Cursor(),2,0,2,0,{})['rows_ok'])

    def test_streaming_sheets_global_ids(self):
        ns='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
        rel='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
        def sheet(invoice):
            rows=[COLUMNS,[invoice,'00123','Item','2','40513.5','1.25','','UK']]
            return f'<worksheet xmlns="{ns}"><sheetData>'+''.join(
                '<row>'+''.join(f'<c r="{chr(65+i)}{n}" t="inlineStr"><is><t>{v}</t></is></c>' for i,v in enumerate(values))+'</row>'
                for n,values in enumerate(rows,1))+'</sheetData></worksheet>'
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'fixture.xlsx'
            with zipfile.ZipFile(path,'w') as z:
                z.writestr('xl/workbook.xml',f'<workbook xmlns="{ns}" xmlns:r="{rel}"><sheets><sheet name="a" r:id="r1"/><sheet name="b" r:id="r2"/></sheets></workbook>')
                z.writestr('xl/_rels/workbook.xml.rels','<Relationships><Relationship Id="r1" Target="worksheets/a.xml"/><Relationship Id="r2" Target="worksheets/b.xml"/></Relationships>')
                z.writestr('xl/worksheets/a.xml',sheet('100'))
                z.writestr('xl/worksheets/b.xml',sheet('101'))
            result=[]
            for name,records in sheets(path): result.extend((name,i,raw) for i,raw in records)
            self.assertEqual([(n,i) for n,i,_ in result],[('a',1),('b',2)])
            self.assertEqual(result[0][2]['InvoiceDate'],'2010-12-01 12:00:00')

if __name__=='__main__': unittest.main()

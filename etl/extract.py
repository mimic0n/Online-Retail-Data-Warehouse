"""Streaming XLSX reader using the standard library (no million-row DataFrame)."""
import hashlib
import posixpath
import re
import zipfile
from datetime import datetime, timedelta
from xml.etree import ElementTree as ET
COLUMNS = ['Invoice','StockCode','Description','Quantity','InvoiceDate','Price','Customer ID','Country']
NS = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'

def fingerprint(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''): h.update(block)
    return h.hexdigest()

def sheets(path):
    with zipfile.ZipFile(path) as z:
        strings = []
        if 'xl/sharedStrings.xml' in z.namelist():
            with z.open('xl/sharedStrings.xml') as stream:
                for _, node in ET.iterparse(stream, events=('end',)):
                    if node.tag == NS+'si':
                        strings.append(''.join(t.text or '' for t in node.iter(NS+'t')))
                        node.clear()
        book = ET.fromstring(z.read('xl/workbook.xml'))
        props = book.find(NS+'workbookPr')
        epoch = datetime(1904,1,1) if props is not None and props.get('date1904') in ('1','true') else datetime(1899,12,30)
        rels = {n.get('Id'): n.get('Target') for n in ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
        offset = 0
        for sheet in book.find(NS+'sheets'):
            target = rels[sheet.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')]
            target = target.lstrip('/') if target.startswith('/') else posixpath.normpath('xl/'+target)
            def records(target=target):
                nonlocal offset
                header = None
                with z.open(target) as stream:
                    context = ET.iterparse(stream, events=('start','end'))
                    _, root = next(context)
                    for event,node in context:
                        if event != 'end' or node.tag != NS+'row': continue
                        values = {}
                        for cell in node:
                            ref = re.match(r'[A-Z]+',cell.get('r','')).group()
                            val = cell.find(NS+'v')
                            text = '' if val is None else val.text or ''
                            if cell.get('t') == 's': text = strings[int(text)]
                            elif cell.get('t') == 'inlineStr': text = ''.join(t.text or '' for t in cell.iter(NS+'t'))
                            values[ref] = text.strip()
                        if header is None:
                            header = values
                            if set(header.values()) != set(COLUMNS): raise ValueError(f'Unexpected columns: {header}')
                        else:
                            raw = {key:values.get(col,'') for col,key in header.items()}
                            # XLSX numeric cells serialize IEEE-754 artifacts. Match Excel/openpyxl
                            # numeric interpretation before constructing Decimal in clean().
                            try: raw['Price'] = str(float(raw['Price']))
                            except ValueError: pass
                            date = raw['InvoiceDate']
                            if date:
                                try: raw['InvoiceDate'] = (epoch+timedelta(seconds=round(float(date)*86400))).isoformat(sep=' ',timespec='seconds')
                                except (ValueError,OverflowError): pass
                            offset += 1
                            yield offset,raw
                        node.clear()
                        # Remove processed row elements to bound worksheet memory.
                        parent = root.find(NS+'sheetData')
                        if parent is not None: parent.clear()
            yield sheet.get('name'),records()

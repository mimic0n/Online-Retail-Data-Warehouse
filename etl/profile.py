"""Profile the original workbook without requiring a database or third-party packages."""
import argparse
import json
import re
import sqlite3
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from .extract import sheets, fingerprint
from .clean import clean


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--source',default='data/raw/online-retail-ii.xlsx')
    p.add_argument('--output',default='docs/data_profile.md')
    args = p.parse_args()
    counts = Counter()
    by_sheet = Counter()
    reasons = Counter()
    kinds = Counter()
    totals = defaultdict(Decimal)
    countries = Counter()
    stock = Counter()
    prefixes = Counter()
    signs = Counter()
    samples = {}
    min_date = max_date = None
    max_decimals = 0
    # Exact duplicate comparison stored on disk; keep all source rows in ETL.
    with tempfile.TemporaryDirectory() as temp:
        db = sqlite3.connect(str(Path(temp)/'duplicates.db'))
        db.execute('CREATE TABLE seen (raw TEXT PRIMARY KEY) WITHOUT ROWID')
        for name, records in sheets(args.source):
            for row_id, raw in records:
                counts['read'] += 1
                by_sheet[name] += 1
                counts['missing_customer'] += not raw['Customer ID']
                counts['missing_description'] += not raw['Description']
                countries[raw['Country']] += 1
                invoice = raw['Invoice'].upper()
                counts['c_prefix'] += invoice.startswith('C')
                if invoice[:1].isalpha() and not invoice.startswith('C'):
                    prefixes[invoice] += 1
                if not re.fullmatch(r'\d{5}',raw['StockCode']): stock[raw['StockCode']] += 1
                try:
                    price = Decimal(raw['Price'])
                    q = Decimal(raw['Quantity'])
                    max_decimals = max(max_decimals,max(0,-price.normalize().as_tuple().exponent))
                    signs[f'quantity {(q>0)-(q<0)}, price {(price>0)-(price<0)}'] += 1
                except (InvalidOperation,TypeError): pass
                text = json.dumps(raw,sort_keys=True,ensure_ascii=False)
                cur = db.execute('INSERT OR IGNORE INTO seen VALUES(?)',(text,))
                counts['duplicate_rows'] += cur.rowcount == 0
                try:
                    row = clean(raw)
                except ValueError as exc:
                    reasons[str(exc)] += 1
                    continue
                counts['valid'] += 1
                amount, kind = row[-2:]
                kinds[kind] += 1
                totals[kind] += amount
                date = row[1]
                min_date = date if min_date is None else min(date,min_date)
                max_date = date if max_date is None else max(date,max_date)
                # Select invoices across sales, cancellations and unknown customers.
                group = 'UNKNOWN_CUSTOMER' if row[5] is None else kind
                if invoice not in samples and sum(v['group']==group for v in samples.values()) < 7:
                    samples[invoice] = {'group':group,'rows':0,'amount':Decimal(0)}
                if invoice in samples:
                    samples[invoice]['rows'] += 1
                    samples[invoice]['amount'] += amount
                if counts['read'] % 100000 == 0: print(f"Profile: {counts['read']:,}",flush=True)
        db.close()
    counts['rejected'] = counts['read'] - counts['valid']
    result = {'source':args.source,'sha256':fingerprint(args.source),'profiled_at':datetime.now(timezone.utc).isoformat(),
              'sheets':dict(by_sheet),'counts':dict(counts),'rejections':dict(reasons),
              'transaction_rows':dict(kinds),'amounts':{k:str(v) for k,v in totals.items()},
              'valid_date_min':str(min_date),'valid_date_max':str(max_date),'max_price_decimals':max_decimals,
              'quantity_price_signs':dict(signs),'countries':dict(countries),
              'nonstandard_stock_codes':dict(stock),'other_letter_invoices':dict(prefixes),
              'invoice_samples':{k:{**v,'amount':str(v['amount'])} for k,v in samples.items()}}
    out = Path(args.output)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.with_suffix('.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    lines = ['# Hồ sơ dữ liệu thực tế','',f"Nguồn cục bộ: `{args.source}`",f"SHA-256: `{result['sha256']}`",
             f"Thời điểm lập hồ sơ UTC: {result['profiled_at']}",'',
             'Đếm trực tiếp workbook bằng bộ đọc streaming. Giữ ngày gốc và toàn bộ dòng trùng; giữ mã phí đặc biệt. File CSV có sẵn không được dùng làm nguồn chuẩn.',
             '', '| Sheet | Số dòng |','|---|---:|']
    lines += [f'| {k} | {v:,} |' for k,v in by_sheet.items()]
    lines += ['','| Kiểm tra | Kết quả |','|---|---:|']
    lines += [f'| {k} | {v:,} |' for k,v in counts.items()]
    lines += [f'| Số lẻ Price tối đa | {max_decimals} |','',f'Phạm vi ngày hợp lệ: {min_date} → {max_date}.','',
              '| Loại | Dòng hợp lệ | Tổng tiền GBP |','|---|---:|---:|']
    lines += [f'| {k} | {v:,} | {totals[k]:.4f} |' for k,v in kinds.items()]
    lines += ['','| Lỗi | Số dòng |','|---|---:|']+[f'| {k} | {v:,} |' for k,v in reasons.items()]
    lines += ['','Chi tiết quốc gia, mã đặc biệt, dấu số lượng/giá và mẫu hóa đơn ở file JSON cạnh tài liệu này.',
              'Các mẫu hóa đơn là tổng được tính tự động để đối chiếu, chưa phải xác minh thủ công.',
              'Số liệu trên là kết quả Python trên nguồn, chưa phải bằng chứng kho PostgreSQL đã nạp thành công.',
              '', 'Quy tắc: khách thiếu mã dùng khóa 0; tên sản phẩm lấy mô tả không trống tại ngày giao dịch gần nhất, hòa ngày chọn mã file rồi số dòng lớn hơn. Thiếu mô tả hoàn toàn dùng Unknown product.',
              'Phân loại hủy phục vụ phân tích, chưa xác nhận hoàn tiền hay đối chiếu từng đơn hủy với đơn gốc.',
              '', 'Ghi nguồn theo kế hoạch: D. Chen (2012), UCI Online Retail II, DOI 10.24432/C5CG6D, CC BY 4.0. Ngày tải file chưa được cung cấp; không suy ra từ thời gian sửa file.']
    out.write_text('\n'.join(lines)+'\n')
    print(json.dumps({'sheets':dict(by_sheet),'counts':dict(counts),'amounts':result['amounts']}))

if __name__=='__main__': main()

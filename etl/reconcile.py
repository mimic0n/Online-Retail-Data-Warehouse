from decimal import Decimal


def reconcile(cur, read, valid, rejected, inserted, expected_totals=None):
    cur.execute('''SELECT count(*),bool_and(f.invoice_no=t.invoice_no AND f.invoice_datetime=t.invoice_datetime
    AND f.quantity=t.quantity AND f.unit_price=t.unit_price AND f.line_amount=t.line_amount
    AND f.transaction_type=t.transaction_type AND p.stock_code=t.stock_code AND k.country=t.country
    AND c.customer_id IS NOT DISTINCT FROM t.customer_id) FROM tmp_valid t
    JOIN dw.fact_sales f USING(source_file_id,source_row_id)
    JOIN dw.dim_product p USING(product_key) JOIN dw.dim_country k USING(country_key)
    JOIN dw.dim_customer c USING(customer_key)''')
    count, values_match = cur.fetchone()
    cur.execute('''SELECT t.transaction_type,sum(t.line_amount),sum(f.line_amount)
    FROM tmp_valid t JOIN dw.fact_sales f USING(source_file_id,source_row_id) GROUP BY t.transaction_type''')
    totals = {kind: {'valid_table':str(a),'warehouse':str(b)} for kind,a,b in cur.fetchall()}
    ok = read == valid+rejected and valid == count and (values_match is not False)
    ok = ok and 0 <= inserted <= valid
    for kind,values in totals.items():
        expected = Decimal(values['valid_table']) if expected_totals is None else expected_totals.get(kind,Decimal(0))
        values['python'] = str(expected)
        ok = ok and expected == Decimal(values['valid_table']) == Decimal(values['warehouse'])
    if expected_totals is not None: ok = ok and set(expected_totals) == set(totals)
    if not ok: raise ValueError('RECONCILIATION_FAILED')
    return {'rows_ok':True,'amounts':totals,'rows_existing':valid-inserted}

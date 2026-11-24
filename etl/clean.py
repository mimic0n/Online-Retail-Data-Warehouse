from datetime import datetime
from decimal import Decimal, InvalidOperation
from .classify import classify

def integer(value, name):
    try:
        n = Decimal(value)
        if not n.is_finite() or n != n.to_integral_value(): raise ValueError()
        return int(n)
    except (InvalidOperation, ValueError): raise ValueError('INVALID_' + name) from None

def clean(raw):
    invoice = raw['Invoice'].strip().upper()
    stock = raw['StockCode'].strip()
    country = raw['Country'].strip()
    if not invoice or not stock or not country: raise ValueError('MISSING_REQUIRED_CODE_OR_COUNTRY')
    quantity = integer(raw['Quantity'], 'QUANTITY')
    if not -(2**31) <= quantity < 2**31: raise ValueError('QUANTITY_OVERFLOW')
    customer = None
    if raw['Customer ID'].strip():
        n = integer(raw['Customer ID'], 'CUSTOMER_ID')
        if n <= 0: raise ValueError('INVALID_CUSTOMER_ID')
        customer = str(n)
    try:
        price = Decimal(raw['Price'])
        if not price.is_finite() or abs(price) >= Decimal('100000000') or price != price.quantize(Decimal('.0001')):
            raise ValueError()
    except (InvalidOperation, ValueError): raise ValueError('INVALID_PRICE_PRECISION_OR_RANGE') from None
    try: date = datetime.fromisoformat(raw['InvoiceDate'])
    except ValueError: raise ValueError('INVALID_INVOICE_DATE') from None
    if date.tzinfo is not None: raise ValueError('TIMEZONE_NOT_SUPPORTED')
    kind, amount = classify(invoice, quantity, price)
    return (invoice,date,int(date.strftime('%Y%m%d')),stock,raw['Description'].strip(),customer,country,quantity,price,amount,kind)

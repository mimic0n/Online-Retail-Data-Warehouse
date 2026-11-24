from decimal import Decimal
def classify(invoice, quantity, price):
    if quantity == 0: raise ValueError('ZERO_QUANTITY')
    if price <= 0: raise ValueError('NON_POSITIVE_PRICE')
    if invoice.startswith('C'):
        if quantity > 0: raise ValueError('CANCELLATION_POSITIVE_QUANTITY')
        kind = 'RETURN_CANCELLATION'
    else: kind = 'SALE' if quantity > 0 else 'ADJUSTMENT'
    amount = quantity * price
    if abs(amount) >= Decimal('10000000000'): raise ValueError('AMOUNT_OVERFLOW')
    return kind, amount

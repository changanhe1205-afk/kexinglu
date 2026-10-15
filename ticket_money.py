"""CNY presentation without rewriting the text field while the user types."""
from decimal import Decimal, InvalidOperation
import re


def amount_text(raw):
    text=str(raw if raw is not None else '').strip()
    if not text:return ''
    text=re.sub(r'^(?:CNY\s*|人民币\s*|[¥￥]\s*)','',text,flags=re.I)
    text=re.sub(r'\s*元$','',text).replace(',','').strip()
    if not re.fullmatch(r'\d+(?:\.\d{0,2})?',text):
        raise ValueError('票价请填写人民币金额，最多两位小数，如 680 或 CNY 680.00')
    try:
        return str(Decimal(text).quantize(Decimal('0.01')))
    except InvalidOperation:
        raise ValueError('票价金额过长，请检查输入') from None


def cny_price(raw):
    if not str(raw if raw is not None else '').strip():return 'CNY —'
    try:return 'CNY '+amount_text(raw)
    except ValueError:return str(raw).strip()  # Preserve legacy notes/currencies verbatim.

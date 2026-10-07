"""Strict source normalization; language/locale is explicit and blanks remain unknown."""
import unicodedata
from datetime import datetime, date, timedelta
from decimal import Decimal, InvalidOperation
from lotus_farm.rules import RuleError, canonical_hash


def source_text(value):
    if value is None:
        return None
    return ' '.join(unicodedata.normalize('NFC',str(value)).strip().split())


def source_number(value, decimal_separator=',', group_separator='.', percent=False):
    if value is None or source_text(value) in ('','-'):
        return None
    if decimal_separator==group_separator or decimal_separator not in ('.',','):
        raise RuleError('Declare separate decimal and grouping separators.')
    text=source_text(value)
    marked=text.endswith('%')
    if marked:
        if not percent:
            raise RuleError('Percentage is not allowed in a quantity column.')
        text=text[:-1].strip()
    if isinstance(value,(int,float,Decimal)) and not isinstance(value,bool):
        text=str(value)
    else:
        # Reject irregular grouping rather than silently changing the magnitude.
        parts=text.split(decimal_separator)
        if len(parts)>2:
            raise RuleError('Invalid decimal number.')
        whole=parts[0].lstrip('+-')
        if group_separator and group_separator in whole:
            groups=whole.split(group_separator)
            if not 1<=len(groups[0])<=3 or any(len(g)!=3 for g in groups[1:]):
                raise RuleError('Invalid thousands grouping.')
        text=text.replace(group_separator,'').replace(decimal_separator,'.')
    try:result=Decimal(text)
    except (ValueError,InvalidOperation):raise RuleError('Source number is invalid.') from None
    if not result.is_finite():
        raise RuleError('Source number must be finite.')
    return float(result/100 if marked else result)


def source_date(value):
    if value is None or source_text(value) in ('','-'):
        return None
    if isinstance(value,datetime):return value.date().isoformat()
    if isinstance(value,date):return value.isoformat()
    if isinstance(value,(int,float)):
        if value<1 or int(value)==60:
            raise RuleError('Invalid Excel date serial.')
        # Excel 1900 leap-year bug: serials before March use a different offset.
        epoch=date(1899,12,31) if value<60 else date(1899,12,30)
        try:return (epoch+timedelta(days=int(value))).isoformat()
        except (OverflowError,ValueError):raise RuleError('Excel date is out of range.') from None
    for pattern in ('%d/%m/%Y','%d.%m.%Y','%Y-%m-%d'):
        try:return datetime.strptime(source_text(value),pattern).date().isoformat()
        except ValueError:pass
    raise RuleError('Source date format is unsupported; filename dates do not replace sheet dates.')


def staged_row(source_key,sheet,row_number,raw,legacy_org_key):
    if not source_key or not sheet or not legacy_org_key or int(row_number)<1:
        raise RuleError('Source key, sheet, row and explicit legacy organization key are required.')
    import json
    return dict(row_key=canonical_hash([source_key,sheet,int(row_number)]),source_sheet=sheet,
                source_row=int(row_number),source_hash=canonical_hash(raw),
                raw_json=json.dumps(raw,ensure_ascii=False,default=str,sort_keys=True),
                legacy_org_key=legacy_org_key,row_status='Pending')

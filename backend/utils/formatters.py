from typing import Union, Any
from datetime import datetime, date
import pandas as pd

def format_financial_value(value: Union[int, float, str, None], include_sign: bool = False) -> str:
    if value is None:
        return "0"
    
    try:
        num = float(value)
    except (ValueError, TypeError):
        return str(value)

    abs_num = abs(num)
    sign = "-" if num < 0 else ""
    
    if abs_num >= 1_000_000_000:
        formatted = f"{abs_num / 1_000_000_000:.2f}".rstrip('0').rstrip('.') + "B"
    elif abs_num >= 1_000_000:
        formatted = f"{abs_num / 1_000_000:.2f}".rstrip('0').rstrip('.') + "M"
    elif abs_num >= 1_000:
        formatted = f"{abs_num / 1_000:.2f}".rstrip('0').rstrip('.') + "K"
    else:
        formatted = f"{abs_num:.2f}".rstrip('0').rstrip('.')

    result = f"{sign}{formatted}"
    
    if include_sign:
        return f"${result}"
        
    return result

from datetime import datetime, date
import pandas as pd

def format_date(date_val: Any) -> str: # 'YYYY-MM-DD'

    if date_val is None or str(date_val).lower() in ['none', 'nan', 'null', '']:
        return ""

    if isinstance(date_val, (datetime, date)):
        return date_val.strftime('%Y-%m-%d')

    if hasattr(date_val, 'strftime'):
        return date_val.strftime('%Y-%m-%d')

    date_str = str(date_val).strip()
    
    formats = [
        '%Y-%m-%d',          # 2024-01-30
        '%Y-%m-%d %H:%M:%S', # 2024-01-30 14:30:00
        '%d/%m/%Y',          # 30/01/2024
        '%m/%d/%Y',          # 01/30/2024
        '%Y/%m/%d',          # 2024/01/30
        '%b %d, %Y',         # Jan 30, 2024
        '%d-%m-%Y'           # 30-01-2024
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).strftime('%Y-%m-%d')
        except ValueError:
            continue

    try:
        return pd.to_datetime(date_str).strftime('%Y-%m-%d')
    except:
        return date_str
from config import SYMBOLS

def resolve_symbol(text: str):
    q = (text or '').lower().replace('check', '').replace('scan', '').strip()
    q = q.replace(' ', '')
    if q in SYMBOLS:
        return q.upper(), SYMBOLS[q]
    for name, ticker in SYMBOLS.items():
        if name in q:
            return name.upper(), ticker
    return None, None

def list_symbols():
    return sorted(set(SYMBOLS.keys()))

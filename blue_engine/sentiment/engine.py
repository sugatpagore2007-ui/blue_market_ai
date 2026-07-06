from __future__ import annotations
import requests


def fear_greed_crypto() -> dict:
    try:
        r = requests.get('https://api.alternative.me/fng/?limit=1', timeout=6)
        data = r.json()['data'][0]
        return {'source':'alternative.me', 'value': int(data['value']), 'label': data['value_classification']}
    except Exception:
        return {'source':'fallback', 'value': None, 'label': 'unavailable'}


def sentiment_for_symbol(ticker: str) -> dict:
    if ticker in {'BTC-USD','ETH-USD'}:
        fg = fear_greed_crypto()
        if fg['value'] is None:
            return {'sentiment':'neutral', 'note':'Crypto sentiment API unavailable.'}
        if fg['value'] >= 75:
            return {'sentiment':'greed', 'note':f'Crypto Fear & Greed is {fg["value"]} ({fg["label"]}). Avoid chasing late buys.'}
        if fg['value'] <= 25:
            return {'sentiment':'fear', 'note':f'Crypto Fear & Greed is {fg["value"]} ({fg["label"]}). Watch for panic reversals.'}
        return {'sentiment':'neutral', 'note':f'Crypto Fear & Greed is {fg["value"]} ({fg["label"]}).'}
    return {'sentiment':'neutral', 'note':'No live sentiment source configured for this symbol yet.'}

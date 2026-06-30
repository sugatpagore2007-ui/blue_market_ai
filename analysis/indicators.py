import numpy as np
import pandas as pd

def ema(series, length):
    return series.ewm(span=length, adjust=False).mean()

def atr(df, length=14):
    h, l, c = df['high'], df['low'], df['close']
    tr = pd.concat([(h-l), (h-c.shift()).abs(), (l-c.shift()).abs()], axis=1).max(axis=1)
    return tr.rolling(length).mean()

def rsi(series, length=14):
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(length).mean()
    loss = (-delta.clip(upper=0)).rolling(length).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def add_indicators(df):
    df = df.copy()
    df['ema_20'] = ema(df['close'], 20)
    df['ema_50'] = ema(df['close'], 50)
    df['ema_200'] = ema(df['close'], 200)
    df['atr_14'] = atr(df, 14)
    df['rsi_14'] = rsi(df['close'], 14)
    return df

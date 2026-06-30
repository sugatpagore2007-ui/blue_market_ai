# Phase 13 — Candlestick Pattern Intelligence

This upgrade adds a rule-based candlestick-pattern brain to Blue Forex Market AI.

Blue now checks candle body, wick size, gap behavior, rejection, continuation, and reversal structures. Candlestick patterns are used as **confirmation/warning only**. They do not force live trades by themselves.

## New Commands

```txt
phase13 status
candle help
candlestick patterns
candles gold
candles eurusd 15m
candles xauusd 5m
```

## How Blue Uses Candlesticks

Blue detects the current/recent candlestick pattern on the entry timeframe, then adds it to the final signal report.

It can:

- confirm a BUY signal when bullish candles support it
- confirm a SELL signal when bearish candles support it
- reduce confidence when candles conflict with the trade direction
- change a weak conflicting setup to WAIT
- warn when there are too many indecision candles

It cannot:

- guarantee profit
- force live trades
- replace risk management, news filters, SMC, ML, or broker checks

## Pattern Families Added

### Single-Candle Patterns

- Doji
- Long-Legged Doji
- Dragonfly Doji
- Gravestone Doji
- Spinning Top
- High Wave
- Bullish Marubozu
- Bearish Marubozu
- Hammer
- Hanging Man
- Inverted Hammer
- Shooting Star
- Bullish Pin Bar
- Bearish Pin Bar
- Bullish Belt Hold
- Bearish Belt Hold

### Two-Candle Patterns

- Bullish Engulfing
- Bearish Engulfing
- Piercing Line
- Dark Cloud Cover
- Bullish Harami
- Bearish Harami
- Bullish Harami Cross
- Bearish Harami Cross
- Tweezer Bottom
- Tweezer Top
- Bullish Kicker
- Bearish Kicker
- Matching Low
- Meeting Lines
- On-Neck
- In-Neck
- Thrusting Line
- Bullish Separating Lines
- Bearish Separating Lines

### Three+ Candle Patterns

- Morning Star
- Evening Star
- Morning Doji Star
- Evening Doji Star
- Three White Soldiers
- Three Black Crows
- Three Inside Up
- Three Inside Down
- Three Outside Up
- Three Outside Down
- Abandoned Baby Bullish
- Abandoned Baby Bearish
- Rising Three Methods
- Falling Three Methods
- Upside Tasuki Gap
- Downside Tasuki Gap
- Ladder Bottom
- Advance Block
- Deliberation
- Mat Hold Bullish
- Mat Hold Bearish

## Example Output

```txt
Candlestick pattern brain:
Bias bullish | Bullish 8.0 | Bearish 2.0 | Decision CONFIRMS_BUY
Candlestick bias supports the BUY idea.
- Bullish Engulfing (bullish) strength 5
- Tweezer Bottom (bullish) strength 3
```

## Important Trading Note

Candlestick patterns work best when combined with:

- higher-timeframe trend
- liquidity sweep / SMC structure
- news filter
- spread check
- risk-to-reward check
- dataset ML probability
- trade memory / journal learning

A candle pattern alone is not enough for safe autopilot trading.

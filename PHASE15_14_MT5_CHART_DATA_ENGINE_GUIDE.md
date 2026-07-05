# Phase 15.14 — MT5 Chart Data Engine

Blue can now analyze candles from the connected MT5 broker terminal instead of depending only on Yahoo/yfinance chart data.

## Why this upgrade matters

Before Phase 15.14, Blue mostly analyzed Yahoo/yfinance candles and then executed through MT5. That can create mismatch:

```text
Yahoo chart says BUY
MT5 broker price/candle is slightly different
Order execution may not match the chart analysis
```

Now Blue can use this better flow:

```text
MT5 broker candles
↓
Blue analysis / ML / SMC / candlestick logic
↓
MT5 broker symbol specs
↓
MT5 demo order execution
```

## Data-source modes

```text
auto   = MT5 broker candles first, Yahoo fallback if MT5 is unavailable
mt5    = MT5 broker candles only
yahoo  = old Yahoo/yfinance candles only
```

Default mode is:

```text
auto
```

## New commands

```text
data source
use mt5 data
use yahoo data
use auto data
mt5 candles gold
compare data gold
```

Examples:

```text
connect mt5
data source
use mt5 data
mt5 candles gold
gold
best
autopilot on
```

## Recommended setup for autopilot

Use this before autopilot:

```text
connect mt5
use mt5 data
mt5 candles gold
autopilot on
```

This makes Blue use the same broker candles for analysis and execution.

## Fallback behavior

If mode is `auto` and MT5 candles fail, Blue falls back to Yahoo/yfinance. If mode is `mt5`, Blue will not use Yahoo fallback and will show an error so you know MT5 is not ready.

## Notes

- MT5 terminal must be open and logged in.
- Market Watch symbols must be visible/selectable.
- Use `show mt5 symbols xau`, `show mt5 symbols eur`, or `show mt5 symbols btc` if a symbol is not found.
- TradingView direct candle API is not included. TradingView can still be used by screenshot/OCR or webhook-style alerts later.

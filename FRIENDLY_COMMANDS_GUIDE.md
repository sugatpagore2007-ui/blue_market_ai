# Blue Friendly Commands Guide

This version keeps all old commands, but adds short human-language commands.

## Most useful short commands

| Type this | Meaning |
|---|---|
| `help` | Show friendly command menu |
| `gold` | Analyze Gold / XAUUSD |
| `eurusd` | Analyze EURUSD |
| `btc` | Analyze Bitcoin |
| `best` | Find strongest setup |
| `scan` | Scan market |
| `train` | Train ready ML dataset |
| `learn` | Run background learning now |
| `learning` | Show learning report |
| `model` | Show dataset ML report |
| `retrain` | Retrain model now |
| `learn 30d` | Learn MT5 history for 30 days |
| `connect` | Connect selected broker |
| `broker` | Broker status |
| `safe` | Auto execution safety status |
| `conservative` | Set conservative trader mode |
| `normal` | Set balanced trader mode |
| `fast` | Set aggressive trader mode |
| `practice` | Set learning/demo trader mode |
| `go` | Start autopilot |
| `stop` | Stop autopilot |
| `manage` | Run trade manager |
| `candles gold` | Candlestick read for Gold |
| `patterns` | Candlestick pattern catalog |
| `voice` | Start voice mode |
| `bye` | Exit Blue |

## Examples

```text
gold
best
train
learn 90d
candles gold 15m
connect
conservative
go
stop
```

## Notes

- Old commands like `ml train dataset datasets/file.csv` still work.
- Short `train` uses `datasets/blue_ml_ready_combined_1050_rows.csv`.
- Short `learn` runs a background learning check immediately.
- Blue still does not place live trades unless live execution settings are intentionally enabled.


## Phase 15.14 chart data commands

| Command | Meaning |
|---|---|
| `data source` | Show whether Blue is using MT5, Yahoo, or auto data mode |
| `use mt5 data` | Use connected MT5 broker candles for analysis |
| `use yahoo data` | Use old Yahoo/yfinance chart candles |
| `use auto data` | Use MT5 first, Yahoo fallback |
| `mt5 candles gold` | Test if Blue can read MT5 candles for any pair |
| `compare data gold` | Compare latest MT5 close vs Yahoo close |


## Phase 15.15 Order Execution Doctor

Commands:

```text
order doctor
execution doctor
why no order
order doctor gold
execution doctor eurusd
order check btc
```

This is read-only. It diagnoses why MT5/autopilot may not punch an order and never places trades by itself.

## Phase 15.16 Internet / Environment Learning Commands

```text
internet help       -> show internet learning help
internet seed       -> add default trusted sources
internet sources    -> show trusted public learning sources
internet add <url>  -> add a page/RSS source
internet learn      -> learn market context from trusted internet/RSS sources
environment learn   -> same as internet learn
internet report     -> show internet/environment memory
baby brain          -> explain how Blue learns like a human
internet on         -> enable internet learning + background internet mode
internet off        -> disable internet learning
```

Safety: internet memory is context only. It cannot place orders, modify trades, or bypass autopilot/MT5 guardrails.

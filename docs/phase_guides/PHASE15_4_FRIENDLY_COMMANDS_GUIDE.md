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

# Phase 15.4 — Friendly Human Commands

Blue now accepts short and natural commands. You do not need to remember long technical commands.

## Basic

| Command | Meaning |
|---|---|
| `help` | Show simple commands |
| `start` | Confirm Blue is running |
| `status` | Show system status |
| `stop` | Stop autopilot, background learning loop, and voice speaking |
| `exit` | Close Blue |

## Market analysis

| Command | Meaning |
|---|---|
| `gold` | Analyze XAUUSD / gold |
| `btc` | Analyze BTCUSD |
| `eur` | Analyze EURUSD |
| `gbp` | Analyze GBPUSD |
| `jpy` | Analyze USDJPY |
| `check gold` | Analyze gold in human language |
| `gold buy or sell` | Ask Blue for direction |
| `best` | Show strongest setup |
| `scan` | Scan market |
| `why` | Explain the last signal |
| `reason gold` | Show trade basis for the symbol |
| `news` | Show news/macro reminder |
| `macro` | Show macro context reminder |

## ML learning

| Command | Meaning |
|---|---|
| `learn` | Run learning now |
| `learn on` | Start background auto-learning |
| `learn off` | Stop background auto-learning |
| `learn status` | Show background learning status |
| `train` | Train the ready ML dataset |
| `train brain` | Train Blue using the ready dataset |
| `brain` | Show dataset ML status |
| `ml report` | Show dataset ML report |
| `memory` | Show trade memory report |
| `history learn` | Learn from Blue journal/demo trades |
| `mt5 learn` | Learn from MT5 closed history for last 30 days |
| `backtest learn` | Learn all CSV files from `reports/` and `reports/auto_learn/` |

## Broker and account

| Command | Meaning |
|---|---|
| `broker` | Show broker status |
| `connect` | Connect selected broker adapter |
| `connect mt5` | Connect MT5 |
| `use exness` | Switch broker profile to Exness |
| `use xm` | Switch broker profile to XM |
| `use auto broker` | Auto-detect broker profile |
| `account` | Show MT5 account info |
| `balance` | Show MT5 balance/equity |
| `risk` | Save account balance and risk percent |
| `lot gold` | Calculate broker lot size |
| `symbols gold` | Show matching MT5 symbols |
| `spec gold` | Show symbol specification |

## Trade management

These commands are generic. Replace `gold` with `eur`, `gbp`, `jpy`, `btc`, `eth`, `silver`, `oil`, `nasdaq`, or your broker symbol.

| Command | Meaning |
|---|---|
| `trades` | Show open MT5 positions |
| `profit` | Show open MT5 positions / P&L |
| `stats` | Show trading statistics |
| `journal` | Show Blue journal |
| `breakeven gold` | Move SL to entry if the gold trade is profitable |
| `be gold` | Short form of breakeven |
| `trail gold` | One-time safe trailing update if trade is +1R or better |
| `close gold` | Close open gold positions |
| `close half gold` | Partial close 50% of gold positions |
| `manager on` | Run auto manager once |
| `manager off` | Stop/avoid manager loop |
| `manager` | Show manager status |

## Natural phrases Blue understands

- `tell me gold buy or sell`
- `show me best trade`
- `why should we take this trade`
- `learn from history`
- `train your brain`
- `connect my broker`
- `use xm broker`
- `move gold to breakeven`
- `show my open trades`
- `stop everything`

## Old commands still work

All long commands still work, for example:

```text
ml train dataset datasets/blue_ml_ready_combined_1050_rows.csv
mt5 learn history 30d
background learn status
symbol spec gold
show mt5 symbols xau
```


## Phase 15.14 chart data commands

| Command | Meaning |
|---|---|
| `data source` | Show whether Blue is using MT5, Yahoo, or auto data mode |
| `use mt5 data` | Use connected MT5 broker candles for analysis |
| `use yahoo data` | Use old Yahoo/yfinance chart candles |
| `use auto data` | Use MT5 first, Yahoo fallback |
| `mt5 candles gold` | Test if Blue can read MT5 candles for any pair |
| `compare data gold` | Compare latest MT5 close vs Yahoo close |

# Blue Forex Market AI — Commands and Meanings

## Basic
| Command | Meaning |
|---|---|
| `help` | Show simple command menu |
| `start` | Confirm Blue is running |
| `status` | Show full system status |
| `stop` | Stop autopilot/background actions/speaking |
| `exit` | Close Blue |

## Market Analysis
| Command | Meaning |
|---|---|
| `gold` | Analyze Gold / XAUUSD |
| `btc` | Analyze BTCUSD |
| `eur` | Analyze EURUSD |
| `gbp` | Analyze GBPUSD |
| `jpy` | Analyze USDJPY |
| `best` | Show strongest setup |
| `scan` | Scan all supported forex/CFD pairs |
| `why` | Explain the last signal |
| `news` | Show news/macro risk reminder |
| `macro` | Show macro context reminder |
| `candles gold` | Candlestick analysis for any pair |

## Learning and ML
| Command | Meaning |
|---|---|
| `learn` | Run learning now |
| `learn on` | Turn background auto-learning on |
| `learn off` | Turn background auto-learning off |
| `learn status` | Show background learning status |
| `train` | Train ready ML dataset |
| `train brain` | Train Blue using ready ML data |
| `brain` / `ml report` | Show ML brain report |
| `memory` | Show trade memory report |
| `history learn` | Learn from Blue journal/demo trades |
| `mt5 learn` | Learn from MT5 closed history |
| `backtest learn` | Learn from backtest CSV files |

## Broker, Account, Risk
| Command | Meaning |
|---|---|
| `broker` | Show broker status |
| `connect` / `connect mt5` | Connect selected broker / MT5 |
| `use exness` | Switch broker profile to Exness |
| `use xm` | Switch broker profile to XM |
| `use auto broker` | Auto-detect broker profile |
| `account` | Show MT5 account info |
| `balance` | Show balance/equity |
| `risk` | Save balance and risk percent |
| `lot gold` | Calculate lot size for any symbol |

## Trading / Management
| Command | Meaning |
|---|---|
| `trades` | Show open MT5 positions |
| `profit` | Show current profit/loss |
| `win rate` | Connected-account win-rate report |
| `journal` | Show Blue journal |
| `breakeven gold` / `be gold` | Move SL to entry if profitable |
| `trail gold` | Trail stop for a symbol |
| `close gold` | Close symbol position |
| `close half gold` | Partial close 50% |
| `manager` | Show auto manager status |
| `manager on` | Run auto manager once |
| `manager off` | Stop manager loop |

## Autopilot / Voice
| Command | Meaning |
|---|---|
| `autopilot` | Show autopilot status |
| `autopilot on` | Start demo autopilot |
| `autopilot off` | Stop autopilot |
| `voice` | Start background voice listener manually |
| `voice off` | Stop background voice listener |
| `voice status` | Show mic/TTS package status |
| `quiet` | Stop current voice reply |

## Natural Language Examples
```text
check gold
tell me gold buy or sell
show me best trade
why should we take this trade
show my win rate
take out win rate of btc
learn from history
train your brain
connect my broker
use xm broker
move gold to breakeven
show my open trades
stop everything
```

Replace `gold` with `eur`, `gbp`, `jpy`, `btc`, `eth`, `silver`, `oil`, `nasdaq`, or another supported broker symbol.


## Phase 15.14 — Chart data source commands

| Command | Meaning |
|---|---|
| `data source` | Show chart data mode and MT5 connection status |
| `use mt5 data` | Analyze MT5 broker candles only |
| `use yahoo data` | Analyze Yahoo/yfinance candles only |
| `use auto data` | Use MT5 first, Yahoo fallback |
| `mt5 candles gold` | Test latest broker candles for a symbol |
| `compare data gold` | Compare broker candle close vs Yahoo close |

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

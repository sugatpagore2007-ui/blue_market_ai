# Phase 15.8 — Compact Win Rate + Manual Voice Activation

## What changed

Phase 15.8 updates two behaviors requested by Sp:

1. **Win-rate commands now show only the connected-account win-rate report.**
   Blue no longer appends journal, ML dataset, recent trades, directions, help text, or extra sections when you ask for win rate.

2. **Voice listener no longer starts automatically on app launch.**
   When Blue starts, voice stays OFF. Type `voice` whenever you want Blue to begin listening in the background while terminal text commands keep working.

## Win-rate commands

```text
win rate
connected account win rate
account win rate
show my win rate
stats
performance
gold win rate
btc win rate
eur win rate
gbp win rate
jpy win rate
take out win rate of btc
win rate 30d
win rate gold 180d
```

## Output format

Blue prints this clean format only:

```text
WIN RATE INTELLIGENCE REPORT
========================================================================
Source priority: connected MT5 account first.
History window : last 90 days
Account      : <login> | <server>
Balance/Equity: <balance> / <equity> <currency>
Margin Free  : <free margin> | Leverage 1:<leverage>

CONNECTED ACCOUNT / MT5 HISTORY
Closed trades : <total> | Win rate: <win rate>%
Wins/Loss/BE  : <wins> / <losses> / <breakeven>
Net profit    : <net> | Gross win <gross win> | Gross loss <gross loss>
Profit factor : <pf> | Avg trade <avg> | Avg win/loss <avg win> / <avg loss>

Win rate by symbol
  XAUUSDm            71.43% | 5W/2L/0BE | net 506.58 | PF 30.27
```

## Voice commands

Voice is manual now.

```text
voice
voice off
voice status
voice background status
```

After typing `voice`, Blue listens in the background, and you can still type commands in the terminal.

Example voice commands:

```text
hey blue show my win rate
hey blue take out win rate of btc
hey blue gold win rate
```

## Important

MT5 must be open and logged in for connected-account win-rate data. If MT5 is not connected, Blue will show a compact MT5 unavailable reason instead of falling back to other sections.

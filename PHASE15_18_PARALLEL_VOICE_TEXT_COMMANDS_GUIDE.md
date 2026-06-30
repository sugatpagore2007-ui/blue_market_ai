# Phase 15.18 — Parallel Voice + Text Commands

This upgrade keeps the existing command names stable and adds a safer voice/text runtime.

## Main idea

When Blue is listening by voice, the terminal still accepts typed commands at the same time.

- Voice listener runs in a background thread.
- Text command prompt stays active: `Blue >`.
- Command execution is locked/serialized so voice and text cannot fight over MT5/order management.
- Prompt-only commands are protected in voice mode so background voice never calls `input()` and freezes the terminal.

## Start Blue

```bash
python main.py
```

If mic packages are installed, Blue tries to start the background listener automatically. If voice packages are missing, text commands still work normally.

You can also start voice manually:

```text
voice
talk
voice text on
dual mode
parallel mode
```

Stop only voice listener:

```text
voice off
voice text off
```

Check listener status:

```text
voice background status
voice text status
```

## Commands kept unchanged

```text
help
start
status
stop
exit

gold
btc
eur
gbp
jpy
check gold
gold buy or sell
best
scan
why
news
macro

learn
learn on
learn off
learn status
train
train brain
brain
ml report
memory
history learn
mt5 learn
backtest

broker
connect
connect mt5
use exness
use xm
use auto broker
account
balance
risk
lot gold

trades
profit
stats
journal
breakeven gold
be gold
trail gold
close gold
close half gold

manager on
manager off
manager
autopilot
autopilot on
autopilot off
scan auto

voice
talk
quiet
screenshot
ocr
```

## Natural phrases added for voice + text

```text
show simple commands
tell me gold buy or sell
show me best trade
show my best trade
why should we take this trade
learn from history
train your brain
connect my broker
use xm broker
move gold to breakeven
show my open trades
take out win rate of btc
stop everything
```

## New Phase 15.18 commands

```text
voice text on
voice text off
voice text status
dual mode
parallel mode
both mode
```

These are additions only. The older commands are not removed.

## Safety behavior

Voice mode will not run commands that normally need terminal input, because that can freeze the background listener.

Examples that should be typed in terminal:

```text
risk
lot gold
screenshot
```

Voice will still respond and tell you to type those commands when they need balance/risk/path details.

Manual buy/sell execution from voice is blocked for safety. Use voice for analysis like:

```text
gold buy or sell
```

Use terminal for exact manual execution commands if you deliberately want manual order operations.

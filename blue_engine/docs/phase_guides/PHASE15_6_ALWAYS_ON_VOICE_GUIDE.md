# Phase 15.6 — Always-On Voice + Text Commands

Phase 15.6 upgrades Blue so voice and text can work together.

## What changed

- Blue starts the background voice listener automatically when `python main.py` runs.
- The terminal still accepts typed commands at `Blue >` while voice listens in the background.
- Voice commands are routed through the same Friendly Command Brain as typed commands.
- Wake words work like a simple assistant: `hey blue`, `ok blue`, `blue`, plus optional `hey siri`, `alexa`, `hey google` style phrases.
- Direct commands still work if clearly recognized, like `check gold`, `best`, `train your brain`, `show my open trades`.
- Background voice never uses typed fallback, so it cannot steal the terminal input prompt.

## Startup behavior

Run:

```bash
python main.py
```

Blue starts:

1. Background auto-learning
2. Background voice listener
3. Normal text terminal prompt

You can type and speak at the same time.

## Voice commands

Examples:

```text
hey blue check gold
blue tell me gold buy or sell
hey blue show me best trade
hey blue why should we take this trade
hey blue train your brain
hey blue learn from history
hey blue connect my broker
hey blue use xm broker
hey blue move gold to breakeven
hey blue show my open trades
hey blue stop everything
```

Direct commands also work:

```text
check gold
best
train your brain
learn from history
show my open trades
stop everything
```

## Text commands

All friendly commands work as typed commands too:

```text
help
status
gold
btc
eur
gbp
jpy
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
backtest learn
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
voice off
voice background status
voice status
talk
quiet
screenshot
ocr
exit
```

## New voice commands

```text
voice                 -> start/resume background listener
voice off             -> stop background listener
voice background status -> show listener status and last heard command
voice status          -> show installed mic/TTS packages
voice session         -> old blocking voice mode
quiet                 -> stop current speech
```

## Safety note

When a command comes from background voice, Blue avoids terminal `input()` prompts. For risk-sensitive commands like saving account/risk, type the command in the terminal so you can enter the numbers clearly.

If no saved risk settings exist, voice analysis will still show the signal/reason, but lot size may say to type `risk` first.

## Troubleshooting

Check voice packages:

```text
voice status
```

Install voice packages:

```bash
python -m pip install -r requirements_voice.txt
```

Recommended for Python 3.14:

```bash
python -m pip install SpeechRecognition pyttsx3 sounddevice numpy
```

PyAudio is optional now. Blue can use sounddevice fallback.

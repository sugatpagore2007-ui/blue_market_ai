# Phase 15.5 — Voice Control Hotfix

This build fixes the common voice error:

```text
Could not find PyAudio; check installation
```

## What changed

Blue now tries voice input in this order:

1. SpeechRecognition + PyAudio microphone
2. sounddevice + numpy microphone fallback
3. typed command fallback

This means Blue can still use microphone input even when PyAudio is not available for your Python version.

## Install voice packages

Recommended for Python 3.14:

```bash
python -m pip install -r requirements_voice.txt
```

or manually:

```bash
python -m pip install SpeechRecognition pyttsx3 sounddevice numpy
```

Then run:

```bash
python main.py
```

Inside Blue:

```text
voice status
voice
```

## Useful voice commands

```text
check gold
tell me gold buy or sell
show me best trade
why
train your brain
learn status
show my open trades
move gold to breakeven
stop speaking
stop voice
```

## If PyAudio is missing

That is okay in this build. Blue will try sounddevice fallback.

If you still want classic PyAudio, use Python 3.13 or 3.12 and install:

```bash
python -m pip install PyAudio SpeechRecognition pyttsx3
```

## New commands

```text
voice status
mic status
voice install help
install voice
```

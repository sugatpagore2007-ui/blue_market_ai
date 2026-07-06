# Phase 12 — Video / Strategy Knowledge Learning

This upgrade lets Blue learn from your own strategy notes or transcripts related to YouTube videos.

Important: a YouTube link alone is only a source. Blue cannot truly learn the full lesson unless you give it transcript text or your own notes. Blue stores extracted rules and lesson summaries, not full copied video content.

## What was added

- `knowledge/video_learning.py`
- `knowledge/video_sources.json`
- `knowledge/video_notes_template.md`
- `knowledge/sample_video_notes.md`
- SQLite tables for video sources and extracted lesson rules
- Signal engine integration through `video_knowledge_engine`
- Phase 12 commands in `main.py`

## Commands

```text
video learning help
video seed sources
video sources
video knowledge report
phase12 status
video add source <youtube_url>
video import transcript <youtube_url_or_id> <path/to/transcript.txt>
video import notes <path/to/notes.md>
video fetch transcript <youtube_url_or_id>
video fetch all transcripts
video learn from sources
```

## Recommended workflow

### Step 1 — Save the video links

```text
video seed sources
video sources
```

### Step 2 — Add your notes or transcript

Create a file like:

```text
knowledge/transcripts/video1_notes.txt
```

Write the useful strategy lessons in short lines. Example:

```text
Avoid trading near high-impact news when spread is unstable.
Wait for liquidity sweep plus displacement before entry.
Skip choppy range trades when risk reward is weak.
```

### Step 3 — Import it into Blue

```text
video import transcript jwjjWHzEaJc knowledge/transcripts/video1_notes.txt
```

Or for general notes:

```text
video import notes knowledge/sample_video_notes.md
```

### Step 4 — Check report

```text
video knowledge report
```

### Step 5 — Use normal analysis

```text
analyze gold
analyze eurusd
strongest
```

Blue will now show a `Video / strategy knowledge engine` section when it analyzes a trade.

## What Blue learns

Blue extracts lessons into categories:

- market context
- entry trigger
- no trade filters
- risk management
- psychology / discipline

## Safety behavior

The video knowledge engine is advisory only:

- It never forces a BUY or SELL.
- It can add caution.
- It can slightly adjust confidence.
- It can switch a weak trade to WAIT when a learned no-trade rule matches.
- It still uses the normal risk engine and demo-first execution guards.

## Optional public captions

If captions are available and you install the optional package:

```bash
pip install youtube-transcript-api
```

Then you can try:

```text
video fetch transcript <youtube_url_or_id>
video fetch all transcripts
video learn from sources
```

This may fail if the video has no public captions, the language is unavailable, or the caption API is blocked.


## Your 11-video source set

The links you sent are already stored in `knowledge/video_sources.json`. Run:

```text
video seed sources
video sources
```

To attempt public captions for all saved videos, install the optional caption tool and run:

```bash
pip install youtube-transcript-api
```

Then inside Blue:

```text
video fetch all transcripts
```

If a video has no public captions or the caption API fails, paste your own notes into `knowledge/transcripts/<video_id>.txt` and import them:

```text
video import transcript <video_id> knowledge/transcripts/<video_id>.txt
```

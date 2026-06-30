# Phase 14 — Candlestick + Booming Bulls Knowledge ML

This upgrade adds two things:

1. Candlestick patterns as ML features
2. A safe Booming Bulls channel learning system

## Important

Blue does not ship copied YouTube transcripts, videos, or paid-course content. It stores the channel/source links and can learn from:

- your own notes
- public captions where available
- concise strategy lessons extracted from those notes/captions

Educational video lessons are used as a **knowledge filter**, not as a supervised win/loss model. For true predictive ML, Blue still needs your backtested/demo trade dataset with actual results.

## New Booming Bulls Commands

```txt
booming bulls help
booming bulls seed
booming bulls fetch videos 50
booming bulls fetch transcripts 25
booming bulls import notes knowledge/my_booming_bulls_notes.md
booming bulls export dataset
booming bulls report
```

## New Candlestick ML Dataset Columns

```txt
candlestick_bias
candlestick_pattern
candlestick_strength
source_knowledge
```

These columns are now included in:

```txt
datasets/blue_ml_dataset_template.csv
datasets/blue_ml_sample_dataset.csv
```

## Best Workflow

1. Watch a video.
2. Write your own notes in `knowledge/my_booming_bulls_notes.md`.
3. Run:

```txt
booming bulls import notes knowledge/my_booming_bulls_notes.md
booming bulls export dataset
video knowledge report
```

4. Add real trade outcomes separately in `datasets/my_blue_training_data.csv`.
5. Train supervised ML:

```txt
ml train dataset datasets/my_blue_training_data.csv
```

## Why not train directly on videos?

A trading video explains concepts, but ML needs labeled examples such as:

```txt
setup + context + candle pattern + result = win/loss
```

So Blue uses videos for strategy rules and uses your trade history/backtests for prediction.

# Phase 16 — Cognitive Architecture Auto Brain

This phase is additive. It does **not** replace the current Blue folders or old commands.

## What runs automatically

When `python main.py` starts, Blue now starts a background Cognitive Architecture worker.
It refreshes:

- World Model
- Market DNA memory
- Experience Replay notes
- Knowledge Verification queue
- Opportunity ranking hints
- Confidence calibration tasks

## Important safety

This layer never places, closes, or modifies orders.
It only improves memory, ranking, verified learning and explanation.
Order execution still goes through:

- Autopilot rules
- Gold reserved quota
- Risk filters
- Order Punch Shield
- Session guard
- Self-Healing Doctor

## Files added

- `brain/cognitive_architecture.py`
- `brain_memory/world_model.json`
- `brain_memory/market_dna.json`
- `brain_memory/experience_replay.json`
- `brain_memory/knowledge_verification_queue.json`
- `phase16_cognitive_architecture_state.json`

## Optional commands

You do not need these for normal use, but they are available:

- `cognitive status`
- `world model`
- `market dna`
- `cognitive now`
- `cognitive on`
- `cognitive off`

## How it helps productivity

Blue learns selectively instead of blindly learning everything.
It collects from existing sources, verifies ideas, stores memory, ranks opportunities, and avoids trusting noisy internet data without testing.

# Blue Weekly Evolution Report

Generated: 2026-06-29T16:14:23+00:00

## What Blue reviewed
- Autopilot state
- Gold/Other reserved quota state
- Profitability flywheel state
- Cognitive architecture state
- CME institutional context state
- Neural/self-healing state

## Current trading policy
- Autopilot scan interval: 5 minutes
- Daily auto trades: max 2
- Gold slot: 1 trade only, A+ or 100% confidence required
- Other-pair slot: 1 trade only
- If London gives no trade, New York can still use the same two slots only
- Order Punch Shield and self-healing remain active

## Snapshot
- Quota: `{'enabled': True, 'max_daily_trades': 2, 'london_limit': 1, 'ny_limit': 1, 'roll_london_unused_to_ny': True, 'london_utc_start': '07:00', 'london_utc_end': '16:00', 'ny_utc_start': '12:00', 'ny_utc_end': '21:00', 'days': {}}`
- Profitability flywheel: `{'enabled': True, 'background_enabled': True, 'min_samples_to_adjust': 5, 'max_confidence_boost': 5, 'max_confidence_cut': 12, 'last_calibration_utc': None, 'notes': []}`
- CME: `{'enabled': True, 'background': True, 'running': False, 'interval_seconds': 21600, 'last_run': '2026-06-28T05:30:59+00:00', 'last_message': 'CME context refreshed from local_csv with 9 symbol records.', 'last_error': None, 'updated_at': '2026-06-28T05:30:59+00:00'}`
- Cognitive: `{'enabled': True, 'running': True, 'started_at': None, 'last_run': '2026-06-27T07:04:26+00:00', 'loop_count': 1, 'last_message': 'Cognitive pulse completed: world model, market DNA, verification queue and replay refreshed.', 'last_error': None, 'updated_at': '2026-06-27T07:04:26+00:00'}`

## Evolution decisions
- Keep learning from all sources, but promote only verified knowledge.
- Prioritize MT5 history, Blue journal, CME context, and demo forward test over internet/video notes.
- Continue ranking Gold separately from other instruments because Gold has its own reserved slot.
- If repeated order rejections appear, run Order Doctor and Self-Healing Doctor automatically/visibly.

## Next focus
- Improve setup quality, not trade quantity.
- Track which sessions and instruments actually convert confidence into profit.
- Reduce confidence for setups that underperform in live/demo results.
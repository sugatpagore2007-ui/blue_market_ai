# Phase 15.3 Ready ML Data Hotfix

This build fixes the training error:

```text
['candlestick_strength', 'candlestick_pattern_count', 'talib_patterns_detected', 'candlestick_bias', 'candlestick_pattern', 'talib_available'] not in index
```

## What was fixed

- Dataset trainer now adds missing Phase 13/14 candlestick columns safely.
- Older imported rows in `blue_market_ai.db` no longer crash training.
- Ready-made dataset columns like `atr_pips`, `entry_price`, `take_profit_1`, and `take_profit_2` are mapped correctly.
- Candlestick fields are preserved while normalizing the CSV.

## Train command

```text
ml train dataset datasets/blue_ml_ready_combined_1050_rows.csv
ml dataset report
```

Expected result:

```text
Dataset ML trained from about 1049 rows with both wins and losses.
Model ready : True
```

The ready dataset is synthetic testing data. For real improvement, train later on demo/backtest/MT5 history rows.

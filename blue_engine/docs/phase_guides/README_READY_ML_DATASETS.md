# Blue Ready-Made ML Training Sets

These files are ready-made **synthetic** datasets for testing Blue's ML learning pipeline.
They are not real profitable market data and should not be used as proof of a trading edge.
Use them to test whether Blue can import, train, report, and use ML probability correctly.

## Files

- `blue_ml_ready_combined_1050_rows.csv` — best all-in-one file to train first.
- `blue_ml_starter_150_rows.csv` — small starter file.
- `blue_ml_candlestick_250_rows.csv` — candle pattern learning examples.
- `blue_ml_smc_ict_setups_250_rows.csv` — SMC/ICT-style setup examples.
- `blue_ml_backtest_style_250_rows.csv` — backtest-like trades.
- `blue_ml_mt5_history_style_150_rows.csv` — MT5-history-like trades.
- `blue_ml_blank_template.csv` — blank file for your real demo trades.
- `blue_ml_column_dictionary.csv` — meaning of each column.
- `blue_ready_ml_training_sets.xlsx` — Excel workbook version.

## How to give this data to Blue

1. Extract this ZIP.
2. Copy the CSV files into your Blue project folder:

```text
blue_forex_market_ai_phase15_2_background_auto_learning_final/datasets/
```

3. Run Blue:

```bash
python main.py
```

4. Train Blue with the combined file:

```text
ml train dataset datasets/blue_ml_ready_combined_1050_rows.csv
ml dataset report
```

Or train smaller parts:

```text
ml train dataset datasets/blue_ml_candlestick_250_rows.csv
ml train dataset datasets/blue_ml_smc_ict_setups_250_rows.csv
ml train dataset datasets/blue_ml_backtest_style_250_rows.csv
```

## Best use

Use this synthetic pack first to confirm the ML pipeline works.
For real learning, replace these rows with your own demo trades, backtest results, or MT5 closed history.
Include both wins and losses. A dataset with only wins will teach Blue bad patterns.

## Recommended real-data target

- Test only: 50–150 rows
- Useful model: 300–1,000 real trades
- Stronger model: 2,000+ clean labeled trades

## Safety

Keep live trading off while testing ML:

```env
LIVE_TRADING_ENABLED=false
DEMO_MODE=true
ML_CAN_BLOCK_TRADES=true
ML_CAN_PLACE_TRADES=false
```

# Phase 15.3 Ready ML Dataset Pack

This build includes ready-made ML training sets inside the `datasets/` folder so Blue can train immediately.

## Included training files

- `datasets/blue_ml_ready_combined_1050_rows.csv` — best first file to train on.
- `datasets/blue_ml_starter_150_rows.csv` — small starter test set.
- `datasets/blue_ml_candlestick_250_rows.csv` — candlestick-focused training data.
- `datasets/blue_ml_smc_ict_setups_250_rows.csv` — SMC/ICT-style setup examples.
- `datasets/blue_ml_backtest_style_250_rows.csv` — backtest-style examples.
- `datasets/blue_ml_mt5_history_style_150_rows.csv` — MT5-history-style examples.
- `datasets/blue_ml_blank_template.csv` — blank template for your own trades.
- `datasets/blue_ml_column_dictionary.csv` — column meanings.
- `datasets/blue_ml_allowed_categories.json` — allowed category values.
- `datasets/blue_ready_ml_training_sets.xlsx` — Excel workbook version.

## Train Blue on the ready dataset

Run Blue:

```bash
python main.py
```

Inside Blue, train the combined dataset:

```text
ml train dataset datasets/blue_ml_ready_combined_1050_rows.csv
ml dataset report
```

## Train special datasets

```text
ml train dataset datasets/blue_ml_candlestick_250_rows.csv
ml train dataset datasets/blue_ml_smc_ict_setups_250_rows.csv
ml train dataset datasets/blue_ml_backtest_style_250_rows.csv
ml train dataset datasets/blue_ml_mt5_history_style_150_rows.csv
```

## How machine learning uses this data

Blue reads each row as one past trade/setup example. It learns patterns between features and result.

Example features:

- symbol
- timeframe
- action
- setup_type
- session
- market_regime
- news_risk
- spread_pips
- atr_pips
- rr_ratio
- rule_confidence
- candlestick_pattern
- candlestick_bias
- dxy_bias
- result
- pnl_r

The target label is mainly `result` / `pnl_r`.

## Important safety note

These ready-made datasets are synthetic examples for learning/testing the ML pipeline. For serious use, later train Blue with your own demo trades, backtest trades, and MT5 closed history. Keep live trading off while testing.

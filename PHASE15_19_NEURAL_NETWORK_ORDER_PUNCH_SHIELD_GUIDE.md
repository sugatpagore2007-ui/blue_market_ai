# Phase 15.19 — Neural Network Brain + Order Punch Shield

This upgrade adds Blue's neural confirmation brain and stronger order execution diagnostics.

## Neural Network Brain

Best architecture supported:

- CNN layer: learns candle/setup shape patterns.
- BiLSTM layer: learns sequence-style market behavior.
- Attention layer: focuses on the most important parts of the setup.

If TensorFlow is installed, Blue trains:

```bash
pip install tensorflow
```

Model file:

```text
models/blue_cnn_bilstm_attention.keras
```

If TensorFlow is not installed, Blue still works and trains a fallback neural model using scikit-learn MLP:

```bash
pip install scikit-learn joblib
```

## Commands

Old commands are not changed.

New commands added:

```text
neural help
neural train
neural train dataset datasets/blue_ml_ready_combined_1050_rows.csv
neural report
neural predict gold
neural on
neural off
neural background on
neural background off
nn help
nn train
nn report
nn predict gold
deep learn
```

## How it affects trades

Neural brain is a confirmation brain only.

It can:

```text
confirm a good setup
blend confidence
block weak learned-history setups
show probability and model status
train in background when due
```

It cannot:

```text
punch orders by itself
bypass SMC/ICT logic
override risk filter
override demo-only MT5 protection
force autopilot trades
```

## Order Punch Shield

Added stronger order pre-check before sending orders:

```text
refresh live bid/ask before send
run mt5.order_check before order_send
try multiple filling modes
retry after price change/requote/off-price
fallback to market order without SL/TP then attach SL/TP if broker rejects initial stops
show exact retcode, last_error, and diagnostics
```

This removes common code-side order-punching mistakes. It still cannot control broker-side conditions like closed market, disabled Algo Trading, missing MT5 login, non-demo account block, spread too high, or broker rejection.

Best check command:

```text
order doctor gold
```

## Background behavior

When Blue runs, background learning also checks neural retraining when due.

```bash
python main.py
```

The terminal remains usable, voice remains usable, and autopilot can still scan in background.

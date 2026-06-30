# Phase 11 Dataset ML Guide

Blue can now learn from CSV datasets you provide.

## Fast start

```txt
ml dataset template
ml train dataset datasets/blue_ml_sample_dataset.csv
ml dataset report
check gold
```

## Your CSV must include a label

Blue needs to know the result of each example:

- `result=win` or `result=loss`
- OR `pnl_r=1.5` / `pnl_r=-1.0`

## Recommended columns

```csv
timestamp,symbol,timeframe,action,setup_type,trade_style,session,market_regime,trend_bias,news_risk,spread_pips,atr,rr_ratio,rule_confidence,tf_alignment,liquidity_sweep,fvg_present,order_block_present,smt_divergence,correlation_risk,entry,stop_loss,target_1,target_2,result,pnl_r,notes
```

## What Blue learns

Blue learns which combinations historically worked better:

- Symbol + session
- Setup type
- Trend/regime
- News risk
- Spread and volatility
- Risk/reward
- Liquidity sweep / FVG / order block presence
- Multi-timeframe alignment
- Original confidence score

## What Blue does with the model

For every new signal, Blue adds a user-dataset ML probability. It can lower confidence or block a trade if the dataset says similar setups performed badly.

It does **not** guarantee profit and does **not** force live entries.

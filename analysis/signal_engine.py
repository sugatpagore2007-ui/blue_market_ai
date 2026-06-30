from ai_desk.human_desk import upgrade_signal
from intelligence.phase9_intelligence import apply_phase9_intelligence
from intelligence.human_trader_brain import build_market_context, apply_human_trader_brain
from intelligence.human_trader_natural import apply_human_trader_natural
from news.macro_brain import build_macro_brain
from analysis.market_data import fetch_ohlcv
from analysis.indicators import add_indicators
from analysis.smc_ict import smc_snapshot, nearest_zone, killzone_now
from analysis.liquidity_heatmap import build_liquidity_heatmap
from analysis.smt import detect_smt
from news.forex_factory import news_filter
from learning.confidence_model import adjust_confidence
from learning.dataset_learning import apply_dataset_ml_learning
from learning.neural_network_brain import apply_neural_network_brain
from learning.profitability_flywheel import apply_profitability_flywheel
from brain.cognitive_architecture import apply_cognitive_architecture
from institutional.cme_group_brain import apply_cme_group_brain
from brain.autonomous_evolution import apply_autonomous_evolution
from knowledge.video_learning import apply_video_knowledge
from analysis.candlestick_patterns import detect_candlestick_patterns, apply_candlestick_brain
from risk.account import position_size, empty_risk
from trade_management.manager import build_management_plan
from sentiment.engine import sentiment_for_symbol
from coach.replay_coach import coach_feedback
from config import TIMEFRAMES, MIN_CONFIDENCE_FOR_ACTION, DEFAULT_ATR_MULTIPLIER, TRADE_STYLE_PROFILES, DEFAULT_TRADE_STYLE
from utils.trade_reasoning import attach_terminal_reason_card


def _technical_score(df):
    last = df.iloc[-1]
    score = 0
    why = []
    if last['close'] > last['ema_20'] > last['ema_50']:
        score += 2; why.append('EMA trend bullish')
    elif last['close'] < last['ema_20'] < last['ema_50']:
        score -= 2; why.append('EMA trend bearish')
    else:
        why.append('EMA trend mixed')
    if last['close'] > last['ema_200']:
        score += 1; why.append('above 200 EMA')
    elif last['close'] < last['ema_200']:
        score -= 1; why.append('below 200 EMA')
    rsi = last.get('rsi_14')
    if rsi == rsi:
        if 52 <= rsi <= 68:
            score += 1; why.append('RSI bullish momentum')
        elif 32 <= rsi <= 48:
            score -= 1; why.append('RSI bearish momentum')
        elif rsi > 75:
            score -= 1; why.append('RSI overbought caution')
        elif rsi < 25:
            score += 1; why.append('RSI oversold bounce risk')
    return score, why


def _tf_analysis(df):
    snap = smc_snapshot(df)
    tech_score, why = _technical_score(df)
    smc_score = snap['structure']['score'] + snap['liquidity']['score']
    pd_loc = snap['premium_discount']['price_location']
    if snap['structure']['direction'] == 'bullish' and pd_loc == 'discount':
        smc_score += 1; why.append('bullish bias inside discount')
    if snap['structure']['direction'] == 'bearish' and pd_loc == 'premium':
        smc_score -= 1; why.append('bearish bias inside premium')
    why.append(snap['structure']['event'])
    why.append(snap['liquidity']['type'])
    return {'score': tech_score + smc_score, 'why': why, 'smc': snap}


def _decide(tf_results, trade_style=DEFAULT_TRADE_STYLE):
    profile = TRADE_STYLE_PROFILES.get(trade_style, TRADE_STYLE_PROFILES[DEFAULT_TRADE_STYLE])
    weights = profile.get('decision_weights') or {'5m': 1, '15m': 1.5, '1h': 2, '4h': 2.5, '1d': 2}
    weighted = 0; total_w = 0
    for tf, data in tf_results.items():
        w = weights.get(tf, 1)
        weighted += data['score'] * w
        total_w += w
    avg = weighted / total_w if total_w else 0
    if avg >= 1.6:
        return 'BUY', avg
    if avg <= -1.6:
        return 'SELL', avg
    return 'WAIT', avg


def _trade_levels(df, action, smc, trade_style=DEFAULT_TRADE_STYLE):
    last = df.iloc[-1]
    entry = float(last['close'])
    atr = float(last.get('atr_14') or 0) or max(entry * 0.005, 0.0001)
    profile = TRADE_STYLE_PROFILES.get(trade_style, TRADE_STYLE_PROFILES[DEFAULT_TRADE_STYLE])
    atr_multiplier = profile.get('atr_multiplier', DEFAULT_ATR_MULTIPLIER)
    target_1_r = profile.get('target_1_r', 1.5)
    target_2_r = profile.get('target_2_r', 2.5)
    all_zones = smc['fvgs'] + smc['order_blocks']
    if action == 'BUY':
        zone = nearest_zone(all_zones, entry, 'bullish')
        base_sl = smc['structure']['last_swing_low']
        if zone:
            base_sl = min(base_sl, zone.low)
        stop = min(base_sl, entry - atr * atr_multiplier)
        risk = entry - stop
        t1 = entry + risk * target_1_r
        t2 = entry + risk * target_2_r
    elif action == 'SELL':
        zone = nearest_zone(all_zones, entry, 'bearish')
        base_sl = smc['structure']['last_swing_high']
        if zone:
            base_sl = max(base_sl, zone.high)
        stop = max(base_sl, entry + atr * atr_multiplier)
        risk = stop - entry
        t1 = entry - risk * target_1_r
        t2 = entry - risk * target_2_r
    else:
        stop = entry; t1 = entry; t2 = entry
    return round(entry, 6), round(stop, 6), round(t1, 6), round(t2, 6)


def _confidence(avg_score, tf_results, action, smt_score=0, news_penalty=0):
    base = 50 + min(abs(avg_score) * 13, 35)
    align = 0
    if action != 'WAIT':
        bullish = sum(1 for d in tf_results.values() if d['score'] > 0)
        bearish = sum(1 for d in tf_results.values() if d['score'] < 0)
        align = bullish if action == 'BUY' else bearish
        base += align * 3
    base += smt_score * 3
    base += news_penalty
    return int(max(0, min(95, base)))


def _zone_to_dict(z):
    return {'kind': z.kind, 'direction': z.direction, 'low': round(z.low, 6), 'high': round(z.high, 6), 'index': z.index, 'strength': z.strength}


def build_signal(name, ticker, account=None, trade_style=DEFAULT_TRADE_STYLE):
    trade_style = (trade_style or DEFAULT_TRADE_STYLE).lower().strip()
    if trade_style not in TRADE_STYLE_PROFILES:
        trade_style = DEFAULT_TRADE_STYLE
    style_profile = TRADE_STYLE_PROFILES[trade_style]
    raw = {}
    tf_results = {}
    data_sources = {}
    for tf, cfg in TIMEFRAMES.items():
        df = add_indicators(fetch_ohlcv(ticker, cfg['interval'], cfg['period']))
        raw[tf] = df
        data_sources[tf] = {
            'source': df.attrs.get('data_source', 'unknown'),
            'broker_symbol': df.attrs.get('broker_symbol', ''),
            'mt5_error': df.attrs.get('mt5_error', ''),
            'bars': len(df),
        }
        tf_results[tf] = _tf_analysis(df)

    action, avg = _decide(tf_results, trade_style=trade_style)
    base_action_before_filters = action

    # Pro upgrades: SMT divergence, liquidity heatmap and Forex Factory news filter
    main_tf_for_pro = '1h' if '1h' in raw else list(raw.keys())[0]
    smt = detect_smt(ticker, raw[main_tf_for_pro])
    news = news_filter(ticker)
    market_sentiment = sentiment_for_symbol(ticker)
    heatmap = build_liquidity_heatmap(raw['15m'] if '15m' in raw else raw[main_tf_for_pro])

    confidence = _confidence(avg, tf_results, action, smt_score=smt.get('score', 0), news_penalty=news.get('penalty', 0))
    confidence, learning_note = adjust_confidence(name, action, confidence)
    if confidence < MIN_CONFIDENCE_FOR_ACTION:
        action = 'WAIT'
    action_after_confidence_filter = action

    # Entry timeframe rule: default Intraday uses 5m execution after checking all timeframes.
    # Other styles activate only when the user says scalping, swing trading, or position trading.
    main_tf = style_profile.get('entry_tf', '5m')
    if main_tf not in raw:
        main_tf = '5m' if '5m' in raw else ('15m' if '15m' in raw else list(raw.keys())[0])
    main_smc = tf_results[main_tf]['smc']
    entry, stop, t1, t2 = _trade_levels(raw[main_tf], action, main_smc, trade_style=trade_style)
    if action != 'WAIT' and account:
        risk = position_size(account['balance'], account['risk_percent'], entry, stop, ticker=ticker)
    else:
        risk = empty_risk(
            account.get('balance', 0) if account else 0,
            account.get('risk_percent', 0) if account else 0
        )
    session, session_note = killzone_now()
    macro_brain = build_macro_brain(ticker, news=news, sentiment=market_sentiment)
    market_context = build_market_context(name, ticker, raw, tf_results, session, news, market_sentiment)
    candlestick_brain = detect_candlestick_patterns(raw[main_tf], lookback=5)

    timeframes = {}
    for tf, data in tf_results.items():
        timeframes[tf] = {
            'role': TIMEFRAMES[tf]['role'],
            'score': round(data['score'], 2),
            'why': data['why'][:6],
            'structure': data['smc']['structure'],
            'liquidity': data['smc']['liquidity'],
            'premium_discount': data['smc']['premium_discount'],
            'fvgs': [_zone_to_dict(z) for z in data['smc']['fvgs'][-3:]],
            'order_blocks': [_zone_to_dict(z) for z in data['smc']['order_blocks'][-3:]],
        }

    regime = main_smc['structure']['direction'] + ' / ' + main_smc['premium_discount']['price_location']
    if action == 'WAIT':
        analyst_reason = (
            f"No trade in {style_profile.get('label', trade_style.title())} mode because the confluence is not clean enough. Current regime is {regime}. "
            f"A real analyst would wait for liquidity sweep, displacement, then retest of FVG/OB before entry."
        )
        human = analyst_reason
    else:
        side_word = 'buying' if action == 'BUY' else 'selling'
        main_reasons = []
        for tf in ['1d', '4h', '1h', '15m', '5m']:
            d = timeframes.get(tf)
            if not d:
                continue
            if action == 'BUY' and d['score'] > 0:
                main_reasons.append(f"{tf} supports buy: {', '.join(d['why'][:3])}")
            if action == 'SELL' and d['score'] < 0:
                main_reasons.append(f"{tf} supports sell: {', '.join(d['why'][:3])}")
        reason_line = '; '.join(main_reasons[:3]) if main_reasons else f"average multi-timeframe score supports {action.lower()}"
        if action == 'BUY':
            analyst_reason = (
                f"Why BUY in {style_profile.get('label', trade_style.title())} mode: Blue checked all configured timeframes, then planned execution from the {main_tf} chart. The setup is showing bullish confluence, not just one indicator. "
                f"{reason_line}. The main read shows price in {main_smc['premium_discount']['price_location']} zone, "
                f"with {main_smc['structure']['event']} and {main_smc['liquidity']['type']}. "
                f"That means buyers are currently stronger after liquidity/structure confirmation. "
                f"The stop loss is placed below the important swing or SMC zone, so the trade idea is invalid only if price breaks that protection area. "
                f"Targets are based on the risk distance, giving a cleaner reward-to-risk plan."
            )
        else:
            analyst_reason = (
                f"Why SELL in {style_profile.get('label', trade_style.title())} mode: Blue checked all configured timeframes, then planned execution from the {main_tf} chart. The setup is showing bearish confluence, not just one indicator. "
                f"{reason_line}. The main read shows price in {main_smc['premium_discount']['price_location']} zone, "
                f"with {main_smc['structure']['event']} and {main_smc['liquidity']['type']}. "
                f"That means sellers are currently stronger after liquidity/structure confirmation. "
                f"The stop loss is placed above the important swing or SMC zone, so the trade idea is invalid only if price breaks that protection area. "
                f"Targets are based on the risk distance, giving a cleaner reward-to-risk plan."
            )
        human = analyst_reason

    result = {
        'symbol': name, 'ticker': ticker, 'action': action, 'confidence': confidence,
        'base_action_before_filters': base_action_before_filters,
        'action_after_confidence_filter': action_after_confidence_filter,
        'trade_style': trade_style, 'trade_style_label': style_profile.get('label', trade_style.title()),
        'entry_timeframe': main_tf, 'style_note': style_profile.get('note', ''),
        'entry': entry, 'stop_loss': stop, 'target_1': t1, 'target_2': t2,
        'risk': risk, 'session': session, 'session_note': session_note,
        'regime': regime, 'news_caution': 'Check high-impact news before entry; this engine does not read live economic calendar.',
        'human_read': human, 'analyst_reason': analyst_reason, 'timeframes': timeframes,
        'sentiment': market_sentiment,
        'news_filter': news, 'macro_brain': macro_brain, 'market_context': market_context,
        'candlestick_brain': candlestick_brain,
        'chart_data_sources': data_sources,
        'chart_data_source': data_sources.get(main_tf, {}).get('source', 'unknown'),
        'broker_chart_symbol': data_sources.get(main_tf, {}).get('broker_symbol', ''),
        'advanced_concepts': ['Judas swing', 'AMD model', 'breaker block', 'mitigation block', 'IFVG', 'turtle soup', 'displacement candle', 'balanced price range', 'macro time window', 'dealing range'],
        'smc_upgrade': ['BOS/CHOCH structure', 'liquidity sweep', 'FVG', 'order block', 'premium/discount', 'kill zone', 'ATR risk model', 'post-analysis lot sizing', 'liquidity heatmap', 'SMT divergence', 'Forex Factory news filter', 'AI confidence learning', 'sentiment engine', 'candlestick pattern intelligence', 'smart trade management', 'replay coach', 'CNN+BiLSTM+Attention neural brain'],
    }
    # Phase 8: automatic human AI trading desk enrichment.
    # Works automatically in check, scanner, autopilot and voice replies.
    result = upgrade_signal(result)
    # Phase 9: intelligence/accuracy layer with hybrid ML ensemble and A+ filters.
    result = apply_phase9_intelligence(result)
    # Phase 11: user-provided dataset ML learning. It can reduce/block low-probability setups,
    # but it never forces trades.
    result = apply_dataset_ml_learning(result)
    # Phase 15.19: neural network pattern learner. It blends confidence and may block weak setups,
    # but it never forces orders. Best model is CNN+BiLSTM+Attention when TensorFlow is installed.
    result = apply_neural_network_brain(result)
    # Phase 15.22: self-learning profitability flywheel. Learns from setup/session memory and can reduce/block weak repeated patterns.
    result = apply_profitability_flywheel(result)
    # Phase 16: cognitive architecture adds market-DNA memory, opportunity ranking and verified-learning hints.
    result = apply_cognitive_architecture(result)
    # Phase 16.1: CME Group institutional futures context confirms/filters; never forces trades.
    result = apply_cme_group_brain(result)
    # Phase 16.2: Autonomous Evolution Engine adds verified-learning, market-DNA and ranking hints.
    result = apply_autonomous_evolution(result)
    # Phase 10: human trader brain adds context, memory, no-trade filters and modes.
    result = apply_human_trader_brain(result)
    # Phase 15.20: natural human-trader layer adds market story, scenarios and invalidation guidance.
    result = apply_human_trader_natural(result)
    # Phase 12: video/strategy knowledge lessons. Advisory only; never forces trades.
    result = apply_video_knowledge(result)
    # Phase 13: candlestick pattern intelligence. Confirmation/warning only; never forces trades.
    result = apply_candlestick_brain(result)
    result['management_plan'] = build_management_plan(result)
    result['coach_note'] = coach_feedback(result)

    # Phase 15.9: keep the market signal direction separate from execution permission.
    # Later filters can change action to WAIT for safety, but the user should still see
    # whether the market read was BUY, SELL, or truly neutral.
    current_action = str(result.get('action', 'WAIT')).upper()
    signal_direction = current_action if current_action in ['BUY', 'SELL'] else None
    for k in [
        'original_action_before_no_trade',
        'action_before_dataset_ml',
        'action_before_video_knowledge',
        'action_before_candlestick',
        'action_before_neural_network',
        'action_after_confidence_filter',
        'base_action_before_filters',
    ]:
        v = str(result.get(k, '')).upper().strip()
        if v in ['BUY', 'SELL']:
            signal_direction = v
            break
    if not signal_direction:
        signal_direction = 'WAIT'
    result['signal_direction'] = signal_direction
    result['execution_action'] = current_action
    if current_action == 'WAIT' and signal_direction in ['BUY', 'SELL']:
        result['autopilot_display_note'] = (
            f"Market signal is {signal_direction}, but execution is WAIT because one or more "
            "safety/intelligence filters blocked auto-trading."
        )

    # Phase 15 terminal reason card: explains the exact basis for BUY/SELL/WAIT.
    result = attach_terminal_reason_card(result)
    return result

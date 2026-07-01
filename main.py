import threading
import re
from config import APP_NAME, VERSION
try:
    from config import MAJOR_WATCHLIST_SYMBOLS
except Exception:
    MAJOR_WATCHLIST_SYMBOLS = ['xauusd', 'xagusd', 'ethusd', 'btcusd', 'usoil', 'usdjpy', 'eurusd', 'ustec', 'gbpusd']
from pathlib import Path
from utils.symbols import resolve_symbol, list_symbols
from risk.account import ask_account_after_analysis, save_account, load_account, position_size, empty_risk
from analysis.signal_engine import build_signal
from storage.database import save_signal
from research.monte_carlo import run_monte_carlo
from journal.cli import show_open_trades, close_trade_prompt, print_stats
from backtest.replay_engine import simple_replay_backtest
from vision.chart_screenshot import analyze_chart_screenshot
from voice.voice_loop import voice_session, voice_backend_status, voice_install_help
from voice.speaker import speak, interrupt_speech
from voice.background_listener import start_background_voice, stop_background_voice, background_voice_status_text
from ui.floating_orb import orb
from assistant_mode.autonomous import autonomous_watch
from vision.live_chart_ocr import live_chart_ocr_hint
from vision.real_chart_detection import detect_chart_visuals
from llm.analyst_brain import explain_with_llm, llm_help
from scanner.market_scanner import scan_market, print_scan
from memory.preferences import save_preference, preference_summary
from trade_management.manager import management_help
from utils.command_parser import parse_user_commands
from utils.trade_style import detect_trade_style, strip_style_words, style_label
from utils.trade_reasoning import format_terminal_reason_card, attach_terminal_reason_card
from utils.clean_terminal import compact_signal_card
from voice.conversation import conversation, detect_conversation_intent, answer_conversation_intent, make_human_voice_brief
from mt5_bridge.commands import handle_mt5_command
from mt5_bridge.terminal import lot_size_from_broker
from mt5_bridge.auto_executor import execute_signal_if_allowed, auto_status_text
from risk.session_trade_quota import quota_status_text
from mt5_bridge.auto_manager import auto_manager_status, manage_once, manager_loop, pyramiding_status, set_pyramiding_enabled, start_auto_manager_background, stop_auto_manager_background, auto_manager_background_status
from mt5_bridge.autopilot import autopilot_on, autopilot_off, autopilot_status
from mt5_bridge.order_doctor import order_doctor_report
from intelligence.phase9_intelligence import phase9_status_text, train_hybrid_ensemble, ml_learning_report, maybe_auto_retrain
from intelligence.human_trader_brain import human_brain_status_text, trader_modes_text, set_trader_mode_text
from intelligence.human_trader_natural import human_natural_status_text, render_human_report
from memory.trade_memory_brain import trade_memory_report
from broker_bridge.symbol_intelligence import broker_symbol_intelligence_report
from learning.dataset_learning import dataset_learning_help, dataset_learning_report, export_dataset_template, import_dataset_to_db, train_dataset_model
from learning.neural_network_brain import neural_help, neural_network_report, train_neural_network, set_neural_network
from learning.profitability_flywheel import (
    profitability_status_text, profitability_report_text, mistake_report_text,
    calibrate_confidence_text, set_profitability_flywheel,
)
from knowledge.video_learning import (
    video_learning_help, video_sources_report, video_learning_report, seed_default_video_sources,
    add_video_source, import_video_transcript, import_video_notes, try_fetch_public_transcript,
    fetch_all_public_transcripts,
)
from analysis.candlestick_patterns import (
    candlestick_help, candlestick_catalog_text, phase13_status_text, candlestick_report_for_symbol,
)
from knowledge.booming_bulls_learning import (
    booming_bulls_help, seed_booming_bulls_channel, fetch_booming_bulls_video_list,
    fetch_booming_bulls_public_transcripts, fetch_booming_bulls_forex_video_list, import_booming_bulls_notes,
    export_booming_bulls_knowledge_dataset, booming_bulls_report,
)
from learning.mt5_history_importer import learn_mt5_history, mt5_history_learning_help
from learning.backtest_importer import learn_backtest_csv, create_backtest_template, backtest_import_help
from learning.journal_history_importer import learn_blue_journal
from learning.auto_history_learning import (
    phase15_status_text, learning_report_text, set_auto_learning, set_auto_retrain, retrain_now,
    run_startup_auto_learning,
)
from learning.background_auto_learning import (
    start_background_learning_service, stop_background_learning_service,
    run_background_learning_once, background_learning_status_text,
)
from automation.full_auto_controller import (
    start_full_auto_mode, stop_full_auto_mode, full_auto_status_text,
    basic_auto_commands_text, set_full_auto_enabled, run_full_auto_now,
)
from knowledge.internet_learning import (
    internet_learning_help, seed_default_internet_sources, internet_sources_report,
    add_internet_source, collect_internet_learning, internet_learning_report,
    set_internet_learning, baby_brain_text,
)
from analytics.win_rate_intelligence import win_rate_report_text, win_rate_help_text, parse_win_rate_args
from analysis.market_data import (
    chart_data_source_status_text, set_chart_data_source, mt5_candles_test_text, compare_mt5_yahoo_text, get_chart_data_source
)
from diagnostics.self_healing_doctor import (
    run_startup_self_heal, explain_exception, blue_doctor_text, set_self_healing,
)
from brain.cognitive_architecture import cognitive_status_text, run_cognitive_pulse, set_cognitive_architecture
from institutional.cme_group_brain import cme_status_text, collect_cme_context, set_cme_brain, seed_cme_sources
from brain.autonomous_evolution import evolution_status_text, run_evolution_pulse, generate_monday_report


def apply_risk_after_analysis(result, allow_saved=False, interactive=True):
    if result['action'] == 'WAIT':
        return result

    # Background voice must not block the terminal with input() prompts.
    # For typed commands, Blue still asks for fresh balance/risk as before.
    if not interactive:
        account = load_account() if allow_saved else None
        if not account:
            result['risk'] = empty_risk()
            result['risk']['lot_note'] = 'Voice/background mode did not ask for balance/risk. Type risk to save account size, or type this command in terminal for fresh lot sizing.'
            return result
    else:
        # Always ask balance and risk after typed analysis so lot size is fresh for this setup.
        account = ask_account_after_analysis(result['symbol'], result['action'], result['entry'], result['stop_loss'], allow_saved=False)

    result['risk'] = position_size(account['balance'], account['risk_percent'], result['entry'], result['stop_loss'], ticker=result.get('ticker'))
    # If MT5 is connected, override/display lot sizing using real broker symbol specification.
    try:
        broker_lot = lot_size_from_broker(result.get('ticker') or result['symbol'], account['balance'], account['risk_percent'], result['entry'], result['stop_loss'])
        result['mt5_lot'] = broker_lot
        if broker_lot.get('ok'):
            result['risk']['recommended_lot_size'] = broker_lot.get('recommended_lot_size', result['risk'].get('recommended_lot_size', 0))
            result['risk']['lot_note'] = 'MT5 broker lot: ' + broker_lot.get('message', '')
    except Exception:
        pass
    return result


def build_voice_brief(r):
    # Human-style spoken answer with context memory.
    return make_human_voice_brief(r)


def print_signal(r, speak_output=False):
    """Clean Phase 15.21 terminal output.

    The old detailed data is still stored inside the signal object and journal,
    but the terminal now shows one readable card instead of a messy long dump.
    """
    print(compact_signal_card(r))
    if speak_output:
        speak(build_voice_brief(r), block=False)


def scan_one(text, from_voice=False):
    trade_style = detect_trade_style(text)
    clean_text = strip_style_words(text)
    name, ticker = resolve_symbol(clean_text)
    if not ticker:
        msg = 'Supported charts: ' + ', '.join(list_symbols())
        print(msg); return msg
    print(f'Analyzing {name} in {style_label(trade_style)} mode first...')
    orb.update('thinking', f'Analyzing {name} {style_label(trade_style)}')
    result = build_signal(name, ticker, account=None, trade_style=trade_style)
    result = apply_risk_after_analysis(result, allow_saved=from_voice, interactive=not from_voice)
    print_signal(result, speak_output=False)
    orb.update('speaking' if from_voice else 'ready', f"{name} {result['action']} {result['confidence']}%")
    save_signal(result)
    return build_voice_brief(result)


def strongest(trade_style='intraday', from_voice=False):
    results = []
    unique = list(MAJOR_WATCHLIST_SYMBOLS)
    print('Analyzing all symbols first...')
    for s in unique:
        name, ticker = resolve_symbol(s)
        try:
            results.append(build_signal(name, ticker, account=None, trade_style=trade_style))
        except Exception as e:
            print(f'Skipped {s}: {e}')
    results.sort(key=lambda x: x['confidence'], reverse=True)
    top = results[:3]
    actionable = [r for r in top if r['action'] != 'WAIT']
    shared_account = None
    if actionable:
        first = actionable[0]
        if from_voice:
            shared_account = load_account()
            if not shared_account:
                print('Voice/background mode: no saved risk settings. Type risk in terminal to save balance/risk for lot size.')
        else:
            shared_account = ask_account_after_analysis(first['symbol'], first['action'], first['entry'], first['stop_loss'])
    for r in top:
        if r['action'] != 'WAIT' and shared_account:
            r['risk'] = position_size(shared_account['balance'], shared_account['risk_percent'], r['entry'], r['stop_loss'], ticker=r.get('ticker'))
        print_signal(r); save_signal(r)


def set_account():
    balance = float(input('Enter account size/balance: ').strip())
    risk_percent = float(input('Enter risk percent per trade: ').strip())
    save_account(balance, risk_percent)
    print('Saved.')


def run_backtest_cmd(cmd):
    name, ticker = resolve_symbol(strip_style_words(cmd))
    if not ticker:
        print('Example: backtest gold'); return
    print(simple_replay_backtest(ticker))


def analyze_image_cmd(cmd):
    path = cmd.replace('screenshot', '').replace('image', '').replace('analyze', '').strip().strip('"')
    if not path:
        path = input('Enter screenshot path: ').strip().strip('"')
    print(analyze_chart_screenshot(path))


def build_symbol_report(symbol_text, trade_style='intraday', save=False):
    name, ticker = resolve_symbol(strip_style_words(symbol_text))
    if not ticker:
        msg = 'Supported charts: ' + ', '.join(list_symbols())
        print(msg)
        return None
    result = build_signal(name, ticker, account=None, trade_style=trade_style)
    if save:
        try:
            save_signal(result)
        except Exception:
            pass
    return result


def human_symbol_report(symbol_text, section='report'):
    trade_style = detect_trade_style(symbol_text)
    result = build_symbol_report(symbol_text, trade_style=trade_style, save=True)
    if not result:
        return 'Unsupported symbol'
    section = (section or 'report').lower().strip()
    if section == 'story':
        msg = (result.get('market_story') or {}).get('story_text') or render_human_report(result)
    elif section == 'scenario':
        plans = result.get('trade_scenarios') or {}
        msg = '\n'.join([plans.get('plan_a',''), plans.get('plan_b',''), plans.get('plan_c','')]).strip()
    elif section == 'invalidation':
        msg = result.get('trade_invalidation') or 'No invalidation available.'
    elif section == 'why_wait':
        nt = result.get('no_trade_intelligence') or {}
        msg = 'Why wait: ' + (nt.get('note') or result.get('analyst_reason') or 'No wait note available.')
    else:
        msg = render_human_report(result)
    print(msg)
    return msg


def news_macro_report(kind="news"):
    """Lightweight command output for news/macro commands.
    Full symbol-specific news checks still run inside normal analysis commands.
    """
    msg = (
        "News / Macro Brain\n"
        "- Blue checks Forex Factory-style news risk inside each symbol analysis when available.\n"
        "- High-impact USD/EUR/GBP/JPY events can reduce confidence or block weak trades.\n"
        "- Use: gold, eur, gbp, jpy, or best to see the news/macro filter inside the trade basis card.\n"
        "- For safest trading, avoid entries near CPI, NFP, FOMC, rate decisions, and major speeches."
    )
    print(msg)
    return msg


def learn_all_backtest_reports():
    """Learn every CSV found in reports/ and reports/auto_learn/."""
    folders = [Path('reports'), Path('reports/auto_learn')]
    files = []
    for folder in folders:
        if folder.exists():
            files.extend(sorted(folder.glob('*.csv')))
    if not files:
        msg = "No backtest CSV files found. Put files in reports/ or reports/auto_learn/, then type: backtest learn"
        print(msg)
        return msg
    lines = [f"Backtest learn all: found {len(files)} CSV file(s)."]
    total_rows = 0
    last_train = None
    for f in files:
        try:
            res = learn_backtest_csv(str(f), train_after=False)
            rows = int(res.get('rows', res.get('imported_rows', 0)) or 0)
            total_rows += rows
            lines.append(f"- {f}: {res.get('message', res)}")
        except Exception as exc:
            lines.append(f"- {f}: failed - {exc}")
    try:
        last_train = retrain_now()
        lines.append("Training: " + str(last_train.get('message', last_train)))
    except Exception as exc:
        lines.append("Training skipped: " + str(exc))
    lines.append(f"Total imported/processed rows reported: {total_rows}")
    msg = "\n".join(lines)
    print(msg)
    return msg

def simple_commands_text():
    return """Blue Friendly Commands — Phase 15.22 Self-Learning + Session Quota

Basic:
  help                      -> show this simple command menu
  start                     -> confirm Blue is running
  status / auto status      -> full automatic system status
  stop                      -> stop autopilot + background learning loop + voice speaking
  full auto on              -> start all automatic systems now
  full auto off             -> stop automatic systems and disable auto-start
  auto now                  -> run one automatic learning/background pulse
  basic commands            -> show the short auto/text command menu
  exit                      -> close Blue

Market analysis:
  gold / btc / eur / gbp / jpy -> analyze that pair
  check gold                -> analyze gold in human language
  gold buy or sell          -> ask Blue for direction
  best                      -> strongest setup scan
  scan                      -> scan forex/CFD pairs
  why                       -> reason behind the last signal
  reason gold               -> trade basis for that pair
  news                      -> news/macro risk reminder
  macro                     -> macro context reminder
  data source               -> show chart data source mode
  use mt5 data              -> analyze broker MT5 candles first/only
  use yahoo data            -> analyze old Yahoo/yfinance candles
  use auto data             -> MT5 first, Yahoo fallback
  mt5 candles gold          -> test MT5 broker candles for any pair
  compare data gold         -> compare MT5 close vs Yahoo close
  candles gold              -> candlestick read for any pair
  patterns                  -> candlestick pattern list

Learning / ML:
  learn                     -> run learning now
  learn on                  -> start background auto-learning
  learn off                 -> stop background auto-learning
  learn status              -> show background learning status
  train                     -> train ready ML dataset
  train brain               -> train Blue using ready dataset
  brain / ml report         -> show dataset ML report
  neural train              -> train Neural Network Brain
  neural report             -> show neural model status
  neural predict gold       -> analyze symbol with neural confirmation
  memory                    -> show trade memory report
  win rate                  -> connected account + journal + ML performance report
  gold win rate             -> symbol-specific win rate; works for any pair
  history learn             -> learn from Blue journal/demo trades
  mt5 learn                 -> learn from MT5 closed history, last 30 days
  backtest learn            -> learn all CSV files from reports/ and reports/auto_learn/
  internet learn            -> learn market context from trusted internet/RSS sources
  internet report           -> show internet/environment memory
  internet on/off           -> enable/disable internet learning background mode
  internet sources          -> show trusted public learning sources
  baby brain                -> explain how Blue learns like a human
  self learn                -> show self-learning flywheel status
  self learn on/off         -> enable/disable profitability flywheel
  self report               -> setup/session learning report
  profitability report      -> same as self report
  mistake report            -> show repeated weak setups/loss patterns
  calibrate confidence      -> refresh confidence calibration from memory
  session quota             -> show 2-trades/day Gold/Other reserved quota

Broker / Account:
  broker                    -> broker status
  connect                   -> connect selected broker
  connect mt5               -> connect MT5
  use exness                -> switch broker profile to Exness
  use xm                    -> switch broker profile to XM
  use auto broker           -> auto-detect broker profile
  account / balance         -> show MT5 account info
  risk                      -> save account balance and risk percent
  lot gold                  -> calculate broker lot size for any pair
  symbols gold              -> show broker symbols for any pair
  spec gold                 -> show broker symbol specification for any pair

Trade management:
  trades / profit           -> show open MT5 positions
  stats / win rate          -> show connected-account win rate and performance
  journal                   -> show Blue journal
  breakeven gold / be gold  -> move SL to entry if profitable; works for any pair
  trail gold                -> one-time safe trailing update; works for any pair
  close gold                -> close open positions for that pair
  close half gold           -> partial close 50% for that pair
  manager on                -> run auto manager once
  manager off               -> stop manager loop / no continuous manager
  manager                   -> auto manager status

Autopilot / Voice / UI:
  autopilot                 -> autopilot status
  autopilot on              -> turn autopilot on
  autopilot off             -> turn autopilot off
  scan auto                 -> autonomous all-pairs scan
  session quota             -> 2 trades/day: 1 Gold slot + 1 other-pair slot
  voice / talk              -> start/resume background voice listener; typed commands still work
  voice off                 -> stop background voice listener
  voice background status   -> show always-on voice listener status
  voice text status         -> same: check parallel voice + text mode
  voice session             -> old blocking voice mode
  quiet                     -> stop voice reply
  screenshot                -> analyze chart screenshot
  ocr                       -> live chart OCR help

New Phase 15.18 parallel commands:
  voice text on / dual mode / parallel mode -> start non-blocking voice + text mode
  voice text off                            -> stop only the voice listener
  voice text status                         -> show voice listener status

Human examples:
  tell me gold buy or sell
  show me best trade
  show my win rate
  take out win rate of btc
  why should we take this trade
  learn from history
  train your brain
  connect my broker
  use xm broker
  move gold to breakeven
  show my open trades
  stop everything

Note: pair commands are generic. Major focus: xauusd, xagusd, ethusd, btcusd, usoil, usdjpy, eurusd, ustec, gbpusd. Other supported symbols still work as minor/additional.
"""

def handle_command(cmd, from_voice=False, normalized=False):
    cmd = cmd.strip().lower()
    conversation.remember_user(cmd)

    # Phase 15.17 — Auto Everything + Text Command mode.
    # Heavy services start automatically; these basic commands are manual controls/overrides.
    if cmd in ['status', 'blue status', 'system status', 'auto status', 'automatic status', 'full auto status', 'automation status']:
        msg = full_auto_status_text(); print(msg); return msg
    if cmd in ['basic commands', 'auto commands', 'automatic commands', 'full auto commands', 'text command mode', 'auto mode']:
        msg = basic_auto_commands_text(); print(msg); return msg
    if cmd in ['full auto on', 'auto on', 'automatic on', 'start automatic', 'start everything automatic']:
        set_full_auto_enabled(True)
        res = start_full_auto_mode(print_fn=print, command_handler=handle_command, force=True)
        msg = res.get('message', str(res))
        for line in res.get('results', []):
            print(line)
        if res.get('warnings'):
            print('Warnings:')
            for w in res.get('warnings', []):
                print('-', w)
        print(msg)
        return msg
    if cmd in ['full auto off', 'auto off', 'automatic off', 'disable automatic', 'disable auto start']:
        res = stop_full_auto_mode(disable_autostart=True)
        msg = res.get('message', str(res))
        print(msg)
        return msg
    if cmd in ['auto now', 'automatic now', 'run auto now', 'background now']:
        res = run_full_auto_now(print_fn=print)
        msg = res.get('message', str(res))
        return msg

    # One-command autopilot. Terminal-only; MT5 must already be running.
    if cmd in ['blue autopilot on', 'autopilot on', 'start autopilot', 'automate everything']:
        msg = autopilot_on(scan_seconds=300)
        print(msg)
        return msg
    if cmd in ['blue autopilot off', 'autopilot off', 'stop autopilot']:
        msg = autopilot_off()
        print(msg)
        if from_voice:
            speak(msg, block=False)
        return msg
    if cmd in ['blue autopilot status', 'autopilot status']:
        msg = autopilot_status()
        print(msg)
        return msg

    if cmd in ['evolution status', 'phase16.2 status', 'phase16 2 status']:
        msg = evolution_status_text(); print(msg); return msg
    if cmd in ['evolution now', 'phase16.2 now', 'phase16 2 now', 'weekly report now']:
        res = run_evolution_pulse(force_monday_report=True); msg = res.get('message', str(res)); print(msg); return msg
    if cmd in ['monday report', 'weekly evolution report']:
        res = generate_monday_report(force=True); msg = res.get('message', str(res)); print(msg); return msg

    if cmd in ['blue start status', 'start status']:
        msg = 'Blue is already running. Type help for simple commands, or type gold / best / train / learn status.'
        print(msg)
        return msg
    if cmd in ['blue doctor', 'doctor', 'self doctor', 'health', 'health check', 'system check']:
        msg = blue_doctor_text(); print(msg); return msg
    if cmd in ['self heal on', 'self healing on', 'doctor on']:
        msg = set_self_healing(True); print(msg); return msg
    if cmd in ['self heal off', 'self healing off', 'doctor off']:
        msg = set_self_healing(False); print(msg); return msg
    if cmd in ['stop everything', 'stop all', 'stop']:
        res = stop_full_auto_mode(disable_autostart=False)
        msg = res.get('message', str(res))
        print(msg)
        return msg
    if cmd in ['news report', 'macro report']:
        return news_macro_report('macro' if 'macro' in cmd else 'news')
    if cmd in ['why last trade', 'last reason', 'why should we take this trade']:
        answer = answer_conversation_intent('why_last') or 'No previous analyzed trade is stored yet. Type gold or best first, then type why.'
        print(answer)
        return answer

    # MT5 terminal-only commands. These never open MT5 from code; MT5 must already be running.
    mt5_answer = handle_mt5_command(cmd)
    if mt5_answer:
        print(mt5_answer)
        if from_voice:
            speak(mt5_answer, block=False)
        return mt5_answer

    # Human conversation layer: lets user ask follow-ups like 'why?', 'repeat',
    # 'what is lot size?', 'short answer', etc.
    conv_intent = detect_conversation_intent(cmd)
    if conv_intent and conv_intent != 'market_opinion':
        answer = answer_conversation_intent(conv_intent)
        if answer:
            print(answer)
            if from_voice:
                speak(answer, block=False)
            return answer

    if not normalized:
        parsed = parse_user_commands(cmd)
        if len(parsed) > 1 or (parsed and parsed[0] != cmd):
            last_response = None
            for one in parsed:
                print(f"Command understood: {one}")
                last_response = handle_command(one, from_voice=from_voice, normalized=True)
            return last_response
    # Phase 15.14 — MT5 Chart Data Engine. Lets Blue analyze broker candles instead of Yahoo candles.
    if cmd in ['data source', 'chart data', 'data mode', 'source data', 'chart source']:
        msg = chart_data_source_status_text(); print(msg); return msg
    if cmd in ['use mt5 data', 'mt5 data on', 'use broker data', 'use broker candles', 'use mt5 candles', 'mt5 chart data', 'broker chart data']:
        src = set_chart_data_source('mt5')
        msg = 'Chart data source set to MT5 ONLY. Blue will analyze connected broker candles. If MT5 is not connected, analysis will fail instead of using Yahoo fallback.'
        print(msg); return msg
    if cmd in ['use yahoo data', 'use yfinance data', 'yahoo data on', 'use old data', 'yahoo chart data']:
        src = set_chart_data_source('yahoo')
        msg = 'Chart data source set to YAHOO/YFINANCE ONLY. This is the old fallback mode.'
        print(msg); return msg
    if cmd in ['use auto data', 'auto data', 'use auto chart data', 'auto chart source', 'mt5 first data']:
        src = set_chart_data_source('auto')
        msg = 'Chart data source set to AUTO. Blue will use MT5 broker candles first, then Yahoo/yfinance fallback if MT5 candles are unavailable.'
        print(msg); return msg
    if cmd.startswith('mt5 candles ') or cmd.startswith('broker candles '):
        token = cmd.replace('mt5 candles ', '', 1).replace('broker candles ', '', 1).strip() or 'gold'
        name, ticker = resolve_symbol(token)
        if not ticker:
            ticker = token
            name = token.upper()
        msg = mt5_candles_test_text(ticker, name, interval='5m', period='5d')
        print(msg); return msg
    if cmd.startswith('compare data ') or cmd.startswith('compare chart data ') or cmd.startswith('compare candles '):
        token = cmd.replace('compare chart data ', '', 1).replace('compare data ', '', 1).replace('compare candles ', '', 1).strip() or 'gold'
        name, ticker = resolve_symbol(token)
        if not ticker:
            ticker = token
            name = token.upper()
        msg = compare_mt5_yahoo_text(ticker, name, interval='5m', period='5d')
        print(msg); return msg

    # Phase 15.15 — Order Execution Doctor. Read-only: no order_send(), only diagnostics/order_check.
    if cmd in ['order doctor help', 'execution doctor help', 'trade doctor help']:
        msg = (
            'Order Doctor commands:\n'
            '  order doctor              -> diagnose default gold / current broker execution settings\n'
            '  order doctor gold         -> diagnose gold order mechanics\n'
            '  execution doctor eurusd   -> diagnose EURUSD order mechanics\n'
            '  why no order              -> explain common blockers for auto execution\n'
            'The doctor is read-only. It does not place, close, or modify trades.'
        )
        print(msg); return msg
    if (cmd in ['order doctor', 'execution doctor', 'trade doctor', 'why no order', 'why order not execute', 'why not punch order', 'order check']
        or cmd.startswith('order doctor ') or cmd.startswith('execution doctor ') or cmd.startswith('trade doctor ') or cmd.startswith('order check ')):
        token = cmd
        for prefix in ['order doctor', 'execution doctor', 'trade doctor', 'order check']:
            if token.startswith(prefix):
                token = token.replace(prefix, '', 1).strip()
                break
        if token in ['', 'why no order', 'why order not execute', 'why not punch order']:
            token = 'gold'
        # Build a fresh signal if a symbol was provided, so doctor can also check action/confidence.
        signal = None
        name, ticker = resolve_symbol(token)
        try:
            if ticker:
                signal = build_signal(name, ticker, account=None, trade_style='intraday')
                signal = attach_terminal_reason_card(signal)
        except Exception as exc:
            print(f'Order doctor signal build skipped: {exc}')
        msg = order_doctor_report(symbol_text=(ticker or token), signal=signal, run_order_check=True)
        print(msg)
        if from_voice:
            speak('Order doctor report is ready in terminal.', block=False)
        return msg

    # Phase 15.7 — Win Rate Intelligence. Works from text and always-on voice.
    if cmd in ['win rate help', 'winrate help', 'performance help']:
        msg = win_rate_help_text(); print(msg); return msg
    if (cmd in ['win rate', 'winrate', 'stats', 'statistics', 'performance', 'account win rate',
                'connected account win rate', 'show win rate', 'show my win rate', 'show everything',
                'show me everything', 'everything report']
        or cmd.startswith('win rate ') or cmd.startswith('winrate ')
        or cmd.startswith('account win rate') or cmd.startswith('connected account win rate')
        or 'win rate' in cmd or 'winrate' in cmd or 'take out win rate' in cmd):
        symbol_arg, days = parse_win_rate_args(cmd)
        msg = win_rate_report_text(symbol_text=symbol_arg, days=days, include_learning=True)
        print(msg)
        if from_voice:
            # Voice gets a compact summary; full details remain printed in terminal.
            first_lines = [line for line in msg.splitlines() if 'Win rate:' in line or line.startswith('Closed trades')][:3]
            speak('Win rate report is ready in terminal. ' + ' '.join(first_lines), block=False)
        return msg

    if cmd in ['exit', 'quit']:
        raise SystemExit
    if cmd in ['simple help', 'friendly help', 'help', 'commands', '?', 'menu']:
        msg = simple_commands_text(); print(msg); return msg
    if cmd in ['set risk', 'risk settings']:
        if from_voice:
            msg = 'For safety, please type risk in the terminal so Blue can ask balance and risk percent clearly.'
            print(msg); return msg
        set_account(); return 'Risk settings saved.'
    if cmd == 'account':
        if from_voice:
            msg = 'For safety, please type account in the terminal to enter balance and risk details.'
            print(msg); return msg
        set_account(); return 'Account saved.'
    if cmd == 'strongest': strongest(from_voice=from_voice); return 'Strongest intraday scan complete.'

    # Phase 15.16 — Internet / Environment Learning Brain. Read-only; never places trades.
    if cmd in ['internet help', 'web help', 'environment help', 'learning brain help']:
        msg = internet_learning_help(); print(msg); return msg
    if cmd in ['internet seed', 'web seed', 'environment seed']:
        res = seed_default_internet_sources(); msg = res.get('message', str(res)); print(msg); return msg
    if cmd in ['internet sources', 'web sources', 'environment sources']:
        msg = internet_sources_report(); print(msg); return msg
    if cmd.startswith('internet add ') or cmd.startswith('web add ') or cmd.startswith('environment add '):
        url = cmd.replace('internet add ', '', 1).replace('web add ', '', 1).replace('environment add ', '', 1).strip().strip('"')
        res = add_internet_source(url); msg = res.get('message', str(res)); print(msg); return msg
    if cmd in ['internet learn', 'internet learn now', 'web learn', 'learn from internet', 'environment learn', 'learn environment', 'environment study']:
        res = collect_internet_learning()
        msg = res.get('message', str(res))
        print(msg)
        if res.get('report_file'):
            print('Report:', res.get('report_file'))
        if res.get('dataset_file'):
            print('Dataset:', res.get('dataset_file'))
        return msg
    if cmd in ['internet report', 'web report', 'environment report', 'internet memory', 'web memory']:
        msg = internet_learning_report(); print(msg); return msg
    if cmd in ['internet on', 'web on', 'environment on']:
        msg = set_internet_learning(True, background=True); print(msg); return msg
    if cmd in ['internet off', 'web off', 'environment off']:
        msg = set_internet_learning(False, background=False); print(msg); return msg
    if cmd in ['baby brain', 'newborn brain', 'human learning brain', 'learning model']:
        msg = baby_brain_text(); print(msg); return msg

    # Phase 15.27 — Self Learning Flywheel + Gold/Other reserved quota.
    if cmd in ['self learn', 'self learning', 'profitability flywheel', 'flywheel status']:
        msg = profitability_status_text(); print(msg); return msg
    if cmd in ['self learn on', 'profitability on', 'flywheel on']:
        msg = set_profitability_flywheel(enabled=True); print(msg); return msg
    if cmd in ['self learn off', 'profitability off', 'flywheel off']:
        msg = set_profitability_flywheel(enabled=False); print(msg); return msg
    if cmd in ['self report', 'profitability report', 'flywheel report', 'pair report', 'session report', 'setup winrate']:
        msg = profitability_report_text(); print(msg); return msg
    if cmd in ['mistake report', 'loss report', 'weak setup report']:
        msg = mistake_report_text(); print(msg); return msg
    if cmd in ['calibrate confidence', 'confidence calibration', 'calibrate']:
        msg = calibrate_confidence_text(); print(msg); return msg
    if cmd in ['session quota', 'quota status', 'trade quota', 'daily quota']:
        msg = quota_status_text(); print(msg); return msg

    # Phase 15.2 — background auto-learning worker. Read-only; never places trades.
    if cmd in ['background learn status', 'background learning status', 'auto learn background status', 'phase15 background status']:
        msg = background_learning_status_text(); print(msg); return msg
    if cmd in ['background learn start', 'background learning on', 'start background learning', 'start auto learning background']:
        res = start_background_learning_service(print_fn=print)
        msg = res.get('message', str(res)); print(msg); return msg
    if cmd in ['background learn stop', 'background learning off', 'stop background learning', 'stop auto learning background']:
        res = stop_background_learning_service()
        msg = res.get('message', str(res)); print(msg); return msg
    if cmd in ['background learn now', 'run background learning now', 'auto background learn now']:
        res = run_background_learning_once(verbose=True)
        msg = res.get('message', str(res)); print(msg); return msg

    # Phase 15 — automatic MT5/backtest history learning. Read-only; never places trades.
    if cmd in ['phase15 status', 'auto history status', 'history learning status']:
        msg = phase15_status_text(); print(msg); return msg
    if cmd in ['startup learn now', 'auto learn now', 'run startup learning']:
        res = run_startup_auto_learning(verbose=True)
        msg = res.get('message', str(res))
        print(msg)
        return msg
    if cmd in ['learning report', 'phase15 report', 'auto history report']:
        msg = learning_report_text(); print(msg); return msg
    if cmd in ['auto learn on', 'auto learning on']:
        msg = set_auto_learning(True); print(msg); return msg
    if cmd in ['auto learn off', 'auto learning off']:
        msg = set_auto_learning(False); print(msg); return msg
    if cmd in ['auto retrain on', 'auto ml retrain on']:
        msg = set_auto_retrain(True); print(msg); return msg
    if cmd in ['auto retrain off', 'auto ml retrain off']:
        msg = set_auto_retrain(False); print(msg); return msg
    if cmd in ['retrain now', 'ml retrain now', 'train from imported history']:
        res = retrain_now(); msg = res.get('message', str(res)); print(msg); return msg
    if cmd in ['journal learn history', 'learn blue journal', 'blue journal learn', 'learn demo journal']:
        res = learn_blue_journal(train_after=True)
        msg = res.get('message', str(res))
        print(msg)
        tr = res.get('train_result') or {}
        if tr:
            print('Training:', tr.get('message', tr))
        return msg
    if cmd in ['mt5 learn help', 'mt5 history learning help', 'history learning help']:
        msg = mt5_history_learning_help(); print(msg); return msg
    if cmd.startswith('mt5 learn history') or cmd.startswith('learn mt5 history'):
        raw = cmd.replace('mt5 learn history', '', 1).replace('learn mt5 history', '', 1).strip()
        parts = raw.split()
        days = 30
        tf = '5m'
        if parts:
            if parts[0] == 'all':
                days = 3650
                parts = parts[1:]
            else:
                token = parts[0].replace('days', '').replace('day', '').replace('d', '')
                if token.isdigit():
                    days = int(token)
                    parts = parts[1:]
        for part in parts:
            if part in ['1m','3m','5m','15m','30m','1h','4h','1d','daily']:
                tf = '1d' if part == 'daily' else part
        res = learn_mt5_history(days=days, timeframe=tf, train_after=True, reconstruct=True)
        msg = res.get('message', str(res))
        print(msg)
        tr = res.get('train_result') or {}
        if tr:
            print('Training:', tr.get('message', tr))
        return msg
    if cmd in ['backtest learning help', 'backtest import help']:
        msg = backtest_import_help(); print(msg); return msg
    if cmd in ['backtest template', 'create backtest template']:
        res = create_backtest_template(); msg = f"Backtest template ready: {res.get('template_file')}"; print(msg); return msg
    if cmd in ['backtest learn all', 'backtest import all', 'learn all backtests']:
        return learn_all_backtest_reports()
    if cmd.startswith('backtest learn ') or cmd.startswith('backtest import '):
        path = cmd.replace('backtest learn ', '', 1).replace('backtest import ', '', 1).strip().strip('\"')
        if path in ['all', 'everything']:
            return learn_all_backtest_reports()
        res = learn_backtest_csv(path, train_after=True)
        msg = res.get('message', str(res))
        print(msg)
        tr = res.get('train_result') or {}
        if tr:
            print('Training:', tr.get('message', tr))
        return msg

    if cmd in ['neural help', 'nn help', 'neural network help']:
        msg = neural_help(); print(msg); return msg
    if cmd in ['neural report', 'nn report', 'neural status', 'nn status']:
        msg = neural_network_report(); print(msg); return msg
    if cmd in ['neural on', 'nn on']:
        msg = set_neural_network(enabled=True); print(msg); return msg
    if cmd in ['neural off', 'nn off']:
        msg = set_neural_network(enabled=False); print(msg); return msg
    if cmd in ['neural background on', 'nn background on']:
        msg = set_neural_network(background=True); print(msg); return msg
    if cmd in ['neural background off', 'nn background off']:
        msg = set_neural_network(background=False); print(msg); return msg
    if cmd in ['neural train', 'train neural', 'nn train', 'train neural network', 'deep learn']:
        res = train_neural_network(path=None, use_imported=True, force=True)
        msg = res.get('message', str(res)); print(msg); return msg
    if cmd.startswith('neural train dataset ') or cmd.startswith('nn train dataset '):
        path = cmd.replace('neural train dataset ', '', 1).replace('nn train dataset ', '', 1).strip().strip('"')
        res = train_neural_network(path=path, use_imported=True, force=True)
        msg = res.get('message', str(res)); print(msg); return msg
    if cmd.startswith('neural predict ') or cmd.startswith('nn predict '):
        token = cmd.replace('neural predict ', '', 1).replace('nn predict ', '', 1).strip() or 'gold'
        return scan_one(token, from_voice=from_voice)

    if cmd in ['phase9 status', 'ml status', 'intelligence status']:
        msg = phase9_status_text(); print(msg); return msg
    if cmd in ['human brain status', 'trader brain status', 'phase10 status', 'human brain', 'human report']:
        msg = human_natural_status_text() + '\n\n' + human_brain_status_text(); print(msg); return msg
    if cmd in ['trader modes', 'personality modes']:
        msg = trader_modes_text(); print(msg); return msg
    if cmd in ['safe trader mode', 'conservative trader mode']:
        msg = set_trader_mode_text('conservative'); print(msg); return msg
    if cmd in ['aggressive trader mode']:
        msg = set_trader_mode_text('aggressive'); print(msg); return msg
    if cmd.startswith('trader mode ') or cmd.startswith('set trader mode '):
        mode = cmd.replace('set trader mode ', '').replace('trader mode ', '').strip()
        msg = set_trader_mode_text(mode); print(msg); return msg
    if cmd.startswith('market story '):
        token = cmd.replace('market story ', '', 1).strip() or 'gold'
        return human_symbol_report(token, section='story')
    if cmd.startswith('scenario '):
        token = cmd.replace('scenario ', '', 1).strip() or 'gold'
        return human_symbol_report(token, section='scenario')
    if cmd.startswith('plan '):
        token = cmd.replace('plan ', '', 1).strip() or 'gold'
        return human_symbol_report(token, section='scenario')
    if cmd.startswith('trade invalidation '):
        token = cmd.replace('trade invalidation ', '', 1).strip() or 'gold'
        return human_symbol_report(token, section='invalidation')
    if cmd in ['why wait', 'should we take this trade']:
        return human_symbol_report('gold', section='why_wait')
    if cmd in ['trade memory', 'memory report', 'learning memory']:
        msg = trade_memory_report(); print(msg); return msg
    if cmd in ['broker intelligence', 'broker brain', 'symbol intelligence']:
        msg = broker_symbol_intelligence_report(); print(msg); return msg
    if cmd in ['ml train', 'train ml', 'retrain ml']:
        res = train_hybrid_ensemble(force=True)
        msg = (res.get('message') or str(res))
        print(msg); return msg
    if cmd in ['ml report', 'auto learning status']:
        msg = ml_learning_report(); print(msg); return msg
    if cmd in ['ml dataset help', 'dataset help', 'dataset learning help']:
        msg = dataset_learning_help(); print(msg); return msg
    if cmd in ['ml dataset template', 'dataset template', 'create ml template']:
        res = export_dataset_template(); msg = f"Template ready: {res.get('template_file')}\nSample ready: {res.get('sample_file')}"; print(msg); return msg
    if cmd in ['ml dataset report', 'dataset report', 'phase11 status']:
        msg = dataset_learning_report(); print(msg); return msg
    if cmd.startswith('ml import dataset ') or cmd.startswith('import dataset '):
        path = cmd.replace('ml import dataset ', '', 1).replace('import dataset ', '', 1).strip().strip('\"')
        res = import_dataset_to_db(path); msg = f"Imported {res.get('imported_rows')} labeled rows from {res.get('source_file')}"; print(msg); return msg
    if cmd.startswith('ml train dataset ') or cmd.startswith('train dataset '):
        path = cmd.replace('ml train dataset ', '', 1).replace('train dataset ', '', 1).strip().strip('\"')
        res = train_dataset_model(path=path, use_imported=True); msg = res.get('message', str(res)); print(msg); return msg
    if cmd in ['ml train imported dataset', 'train imported dataset']:
        res = train_dataset_model(path=None, use_imported=True); msg = res.get('message', str(res)); print(msg); return msg
    if cmd in ['video learning help', 'youtube learning help', 'video help']:
        msg = video_learning_help(); print(msg); return msg
    if cmd in ['video seed sources', 'youtube seed sources']:
        res = seed_default_video_sources(); msg = f"Saved video sources. Added {res.get('added')} new, updated {res.get('updated')}."; print(msg); return msg
    if cmd in ['video sources', 'youtube sources']:
        msg = video_sources_report(); print(msg); return msg
    if cmd in ['video knowledge report', 'youtube knowledge report', 'phase12 status']:
        msg = video_learning_report(); print(msg); return msg
    if cmd.startswith('video add source ') or cmd.startswith('youtube add source '):
        url = cmd.replace('video add source ', '', 1).replace('youtube add source ', '', 1).strip().strip('"')
        res = add_video_source(url); msg = res.get('message', str(res)); print(msg); return msg
    if cmd.startswith('video import transcript ') or cmd.startswith('youtube import transcript '):
        raw = cmd.replace('video import transcript ', '', 1).replace('youtube import transcript ', '', 1).strip()
        parts = raw.split()
        if len(parts) < 2:
            msg = 'Use: video import transcript <youtube_url_or_id> <path/to/transcript.txt>'
        else:
            ref = parts[0].strip('"')
            path = ' '.join(parts[1:]).strip('"')
            res = import_video_transcript(ref, path); msg = res.get('message', str(res))
        print(msg); return msg
    if cmd.startswith('video import notes ') or cmd.startswith('youtube import notes '):
        path = cmd.replace('video import notes ', '', 1).replace('youtube import notes ', '', 1).strip().strip('"')
        res = import_video_notes(path); msg = res.get('message', str(res)); print(msg); return msg
    if cmd in ['video fetch all transcripts', 'youtube fetch all transcripts', 'video learn from sources', 'youtube learn from sources']:
        res = fetch_all_public_transcripts()
        msg = res.get('message', str(res))
        print(msg)
        for item in res.get('results', [])[:20]:
            print(f"- {item.get('video_id')}: {'OK' if item.get('ok') else 'FAILED'} — {item.get('message')}")
        return msg
    if cmd.startswith('video fetch transcript ') or cmd.startswith('youtube fetch transcript '):
        ref = cmd.replace('video fetch transcript ', '', 1).replace('youtube fetch transcript ', '', 1).strip().strip('"')
        res = try_fetch_public_transcript(ref); msg = res.get('message', str(res)); print(msg); return msg
    if cmd in ['booming bulls help', 'boomingbulls help', 'bb help']:
        msg = booming_bulls_help(); print(msg); return msg
    if cmd in ['booming bulls seed', 'boomingbulls seed', 'bb seed']:
        res = seed_booming_bulls_channel(); msg = res.get('message', str(res)); print(msg); return msg
    if cmd.startswith('booming bulls fetch forex videos') or cmd.startswith('boomingbulls fetch forex videos') or cmd.startswith('bb fetch forex videos'):
        parts = cmd.split()
        limit = 100
        for token in reversed(parts):
            if token.isdigit():
                limit = int(token); break
        res = fetch_booming_bulls_forex_video_list(limit=limit); msg = res.get('message', str(res)); print(msg); return msg
    if cmd.startswith('booming bulls fetch videos') or cmd.startswith('boomingbulls fetch videos') or cmd.startswith('bb fetch videos'):
        parts = cmd.split()
        limit = 50
        for token in reversed(parts):
            if token.isdigit():
                limit = int(token); break
        res = fetch_booming_bulls_video_list(limit=limit); msg = res.get('message', str(res)); print(msg); return msg
    if cmd.startswith('booming bulls fetch transcripts') or cmd.startswith('boomingbulls fetch transcripts') or cmd.startswith('bb fetch transcripts'):
        parts = cmd.split()
        limit = 25
        for token in reversed(parts):
            if token.isdigit():
                limit = int(token); break
        res = fetch_booming_bulls_public_transcripts(limit=limit)
        msg = res.get('message', str(res)); print(msg)
        for item in res.get('results', [])[:20]:
            print(f"- {item.get('video_id')}: {'OK' if item.get('ok') else 'FAILED'} — {item.get('message')}")
        return msg
    if cmd.startswith('booming bulls import notes ') or cmd.startswith('boomingbulls import notes ') or cmd.startswith('bb import notes '):
        path = cmd.replace('booming bulls import notes ', '', 1).replace('boomingbulls import notes ', '', 1).replace('bb import notes ', '', 1).strip().strip('"')
        res = import_booming_bulls_notes(path); msg = res.get('message', str(res)); print(msg); return msg
    if cmd in ['booming bulls export dataset', 'boomingbulls export dataset', 'bb export dataset']:
        res = export_booming_bulls_knowledge_dataset(); msg = res.get('message', str(res)); print(msg); return msg
    if cmd in ['booming bulls report', 'boomingbulls report', 'bb report', 'phase14 status']:
        msg = booming_bulls_report(); print(msg); return msg
    if cmd in ['candle help', 'candlestick help', 'candles help']:
        msg = candlestick_help(); print(msg); return msg
    if cmd in ['candlestick patterns', 'candle patterns', 'candle catalog', 'candlestick catalog']:
        msg = candlestick_catalog_text(); print(msg); return msg
    if cmd in ['phase13 status', 'candlestick status', 'candle status']:
        msg = phase13_status_text(); print(msg); return msg
    if cmd.startswith('candles ') or cmd.startswith('candle '):
        raw = cmd.replace('candles ', '', 1).replace('candle ', '', 1).strip()
        parts = raw.split()
        tf = '5m'
        if parts and parts[-1].lower() in ['1m','3m','5m','15m','30m','1h','4h','1d','daily']:
            tf = '1d' if parts[-1].lower() == 'daily' else parts[-1].lower()
            raw_symbol = ' '.join(parts[:-1])
        else:
            raw_symbol = raw
        name, ticker = resolve_symbol(raw_symbol)
        if not ticker:
            msg = 'Use: candles gold OR candles eurusd 15m'
        else:
            msg = candlestick_report_for_symbol(name, ticker, timeframe=tf)
        print(msg); return msg
    if cmd in ['ml auto retrain', 'auto retrain ml']:
        res = maybe_auto_retrain(); msg = res.get('reason', str(res)); print(msg); return msg
    if cmd in ['auto status', 'auto execution status']:
        msg = auto_status_text() + '\n\n' + quota_status_text(); print(msg); return msg
    if cmd in ['auto manager status', 'manager status', 'manager']:
        msg = auto_manager_status() + '\n\n' + auto_manager_background_status(); print(msg); return msg
    if cmd in ['auto manager off', 'manager off', 'stop manager']:
        msg = stop_auto_manager_background(); print(msg); return msg

    if cmd in ['pyramiding status', 'pyramid status', 'scale in status']:
        msg = pyramiding_status(); print(msg); return msg
    if cmd in ['pyramiding on', 'pyramid on', 'scale in on']:
        msg = set_pyramiding_enabled(True); print(msg); return msg
    if cmd in ['pyramiding off', 'pyramid off', 'scale in off']:
        msg = set_pyramiding_enabled(False); print(msg); return msg
    if cmd in ['auto manager on', 'manager on', 'manage trades', 'manage now']:
        bg = start_auto_manager_background(); once = manage_once(); msg = bg + '\n\n' + once; print(msg); return msg
    if cmd.startswith('auto manager loop') or cmd.startswith('manager loop'):
        msg = manager_loop(cycles=10); print(msg); return msg
    if cmd == 'risk-test':
        acc = load_account()
        if not acc: print('No saved account yet.'); return 'No saved account yet.'
        print(run_monte_carlo(risk_percent=acc['risk_percent'])); return 'Risk test complete.'
    if cmd in ['journal', 'open trades']: show_open_trades(); return 'Open journal shown.'
    if cmd in ['close trade', 'update trade']: close_trade_prompt(); return 'Trade updated.'
    if cmd in ['journal stats']:
        print_stats(); return 'Journal stats shown.'
    if cmd.startswith('backtest'): run_backtest_cmd(cmd); return 'Backtest complete.'
    if cmd.startswith('screenshot') or cmd.startswith('image') or cmd.startswith('analyze image'):
        analyze_image_cmd(cmd); return 'Screenshot analysis complete.'
    if cmd in ['voice text on', 'text voice on', 'voice and text', 'dual mode', 'parallel mode', 'both mode']:
        res = start_background_voice(handle_command, print_fn=print, speak_ready=True)
        msg = res.get('message', str(res)); print(msg); return msg
    if cmd in ['voice text off', 'text voice off']:
        res = stop_background_voice()
        msg = res.get('message', str(res)); print(msg); return msg
    if cmd in ['voice text status', 'parallel voice status', 'parallel mode status']:
        msg = background_voice_status_text(); print(msg); return msg
    if cmd in ['voice status', 'mic status', 'microphone status']:
        msg = voice_backend_status().as_text(); print(msg); return msg
    if cmd in ['voice background status', 'background voice status', 'voice listener status', 'listening status']:
        msg = background_voice_status_text(); print(msg); return msg
    if cmd in ['voice install help', 'mic install help', 'install voice']:
        msg = voice_install_help(); print(msg); return msg
    if cmd in ['voice', 'voice on', 'start voice', 'start listening', 'talk']:
        res = start_background_voice(handle_command, print_fn=print, speak_ready=True)
        msg = res.get('message', str(res)); print(msg); return msg
    if cmd in ['voice off', 'stop voice', 'stop listening', 'listening off', 'microphone off']:
        res = stop_background_voice()
        msg = res.get('message', str(res)); print(msg); return msg
    if cmd in ['voice session', 'manual voice', 'blocking voice'] and not from_voice:
        voice_session(lambda c, from_voice=False: handle_command(c, from_voice=from_voice, normalized=False)); return 'Voice session stopped.'
    if cmd in ['stop speaking', 'interrupt', 'silence', 'be quiet', 'quiet']:
        interrupt_speech(); return 'Speech interrupted.'
    if cmd in ['orb', 'floating orb']:
        orb.start(); orb.update('ready', 'Floating orb active'); return 'Floating orb active.'
    if cmd in ['live chart ocr', 'ocr help']:
        msg = live_chart_ocr_hint(); print(msg); speak(msg); return msg
    if cmd.startswith('detect chart'):
        path = cmd.replace('detect chart','').strip().strip('\"')
        if not path: path = input('Enter chart image path: ').strip().strip('\"')
        msg = detect_chart_visuals(path); print(msg); speak(msg); return msg
    if cmd in ['management help', 'trade management']:
        msg = management_help(); print(msg); return msg
    if cmd in ['llm help', 'ai brain']:
        msg = llm_help(); print(msg); return msg
    if cmd.startswith('remember '):
        body = cmd.replace('remember ', '', 1)
        if ' is ' in body:
            k, v = body.split(' is ', 1); save_preference(k.strip(), v.strip()); msg='Preference saved.'
        else: msg='Use: remember risk style is conservative'
        print(msg); return msg
    if cmd in ['memory', 'preferences']:
        msg = preference_summary(); print(msg); return msg
    if cmd.startswith('scan market') or cmd == 'scanner':
        results = scan_market(); print_scan(results); return 'Market scan complete.'
    if cmd.startswith('autonomous') or cmd.startswith('assistant mode') or cmd in ['autonomous all pairs', 'autonomous all', 'monitor all pairs', 'watch all pairs']:
        symbol = cmd.replace('autonomous','').replace('assistant mode','').replace('monitor','').replace('watch','').strip() or 'gold'
        if symbol in ['all pairs', 'all market', 'all markets', 'all']:
            symbol = 'all'
        return autonomous_watch(symbol, minutes=1, scans=3)
    return scan_one(cmd, from_voice=from_voice)



# Phase 15.18 — Parallel Voice + Text command runner.
# The background voice thread and the terminal text loop can both call handle_command.
# This wrapper serializes execution so commands do not fight over MT5/order management.
_COMMAND_EXECUTION_LOCK = threading.RLock()
_ORIGINAL_HANDLE_COMMAND = handle_command


def _voice_prompt_guard(raw_cmd: str) -> str:
    """Return a safe message for voice commands that would otherwise call input().

    Background voice must never call input(), because the main thread is already
    waiting at `Blue >`. These commands still work from typed terminal input.
    """
    t = (raw_cmd or "").strip().lower()
    if not t:
        return ""

    # Prevent accidental manual order punching from voice. Analysis commands like
    # "gold buy or sell" still work because they do not start with buy/sell.
    if re.match(r"^(buy|sell|place|execute)\b", t):
        return (
            "For safety, I will not place manual buy or sell orders from voice. "
            "Say 'gold buy or sell' for analysis, or type a full manual execution command in the terminal."
        )

    # These commands normally ask for balance/risk/entry/SL via input().
    if (t.startswith("lot ") or "mt5 lot" in t or "broker lot" in t or "exact lot" in t):
        return (
            "Lot size needs balance, risk, entry, and stop loss. "
            "Type this command in the terminal so Blue can ask safely."
        )

    # Screenshot/image commands without a path would ask for a path via input().
    screenshot_starts = ("screenshot", "image", "analyze image", "analyse image", "analyze screenshot", "analyse screenshot")
    if t.startswith(screenshot_starts):
        has_path = len(t.split()) > 2 or any(x in t for x in [".png", ".jpg", ".jpeg", ".webp", ".bmp", ":\\", "/"])
        if not has_path:
            return "For screenshot analysis by voice, include the image path, or type screenshot in the terminal."

    # Ticket-based journal edit commands can request a ticket number.
    if t in {"close trade", "update trade", "modify trade", "modify position"}:
        return "This command needs a ticket/position detail. Please type it in the terminal."

    return ""


def handle_command(cmd, from_voice=False, normalized=False):
    raw_cmd = (cmd or "").strip()
    if not raw_cmd:
        return ""
    if from_voice:
        guarded = _voice_prompt_guard(raw_cmd)
        if guarded:
            print(guarded)
            return guarded
    with _COMMAND_EXECUTION_LOCK:
        return _ORIGINAL_HANDLE_COMMAND(raw_cmd, from_voice=from_voice, normalized=normalized)

def main():
    print('\n' + '=' * 78)
    print(f'{APP_NAME} v{VERSION} — PHASE 16'.center(78))
    print('COGNITIVE ARCHITECTURE AUTO BRAIN'.center(78))
    print('=' * 78)
    print('Starting automatic services...')
    try:
        heal_res = run_startup_self_heal(verbose=False)
        print('Self-Healing Doctor:', heal_res.get('message', heal_res))
        for fix in heal_res.get('fixed', [])[:5]:
            print('FIX -', fix)
        for warning in heal_res.get('warnings', [])[:3]:
            print('WARN-', warning)
    except Exception as heal_exc:
        print(explain_exception(heal_exc, where='startup self-healing'))
    try:
        auto_res = start_full_auto_mode(print_fn=print, command_handler=handle_command)
        print('\nAUTO CORE')
        print('-' * 78)
        print(auto_res.get('message', auto_res))
        for line in auto_res.get('results', []):
            print('OK  -', line)
        for warning in auto_res.get('warnings', []):
            print('WARN-', warning)
    except Exception as exc:
        print('\nAUTO CORE')
        print('-' * 78)
        print('Skipped:', exc)
        try:
            bg_res = start_background_learning_service(print_fn=print)
            print('Background learning:', bg_res.get('message', bg_res))
        except Exception as bg_exc:
            print('Background learning skipped:', bg_exc)
    print('\nREADY')
    print('-' * 78)
    print('Text terminal: ON | Natural intent: ON | Cognitive + CME brain: ON | Voice: command only')
    print('You can type normally: "what is gold doing", "protect my gold trade", "best trade"')
    print('Old commands also work: gold | eurusd | btc | best | scan | why | broker | exit')
    print('Safety: MT5 must be open. Orders still pass risk filters + Order Punch Shield.')
    print('=' * 78)
    try:
        while True:
            try:
                cmd = input('Blue > ').strip()
                handle_command(cmd)
            except SystemExit:
                break
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(explain_exception(e, where='terminal command'))
    finally:
        try:
            stop_full_auto_mode(disable_autostart=False)
        except Exception:
            try:
                stop_background_voice()
            except Exception:
                pass
            try:
                stop_background_learning_service()
            except Exception:
                pass

if __name__ == '__main__':
    main()

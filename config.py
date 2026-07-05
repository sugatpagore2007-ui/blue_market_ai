APP_NAME = "Blue Forex Market AI Phase 15.23 — Smart Autopilot Session Guard"
VERSION = 'v16.3-background-autopilot-trade-events'

SYMBOLS = {
    "gold": "GC=F", "xauusd": "GC=F", "xau/usd": "GC=F", "xau": "GC=F",
    "eurusd": "EURUSD=X", "eur/usd": "EURUSD=X",
    "gbpusd": "GBPUSD=X", "gbp/usd": "GBPUSD=X",
    "usdjpy": "JPY=X", "usd/jpy": "JPY=X",
    "btc": "BTC-USD", "btcusd": "BTC-USD", "btc/usd": "BTC-USD",
    "eth": "ETH-USD", "ethusd": "ETH-USD", "eth/usd": "ETH-USD",
    "usoil": "CL=F", "oil": "CL=F", "crude": "CL=F",
    "ustec": "NQ=F", "nasdaq": "NQ=F", "nas100": "NQ=F", "us100": "NQ=F", "spx": "ES=F", "us500": "ES=F",
    "silver": "SI=F", "xagusd": "SI=F",
    "dxy": "DX-Y.NYB",
}

# Phase 15.22 watchlist classification.
# Major list is the focused default universe for scanner/autopilot.
# Other supported symbols remain available by text/voice command as minor/additional markets.
MAJOR_WATCHLIST_SYMBOLS = [
    "xauusd", "xagusd", "ethusd", "btcusd", "usoil",
    "usdjpy", "eurusd", "ustec", "gbpusd",
]
MINOR_ADDITIONAL_SYMBOLS = [
    "gold", "silver", "btc", "eth", "nasdaq", "nas100", "us100",
    "spx", "us500", "dxy", "xau", "xag", "oil",
]

TIMEFRAMES = {
    "5m":  {"interval": "5m",  "period": "5d",   "role": "entry timing"},
    "15m": {"interval": "15m", "period": "10d",  "role": "confirmation"},
    "1h":  {"interval": "1h",  "period": "60d",  "role": "market direction"},
    "4h":  {"interval": "1h",  "period": "120d", "role": "major structure proxy"},
    "1d":  {"interval": "1d",  "period": "1y",   "role": "macro bias"},
}

SMT_PAIRS = {
    "GC=F": "SI=F",          # Gold vs Silver
    "SI=F": "GC=F",
    "BTC-USD": "ETH-USD",   # BTC vs ETH
    "ETH-USD": "BTC-USD",
    "EURUSD=X": "DX-Y.NYB", # EURUSD vs DXY inverse relationship
    "GBPUSD=X": "DX-Y.NYB",
    "NQ=F": "ES=F",         # Nasdaq vs SPX
    "ES=F": "NQ=F",
}

LOT_SPECS = {
    "GC=F":      {"asset": "XAUUSD / Gold", "contract_size": 100.0,    "lot_step": 0.01, "min_lot": 0.01, "max_lot": 100.0, "unit_name": "oz"},
    "SI=F":      {"asset": "XAGUSD / Silver","contract_size": 5000.0,   "lot_step": 0.01, "min_lot": 0.01, "max_lot": 100.0, "unit_name": "oz"},
    "EURUSD=X":  {"asset": "EURUSD",        "contract_size": 100000.0, "lot_step": 0.01, "min_lot": 0.01, "max_lot": 100.0, "unit_name": "EUR"},
    "GBPUSD=X":  {"asset": "GBPUSD",        "contract_size": 100000.0, "lot_step": 0.01, "min_lot": 0.01, "max_lot": 100.0, "unit_name": "GBP"},
    "JPY=X":     {"asset": "USDJPY",        "contract_size": 100000.0, "lot_step": 0.01, "min_lot": 0.01, "max_lot": 100.0, "unit_name": "USD"},
    "BTC-USD":   {"asset": "BTCUSD",        "contract_size": 1.0,      "lot_step": 0.001,"min_lot": 0.001,"max_lot": 100.0, "unit_name": "BTC"},
    "ETH-USD":   {"asset": "ETHUSD",        "contract_size": 1.0,      "lot_step": 0.01, "min_lot": 0.01, "max_lot": 1000.0,"unit_name": "ETH"},
    "CL=F":      {"asset": "USOIL / WTI",   "contract_size": 1000.0,   "lot_step": 0.01, "min_lot": 0.01, "max_lot": 100.0, "unit_name": "barrels"},
    "NQ=F":      {"asset": "NASDAQ",        "contract_size": 20.0,     "lot_step": 0.01, "min_lot": 0.01, "max_lot": 100.0, "unit_name": "index units"},
    "ES=F":      {"asset": "S&P 500",       "contract_size": 50.0,     "lot_step": 0.01, "min_lot": 0.01, "max_lot": 100.0, "unit_name": "index units"},
}

ACCOUNT_FILE = "account_settings.json"
DATABASE_FILE = "blue_market_ai.db"
MIN_CONFIDENCE_FOR_ACTION = 80
MAX_RISK_PERCENT = 2.0
DEFAULT_RISK_PERCENT = 1.0
DEFAULT_ATR_MULTIPLIER = 1.25
SWING_LOOKBACK = 3
FVG_LOOKBACK_BARS = 85
OB_LOOKBACK_BARS = 80
LIQUIDITY_LOOKBACK_BARS = 120
PREMIUM_DISCOUNT_LOOKBACK = 160

# Forex Factory scraping can break when the website changes. The engine fails safe.
FOREX_FACTORY_URL = "https://www.forexfactory.com/calendar"
NEWS_LOOKAHEAD_HOURS = 8


# Trade style profiles
# Default is INTRADAY. Blue will only use Swing / Position / Scalping when the command says it.
TRADE_STYLE_PROFILES = {
    "intraday": {
        "label": "Intraday",
        "entry_tf": "5m",
        "decision_weights": {"5m": 2.2, "15m": 2.0, "1h": 2.0, "4h": 1.2, "1d": 0.6},
        "atr_multiplier": 1.15,
        "target_1_r": 1.5,
        "target_2_r": 2.5,
        "note": "Default mode: scans all available markets/timeframes, but final execution entry is planned from the 5-minute chart."
    },
    "scalping": {
        "label": "Scalping",
        "entry_tf": "5m",
        "decision_weights": {"5m": 3.0, "15m": 2.2, "1h": 1.0, "4h": 0.4, "1d": 0.2},
        "atr_multiplier": 0.9,
        "target_1_r": 1.0,
        "target_2_r": 1.8,
        "note": "Scalping mode: faster 5-minute execution with tighter targets; use only when you specifically ask for scalping."
    },
    "swing": {
        "label": "Swing Trading",
        "entry_tf": "1h",
        "decision_weights": {"5m": 0.4, "15m": 0.8, "1h": 2.0, "4h": 2.8, "1d": 2.5},
        "atr_multiplier": 1.8,
        "target_1_r": 2.0,
        "target_2_r": 3.5,
        "note": "Swing mode: higher-timeframe idea with 1-hour execution; only active when command says swing trading."
    },
    "position": {
        "label": "Position Trading",
        "entry_tf": "4h",
        "decision_weights": {"5m": 0.1, "15m": 0.3, "1h": 1.0, "4h": 2.5, "1d": 3.5},
        "atr_multiplier": 2.2,
        "target_1_r": 2.5,
        "target_2_r": 5.0,
        "note": "Position mode: macro style using 4H execution and daily bias; only active when command says position trading."
    },
}
DEFAULT_TRADE_STYLE = "intraday"


# MT5 terminal-only integration settings
# Blue will NOT open or pop up the MT5 terminal from code.
# Keep your MT5 terminal already running and logged in, then use connect mt5.
MT5_ENABLED = True
MT5_AUTO_LAUNCH = False
MT5_DEFAULT_DEVIATION = 20
MT5_MAGIC_NUMBER = 260530
MT5_COMMENT = "BlueMarketAI"
MT5_STAGE2_EXECUTION_ENABLED = True  # Phase 15.10: demo execution enabled; real-account execution remains blocked

# Prevent MT5/Exness window from popping to front repeatedly.
# Blue caches the MT5 connection and reuses it instead of calling initialize() every scan.
MT5_SUPPRESS_WINDOW_POPUPS = True
MT5_MINIMIZE_AFTER_CONNECT = True
MT5_REUSE_EXISTING_CONNECTION = True

# Your Exness demo symbols usually end with "m" like XAUUSDm, EURUSDm, BTCUSDm.
# Change MT5_SYMBOL_SUFFIX to "" if your broker uses normal symbols like XAUUSD.
MT5_SYMBOL_SUFFIX = "m"

MT5_SYMBOL_MAP = {
    "GC=F": "XAUUSDm",
    "SI=F": "XAGUSDm",
    "EURUSD=X": "EURUSDm",
    "GBPUSD=X": "GBPUSDm",
    "JPY=X": "USDJPYm",
    "BTC-USD": "BTCUSDm",
    "ETH-USD": "ETHUSDm",
    "CL=F": "USOILm",
    "NQ=F": "NAS100m",
    "ES=F": "US500m",
    "DX-Y.NYB": "DXYm",
}

# Extra fallback names Blue will try automatically before giving up.
# This fixes brokers that use suffix/prefix symbols such as XAUUSDm, xauusdm, GOLDm, BTCUSDm.
MT5_SYMBOL_ALIASES = {
    "XAUUSD": ["XAUUSDm", "xauusdm", "XAUUSD", "GOLD", "GOLDm"],
    "XAGUSD": ["XAGUSDm", "xagusdm", "XAGUSD", "SILVER", "SILVERm"],
    "EURUSD": ["EURUSDm", "eurusdm", "EURUSD"],
    "GBPUSD": ["GBPUSDm", "gbpusdm", "GBPUSD"],
    "USDJPY": ["USDJPYm", "usdj pym".replace(" ", ""), "USDJPY"],
    "BTCUSD": ["BTCUSDm", "btcusdm", "BTCUSD", "BTC-USD"],
    "ETHUSD": ["ETHUSDm", "ethusdm", "ETHUSD", "ETH-USD"],
    "USOIL": ["USOILm", "usoilm", "USOIL", "WTI", "WTIm"],
    "NAS100": ["NAS100m", "nas100m", "NAS100", "USTEC", "USTECm", "US100m", "US100", "USTEC.cash", "NAS100.cash", "US100.cash", "USTEC.pro", "NAS100.pro", "US100.pro"],
    "US500": ["US500m", "us500m", "US500", "SPX500", "SPX500m", "SP500", "SP500m", "SPX", "SPXm", "US500.cash", "SPX500.cash"],
    "DXY": ["DXYm", "dxym", "DXY"],
}

# Auto execution guardrails
# Auto execution is terminal-only and will never open MT5 from code.
# Keep DEMO_ONLY True unless you fully understand the risk and have tested heavily.
AUTO_ORDER_EXECUTION = True
MIN_AUTO_TRADE_CONFIDENCE = 80
AUTO_TRADE_DEMO_ONLY = True
AUTO_TRADE_ALLOW_REAL_ACCOUNT = False
AUTO_TRADE_RISK_PERCENT = 1.0
MAX_AUTO_TRADES_PER_DAY = 2
MAX_DAILY_LOSS_PERCENT = 2.0
MAX_SPREAD_POINTS = 80
AUTO_TRADE_USE_TP = "target_1"  # target_1 or target_2

# Auto trade manager settings
# Manager works terminal-only through MT5. It never opens MT5 from code.
AUTO_MANAGER_ENABLED = True
AUTO_MANAGER_DEMO_ONLY = True
AUTO_MANAGER_ALLOW_REAL_ACCOUNT = False
AUTO_MANAGER_CHECK_SECONDS = 60
AUTO_MANAGER_BREAKEVEN_AT_R = 1.0
AUTO_MANAGER_PARTIAL_CLOSE_AT_TP1 = True
AUTO_MANAGER_PARTIAL_CLOSE_PERCENT = 50.0
AUTO_MANAGER_TRAIL_AFTER_TP1 = True
AUTO_MANAGER_TRAIL_LOCK_R = 0.5
AUTO_MANAGER_CLOSE_ON_OPPOSITE_SIGNAL = True
AUTO_MANAGER_MANAGE_ONLY_BLUE_TRADES = True
AUTO_TRADE_PLANS_FILE = "auto_trade_plans.json"

# For auto manager, auto orders use TP2 so TP1 can be used for partial close.
AUTO_TRADE_USE_TP = "target_2"

# Phase 7.6.5: asset-specific spread limits. Gold/crypto/indices naturally have
# larger point spreads than EURUSD/GBPUSD, so a single 80-point limit blocks XAUUSDm.
MAX_SPREAD_POINTS_BY_SYMBOL = {
    "XAUUSD": 450, "XAUUSDm": 450, "GOLD": 450, "GOLDm": 450,
    "XAGUSD": 250, "XAGUSDm": 250,
    "EURUSD": 80, "EURUSDm": 80,
    "GBPUSD": 90, "GBPUSDm": 90,
    "USDJPY": 90, "USDJPYm": 90,
    "BTCUSD": 50000, "BTCUSDm": 50000,
    "ETHUSD": 8000, "ETHUSDm": 8000,
    "USOIL": 250, "USOILm": 250,
    "NAS100": 800, "NAS100m": 800,
    "US500": 300, "US500m": 300,
}

# Do not open or focus MT5 windows. Blue only attaches to an already-open terminal.
MT5_AUTO_LAUNCH = False
MT5_SUPPRESS_WINDOW_POPUPS = True
MT5_MINIMIZE_AFTER_CONNECT = True
MT5_REUSE_EXISTING_CONNECTION = True

# Controlled pyramiding / scale-in settings
# Blue adds only while trade is already winning and protected. It will NOT chase price
# too far from the original entry. These settings are intentionally conservative.
PYRAMIDING_ENABLED = True
PYRAMID_MAX_LEVELS = 2
PYRAMID_ADD_AT_R = [1.0, 1.5]          # add level 1 at +1R, level 2 at +1.5R
PYRAMID_LOT_MULTIPLIERS = [0.50, 0.25] # added lot = current/base lot * multiplier
PYRAMID_MAX_DISTANCE_FROM_ORIGINAL_R = 2.0  # block if price moved more than 2R from original entry
PYRAMID_MIN_CONFIDENCE = 85
PYRAMID_REQUIRE_BREAKEVEN = True
PYRAMID_COOLDOWN_SECONDS = 300
PYRAMID_USE_EXISTING_TP = True
PYRAMID_COMMENT_SUFFIX = " PYRAMID"


# Phase 8.3: Autopilot best-trade-only filter
# When autopilot scans all pairs, it will NOT enter every valid signal.
# It ranks all pairs and executes only the single strongest A+ setup per cycle.
AUTOPILOT_ONLY_BEST_TRADE = True
AUTOPILOT_MIN_SETUP_GRADE = "A"
AUTOPILOT_MAX_NEW_TRADES_PER_CYCLE = 1
AUTOPILOT_REQUIRE_ACTIONABLE_SIGNAL = True

# Phase 15.9 — Autopilot signal display hotfix
# Blue now separates market signal direction from autopilot execution permission.
# If strict filters block execution, terminal will show SIGNAL BUY/SELL + AUTO WAIT/BLOCK
# instead of looking like the whole analysis is only WAIT.
AUTOPILOT_SHOW_SIGNAL_WHEN_BLOCKED = True
AUTOPILOT_SHOW_BLOCK_REASON = True
AUTOPILOT_EXECUTION_STAYS_STRICT = True

# Phase 8.4 order execution fix: count only entry deals, not partial closes/SLTP exits.
AUTO_TRADE_COUNT_ENTRY_DEALS_ONLY = True
ORDER_SEND_RETRY_ON_PRICE_CHANGE = True
ORDER_SEND_EXTRA_DEVIATION = 50


# Phase 8.5 — Broker Adapter Layer
# Forex/CFD Blue remains separate from Indian Market Blue.
# This adapter lets the same Forex/CFD Blue connect to other MT5 brokers such as Exness, XM, IC Markets, etc.
# Use terminal commands: broker status | broker set auto | broker set exness | broker set xm | broker set generic_mt5
BROKER_PLATFORM = "mt5"          # mt5 now; ctrader scaffold exists but real cTrader execution needs Open API implementation
BROKER_PROFILE = "auto"          # auto, exness, xm, icmarkets, generic_mt5, ctrader
BROKER_SETTINGS_FILE = "broker_settings.json"


# Phase 9 — Intelligence / Accuracy / Advanced Hybrid ML
PHASE9_INTELLIGENCE_ENABLED = True
PHASE9_HYBRID_ML_ENABLED = True
PHASE9_ML_MIN_LABELED_TRADES = 40
PHASE9_ML_STACK = ["RandomForest", "XGBoost", "LightGBM", "CatBoost"]
PHASE9_AUTOPILOT_REQUIRE_A_PLUS_FILTER = True
PHASE9_MIN_ML_FINAL_SCORE = 75
PHASE9_MIN_AGENT_VOTES = 5
PHASE9_PORTFOLIO_MAX_BLUE_PLANS = 5

# Phase 9.2 safety: advanced ML libraries are optional so Python 3.14 install does not break.
PHASE9_OPTIONAL_ML_LIBS = True


# Phase 10: Human Trader Brain settings
# These settings make Blue behave more like a disciplined human trader:
# it reads market context, uses a decision pipeline, remembers trade outcomes,
# blocks weak/noisy trades, checks macro/news risk, adapts broker symbols, and
# switches personality modes. Keep learning/demo mode for testing.
DEFAULT_TRADER_PERSONALITY_MODE = "balanced"  # conservative / balanced / aggressive / learning
TRADER_PERSONALITY_MODES = {
    "conservative": {
        "label": "Conservative Human Trader",
        "min_confidence": 90,
        "min_rr_to_tp2": 1.8,
        "max_context_risk_flags": 1,
        "block_choppy_market": True,
        "block_news": True,
        "allow_autopilot": True,
        "risk_multiplier": 0.50,
        "description": "A+ setups only. Skips choppy markets and high-impact news. Best for live/demo safety."
    },
    "balanced": {
        "label": "Balanced Human Trader",
        "min_confidence": 80,
        "min_rr_to_tp2": 1.5,
        "max_context_risk_flags": 2,
        "block_choppy_market": False,
        "block_news": False,
        "allow_autopilot": True,
        "risk_multiplier": 1.00,
        "description": "Default working demo mode. News is shown as a warning, but demo autopilot can still test execution when other guards pass."
    },
    "aggressive": {
        "label": "Aggressive Human Trader",
        "min_confidence": 78,
        "min_rr_to_tp2": 1.25,
        "max_context_risk_flags": 3,
        "block_choppy_market": False,
        "block_news": False,
        "allow_autopilot": False,
        "risk_multiplier": 0.50,
        "description": "More signals, but autopilot is disabled by default. Use mainly for research/testing."
    },
    "learning": {
        "label": "Learning / Paper Trader",
        "min_confidence": 70,
        "min_rr_to_tp2": 1.0,
        "max_context_risk_flags": 99,
        "block_choppy_market": False,
        "block_news": False,
        "allow_autopilot": False,
        "risk_multiplier": 0.00,
        "description": "Paper-trading mode. Blue records and learns but should not live execute."
    },
}

HUMAN_BRAIN_NO_TRADE_RULES = {
    "max_spread_warning_points": 80,
    "minimum_timeframe_alignment": 0.55,
    "minimum_context_score": 55,
    "block_if_stop_loss_zero": True,
    "block_if_rr_invalid": True,
    "prefer_no_trade_after_daily_loss_limit": True,
}

MACRO_BRAIN_CONFIG = {
    "high_impact_keywords": [
        "CPI", "PPI", "NFP", "Non-Farm", "FOMC", "Interest Rate", "Powell", "GDP",
        "Unemployment", "Retail Sales", "PMI", "ECB", "BOE", "BOJ", "Fed"
    ],
    "usd_sensitive": ["GC=F", "SI=F", "EURUSD=X", "GBPUSD=X", "JPY=X", "BTC-USD", "ETH-USD", "NQ=F", "ES=F"],
    "manual_calendar_note": "Always check the live economic calendar before live trading; web calendars can change or block scraping.",
}

TRADE_MEMORY_MIN_SAMPLE = 5
TRADE_MEMORY_CONFIDENCE_STEP = 4


# Phase 11: user dataset ML learning
DATASET_ML_ENABLED = True
DATASET_ML_MIN_ROWS = 20
DATASET_ML_LOW_PROB_BLOCK = 45
DATASET_ML_CONFIDENCE_BLEND = 0.35


# Phase 15 — Automatic History Learning
# Reads closed demo/MT5/backtest trades and converts them into ML training rows.
# Safe by default: learning can approve/block signals, but it never places trades alone.
PHASE15_AUTO_HISTORY_LEARNING_ENABLED = True
PHASE15_AUTO_RETRAIN_ENABLED = True
PHASE15_AUTO_RETRAIN_AFTER_NEW_ROWS = 25
PHASE15_DEFAULT_HISTORY_DAYS = 30
PHASE15_DEFAULT_HISTORY_TIMEFRAME = "5m"
PHASE15_DATASET_DIR = "datasets"
PHASE15_REPORTS_DIR = "reports"
PHASE15_MIN_CLOSED_TRADES_TO_IMPORT = 5
PHASE15_LEARNING_CAN_BLOCK_TRADES = True
PHASE15_LEARNING_CAN_PLACE_TRADES = False


# Phase 15.1 — Startup Auto Learning
# When True, Blue checks learning sources automatically every time you run main.py.
# It is read-only: imports closed history/backtest/journal rows and retrains ML; it never places trades.
PHASE15_STARTUP_AUTO_LEARN_ENABLED = True
PHASE15_STARTUP_LEARN_JOURNAL = True
PHASE15_STARTUP_LEARN_MT5 = True
PHASE15_STARTUP_LEARN_BACKTEST_REPORTS = True
PHASE15_STARTUP_MT5_HISTORY_DAYS = 30
PHASE15_STARTUP_HISTORY_TIMEFRAME = "5m"
PHASE15_STARTUP_BACKTEST_GLOBS = ["reports/*.csv", "reports/auto_learn/*.csv"]

# Phase 15.2: background auto-learning service
# When Blue starts, this launches a daemon worker so the terminal remains usable.
# It checks for new closed journal/MT5/backtest trades, imports only unseen rows,
# and retrains only when the Phase 15 threshold is reached. It never places trades.
PHASE15_BACKGROUND_AUTO_LEARN_ENABLED = True
PHASE15_BACKGROUND_LEARN_ON_START = True
PHASE15_BACKGROUND_START_DELAY_SECONDS = 2
PHASE15_BACKGROUND_INTERVAL_SECONDS = 300  # minimum enforced by code: 60 seconds
PHASE15_BACKGROUND_PRINT_UPDATES = False   # True = print when new rows are learned
PHASE15_BACKGROUND_STATUS_FILE = "phase15_background_learning_status.json"


# Phase 15.10 — Demo Autopilot Working Mode
# Goal: make demo autopilot actually send orders when signal + core guardrails pass.
# It is still demo-only by default and real-account auto execution remains blocked.
PHASE15_10_DEMO_AUTOPILOT_WORKING_MODE = True
PHASE15_10_NEWS_AS_WARNING_ONLY = True
PHASE15_10_MIN_AUTOPILOT_GRADE = "A"
PHASE15_10_MIN_AUTOPILOT_CONFIDENCE = 80
PHASE15_10_SHOW_EXECUTION_DIAGNOSTICS = True
PHASE15_10_REAL_ACCOUNT_AUTO_EXECUTION_LOCK = True


# Phase 15.11 — Autopilot symbol fallback hotfix
PHASE15_11_AUTOPILOT_SYMBOL_FALLBACK = True
PHASE15_11_TRY_NEXT_CANDIDATE_IF_ORDER_SKIPPED = True


# Phase 15.12 — Autopilot execution reliability fix
# Keep this DEMO ONLY. Blue treats broker servers containing demo/trial as demo accounts.
PHASE15_12_EXECUTION_FIX_ENABLED = True
AUTO_TRADE_DEMO_SERVER_KEYWORDS = ["demo", "trial", "practice"]
AUTOPILOT_SKIP_UNAVAILABLE_SYMBOLS = True
AUTOPILOT_PREFER_FOREX_CRYPTO_SYMBOLS = True
AUTOPILOT_TRY_ALL_ELIGIBLE_CANDIDATES = True

# Phase 15.13 — show full reason/basis before autopilot tries an order.
AUTOPILOT_SHOW_TRADE_BASIS = True
# Keep False by default to avoid huge output for every scanned symbol. Set True if you
# want a reason card for every BUY/SELL signal, not only the selected candidate.
AUTOPILOT_SHOW_BASIS_FOR_ALL_SIGNALS = False
AUTOPILOT_SEND_WITHOUT_SLTP_IF_BROKER_REJECTS_STOPS = True
AUTOPILOT_ATTACH_SLTP_AFTER_ENTRY = True
# Default autopilot list keeps the most common Exness demo symbols first.
AUTOPILOT_DEFAULT_SYMBOLS = list(MAJOR_WATCHLIST_SYMBOLS)

# Phase 15.16 — Internet / Environment Learning Brain
# Blue can learn market context from trusted public internet/RSS sources.
# Safe rule: internet memory is context only. It cannot place trades or bypass autopilot/MT5 guardrails.
PHASE15_16_INTERNET_LEARNING_ENABLED = True
PHASE15_16_INTERNET_BACKGROUND_LEARN_ENABLED = True   # Phase 15.17: auto background internet learning on startup
PHASE15_16_INTERNET_MIN_HOURS_BETWEEN_RUNS = 6
PHASE15_16_INTERNET_MAX_ITEMS_PER_SOURCE = 8
PHASE15_16_INTERNET_REQUEST_TIMEOUT_SECONDS = 12
PHASE15_16_INTERNET_ALLOW_UNTRUSTED_SOURCES = False


# Phase 15.17 — Auto Everything + Text Command Mode
# Blue starts the important background systems automatically when you run python main.py,
# while still keeping text commands as manual controls/overrides.
BLUE_AUTO_CORE_ENABLED = True
BLUE_AUTO_START_BACKGROUND_LEARNING = True
BLUE_AUTO_ENABLE_INTERNET_LEARNING = True
BLUE_AUTO_START_AUTOPILOT = True
BLUE_AUTO_START_VOICE_LISTENER = False  # Voice starts only when user types: voice
BLUE_AUTO_SCAN_SECONDS = 300
BLUE_AUTO_STATUS_FILE = "phase15_18_parallel_voice_text_state.json"
BLUE_AUTO_BASIC_COMMANDS_ONLY_NOTE = True

# Extra safety for automatic mode. This build is intentionally demo-only by default.
# Keep these values unless you have tested heavily on demo.
BLUE_AUTO_FORCE_DEMO_ONLY = True
BLUE_AUTO_NEVER_LAUNCH_MT5 = True
BLUE_AUTO_TEXT_COMMANDS_STAY_ENABLED = True

# Phase 15.18 — Parallel Voice + Text Command Mode
# Voice listener runs in a background thread, while typed terminal commands remain active.
# Command execution is serialized with a lock so voice + text cannot fight over MT5 at the same time.
BLUE_PARALLEL_VOICE_TEXT_ENABLED = True
BLUE_VOICE_TEXT_COMMANDS_KEEP_EXISTING_NAMES = True
BLUE_VOICE_BLOCKS_PROMPT_ONLY_COMMANDS = True


# Phase 15.19 — Neural Network Brain + Order Punch Shield
# Neural brain is advisory: it confirms/reduces/blocks weak setups, but never forces live orders.
# Best model: CNN + BiLSTM + Attention when TensorFlow/Keras is installed.
# Fallback model: sklearn MLP if TensorFlow is unavailable, so Blue still runs on normal PCs.
PHASE15_19_NEURAL_NETWORK_ENABLED = True
PHASE15_19_NEURAL_NETWORK_BACKGROUND_ENABLED = True
PHASE15_19_NEURAL_MIN_HOURS_BETWEEN_TRAINING = 12
PHASE15_19_NEURAL_CONFIDENCE_BLEND_WEIGHT = 0.30
PHASE15_19_NEURAL_LOW_PROB_BLOCK_THRESHOLD = 42.0
PHASE15_19_NEURAL_MIN_ROWS_TO_TRAIN = 40
PHASE15_19_NEURAL_MODEL_DIR = "models"
PHASE15_19_NEURAL_KERAS_MODEL_FILE = "models/blue_cnn_bilstm_attention.keras"
PHASE15_19_NEURAL_FALLBACK_MODEL_FILE = "models/blue_neural_mlp_fallback.joblib"
PHASE15_19_NEURAL_META_FILE = "models/blue_neural_network_brain_meta.json"
PHASE15_19_NEURAL_STATE_FILE = "phase15_19_neural_network_state.json"
PHASE15_19_NEURAL_USE_TENSORFLOW_IF_AVAILABLE = True
PHASE15_19_NEURAL_SEQUENCE_LENGTH = 24
PHASE15_19_NEURAL_EPOCHS = 35
PHASE15_19_NEURAL_BATCH_SIZE = 32
PHASE15_19_NEURAL_PATIENCE = 6

# Order Punch Shield: fail loudly before order_send instead of silently not punching.
# This cannot fix broker outages/closed markets, but it removes common code-side execution mistakes.
ORDER_PUNCH_SHIELD_ENABLED = True
ORDER_SEND_ONLY_IF_ORDER_CHECK_OK = True
ORDER_PUNCH_SHIELD_REFRESH_TICK_BEFORE_SEND = True
ORDER_PUNCH_SHIELD_SHOW_PRECHECK_IN_RESULT = True
ORDER_PUNCH_SHIELD_FAILOVER_TO_NO_SLTP = True


# Phase 15.22 session trade quota
PHASE15_22_SESSION_QUOTA_ENABLED = True
PHASE15_22_MAX_DAILY_TRADES = 2
PHASE15_22_LONDON_TRADES = 1
PHASE15_22_NEW_YORK_TRADES = 1
PHASE15_22_ROLL_LONDON_UNUSED_TO_NY = True


# Phase 15.23 — Smart Autopilot Relaxation + 2-Trade Session Guard
# Keeps confidence strict (80+) but stops soft warnings from blocking A/A+ setups.
PHASE15_23_SMART_AUTOPILOT_RELAXATION_ENABLED = True
PHASE15_23_MIN_AUTOPILOT_CONFIDENCE = 80
PHASE15_23_STRONG_SETUP_ML_MIN = 75
PHASE15_23_SOFT_WARNINGS_DO_NOT_BLOCK_A_SETUP = True
PHASE15_23_VOICE_STARTS_ONLY_ON_COMMAND = True


# Phase 16.2 — Autonomous Evolution Engine
PHASE16_2_AUTONOMOUS_EVOLUTION_ENABLED = True
PHASE16_2_AUTOPILOT_SCAN_SECONDS = 300  # 5 minutes
PHASE16_2_MONDAY_REPORT_ENABLED = True
PHASE16_2_AUTOPILOT_EVOLUTION_PULSE = True

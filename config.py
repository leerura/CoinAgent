# Trading pair
SYMBOL: str = "KRW-BTC"

# RSI indicator
RSI_PERIOD: int = 14
RSI_OVERSOLD: float = 40.0    # BUY signal: RSI crosses above this threshold
RSI_OVERBOUGHT: float = 60.0  # SELL signal: RSI crosses below this threshold

# EMA trend filter
EMA_PERIOD: int = 200

# Risk management
STOP_LOSS: float = -0.02      # Force-sell at -2% from avg entry price
TAKE_PROFIT: float = 0.03     # Force-sell at +3% from avg entry price (legacy alias for TAKE_PROFIT_2)
TAKE_PROFIT_1: float = 0.02   # +2% from avg entry → first partial sell (50%)
TAKE_PROFIT_2: float = 0.03   # +3% from avg entry → full exit

# Order sizing
POSITION_SIZE_RATIO: float = 0.20  # 20% of available cash per trade
# POSITION_SIZE_RATIO=0.20 x 2 levels ≈ 36% max deployment.
# ~64% cash reserve is intentional — acts as drawdown buffer. Do not increase without backtesting.

# Pyramid re-entry
# Reduced from 3 → 2 based on backtest analysis.
# Level 3 accounted for 70% of stop-losses with ~49% capital at risk.
# Level 2 cap reduces max deployed capital to ~36%, improving loss symmetry.
MAX_POSITION_LEVELS: int = 2  # Maximum number of pyramid buy levels

# Partial sell
PARTIAL_SELL_RATIO: float = 0.5   # Fraction of BTC to sell at first take-profit

# Fees & balance
FEE_RATE: float = 0.0005         # 0.05% per trade (Upbit KRW market)
INITIAL_CASH: float = 100_000.0  # Virtual starting balance (KRW)

# Loop timing
INTERVAL_SEC: int = 60  # Main loop interval in seconds

# Candle interval for data collection
CANDLE_INTERVAL: str = "minute5"  # 5-minute candles (was "minute1")

# Data collection — must be >= EMA_PERIOD (200 candles for EMA warm-up; RSI_PERIOD+2 is already satisfied)
CANDLE_COUNT: int = 202

# EMA(200) requires exactly 200 candles for first valid value; +2 preserves RSI crossover buffer
assert CANDLE_COUNT >= EMA_PERIOD, "CANDLE_COUNT must be >= EMA_PERIOD (200 candles required for EMA warm-up)"
assert CANDLE_COUNT >= RSI_PERIOD + 2, "CANDLE_COUNT must be >= RSI_PERIOD + 2 (need both rsi and prev_rsi)"
# Trading pair
SYMBOL: str = "KRW-BTC"

# RSI indicator
RSI_PERIOD: int = 14
RSI_OVERSOLD: float = 35.0    # BUY signal: RSI crosses above this threshold
RSI_OVERBOUGHT: float = 65.0  # SELL signal: RSI crosses below this threshold

# EMA trend filter
EMA_PERIOD: int = 200

# Risk management
STOP_LOSS: float = -0.015     # Force-sell at -1.5% from avg entry price
TAKE_PROFIT: float = 0.03     # Force-sell at +3% from avg entry price (legacy alias for TAKE_PROFIT_2)
TAKE_PROFIT_2: float = 0.03   # +3% from avg entry → TP (full exit)

# Order sizing
POSITION_SIZE_RATIO: float = 0.20  # 20% of available cash per trade

# Single-entry strategy: only one position at a time (no pyramid)
MAX_POSITION_LEVELS: int = 1  # Maximum number of position levels

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
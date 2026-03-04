# Trading pair
SYMBOL: str = "KRW-BTC"

# RSI indicator
RSI_PERIOD: int = 14
RSI_OVERSOLD: float = 40.0    # BUY signal: RSI crosses above this threshold
RSI_OVERBOUGHT: float = 60.0  # SELL signal: RSI crosses below this threshold

# EMA trend filter
EMA_PERIOD: int = 200

# Risk management
STOP_LOSS: float = -0.02      # Force-sell at -2% from entry price
TAKE_PROFIT: float = 0.03     # Force-sell at +3% from entry price

# Order sizing
POSITION_SIZE_RATIO: float = 0.20  # 20% of available cash per trade

# Fees & balance
FEE_RATE: float = 0.0005         # 0.05% per trade (Upbit KRW market)
INITIAL_CASH: float = 100_000.0  # Virtual starting balance (KRW)

# Loop timing
INTERVAL_SEC: int = 60  # Main loop interval in seconds

# Data collection — must be >= EMA_PERIOD (200 candles for EMA warm-up; RSI_PERIOD+2 is already satisfied)
CANDLE_COUNT: int = 202

# EMA(200) requires exactly 200 candles for first valid value; +2 preserves RSI crossover buffer
assert CANDLE_COUNT >= EMA_PERIOD, "CANDLE_COUNT must be >= EMA_PERIOD (200 candles required for EMA warm-up)"
assert CANDLE_COUNT >= RSI_PERIOD + 2, "CANDLE_COUNT must be >= RSI_PERIOD + 2 (need both rsi and prev_rsi)"
# Trading pair
SYMBOL: str = "KRW-BTC"

# RSI indicator
RSI_PERIOD: int = 14
RSI_OVERSOLD: float = 30.0    # BUY signal: RSI crosses above this threshold
RSI_OVERBOUGHT: float = 70.0  # SELL signal: RSI crosses below this threshold

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

# Data collection — must be >= RSI_PERIOD + 2 (rsi + prev_rsi both needed)
CANDLE_COUNT: int = 20

# +2: ta library needs RSI_PERIOD+1 for first valid RSI, and one more for prev_rsi (crossover detection)
assert CANDLE_COUNT >= RSI_PERIOD + 2, "CANDLE_COUNT must be >= RSI_PERIOD + 2 (need both rsi and prev_rsi)"
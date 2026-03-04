# backtest/backtest_data_feeder.py
# SRP: loads historical OHLCV data upfront and feeds it sequentially — no trading logic

import time
from datetime import datetime, timedelta

import pyupbit

import config
from core.interfaces import DataCollector
from core.models import CandleData

TICKER = "KRW-BTC"


class BacktestDataFeeder(DataCollector):
    """Implements DataCollector using pre-loaded historical candles.

    All candles for the requested period are fetched at construction time via
    paginated pyupbit.get_ohlcv() calls (max 200 per call).  The feeder then
    replays them one tick at a time, maintaining a sliding-window cursor so
    BacktestRunner can call get_candles(CANDLE_COUNT) identically to how
    TradingAgent calls UpbitDataCollector.get_candles().

    Cursor starts at CANDLE_COUNT so the first window spans candles[0:CANDLE_COUNT],
    giving the IndicatorEngine a full EMA(200) warm-up before any trades occur.
    """

    def __init__(self, start: str, end: str, interval: str = "minute5") -> None:
        self._start_dt: datetime = datetime.strptime(start, "%Y-%m-%d")
        self._end_dt: datetime = datetime.strptime(end, "%Y-%m-%d").replace(
            hour=23, minute=59, second=59
        )
        print(f"[Feeder] Fetching {interval} candles from {start} to {end}…")
        self._candles: list[CandleData] = self._fetch_all(
            self._start_dt, self._end_dt, interval
        )
        print(f"[Feeder] Loaded {len(self._candles):,} candles total.")

        # cursor is the exclusive upper bound of the current window:
        # window = candles[cursor - CANDLE_COUNT : cursor]
        # starts at CANDLE_COUNT so the first window is always fully populated.
        self._cursor: int = config.CANDLE_COUNT

    # ── DataCollector interface ───────────────────────────────────────────────

    def get_candles(self, count: int) -> list[CandleData]:
        """Return the window ending at cursor, then advance cursor by 1."""
        result = self._candles[self._cursor - count : self._cursor]
        self._cursor += 1
        return result

    def has_next(self) -> bool:
        """True while there are untouched candles ahead of the cursor."""
        return self._cursor < len(self._candles)

    # ── Accessors for BacktestRunner ─────────────────────────────────────────

    @property
    def cursor(self) -> int:
        return self._cursor

    @property
    def total(self) -> int:
        return len(self._candles)

    @property
    def period_start(self) -> datetime:
        return self._start_dt

    @property
    def period_end(self) -> datetime:
        return self._end_dt

    # ── Pagination helper ─────────────────────────────────────────────────────

    def _fetch_all(
        self, start_dt: datetime, end_dt: datetime, interval: str
    ) -> list[CandleData]:
        """Paginate backwards from end_dt to start_dt, 200 candles per call."""
        all_candles: list[CandleData] = []
        current_to = end_dt
        batch_count = 0

        while True:
            to_str = current_to.strftime("%Y-%m-%d %H:%M:%S")
            df = pyupbit.get_ohlcv(TICKER, interval=interval, count=200, to=to_str)

            if df is None or df.empty:
                break

            batch: list[CandleData] = [
                CandleData(
                    # Strip timezone info so timestamps are naive (KST local time),
                    # consistent with UpbitDataCollector and with our naive start/end_dt.
                    timestamp=index.to_pydatetime().replace(tzinfo=None),
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row["volume"]),
                )
                for index, row in df.iterrows()
            ]

            # Prepend: pagination goes backwards, so earlier batches come first.
            all_candles = batch + all_candles
            batch_count += 1

            oldest_ts = batch[0].timestamp
            if oldest_ts <= start_dt:
                break

            # Move window one second before the oldest fetched candle.
            current_to = oldest_ts - timedelta(seconds=1)
            time.sleep(0.1)

        # Deduplicate by timestamp: the UTC/KST 9-hour offset causes ~108-candle overlap
        # per batch (each new batch's upper end overlaps the previous batch's lower end).
        # Using a dict keyed by timestamp preserves the last-seen value and eliminates dups.
        seen: dict = {}
        for c in all_candles:
            seen[c.timestamp] = c
        unique_candles = sorted(seen.values(), key=lambda c: c.timestamp)

        # Remove candles outside [start_dt, end_dt].
        filtered = [c for c in unique_candles if start_dt <= c.timestamp <= end_dt]
        print(
            f"[Feeder] Fetched {batch_count} batches "
            f"({len(all_candles):,} raw → {len(unique_candles):,} unique → "
            f"{len(filtered):,} in range)."
        )
        return filtered

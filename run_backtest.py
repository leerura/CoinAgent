"""run_backtest.py — Backtest entry point.

Wires up components identically to main.py but substitutes BacktestDataFeeder
for UpbitDataCollector and BacktestLogger for Logger.  No sleep() anywhere.

Usage:
    python run_backtest.py
    python run_backtest.py --start 2025-09-01 --end 2026-02-28
"""

import argparse
from datetime import datetime, timedelta

import config
from backtest.backtest_data_feeder import BacktestDataFeeder
from backtest.backtest_logger import BacktestLogger
from backtest.backtest_runner import BacktestRunner
from components.executors.simulation_executor import SimulationOrderExecutor
from components.indicator_engine import IndicatorEngine
from components.portfolio import Portfolio
from components.risk_manager import RiskManager
from components.strategies.ema_rsi_strategy import EMARSIStrategy


def _parse_args() -> argparse.Namespace:
    today = datetime.now().date()
    default_start = (today - timedelta(days=180)).strftime("%Y-%m-%d")
    default_end = (today - timedelta(days=1)).strftime("%Y-%m-%d")

    parser = argparse.ArgumentParser(description="BTC/KRW EMA-RSI backtest")
    parser.add_argument(
        "--start",
        default=default_start,
        help=f"Backtest start date YYYY-MM-DD (default: {default_start})",
    )
    parser.add_argument(
        "--end",
        default=default_end,
        help=f"Backtest end date YYYY-MM-DD (default: {default_end})",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    print("=" * 56)
    print("  Coin Backtest — EMA(200) + RSI(14) Strategy")
    print("=" * 56)
    print(f"  Period            : {args.start} ~ {args.end}")
    print(f"  Initial cash      : {config.INITIAL_CASH:,.0f} KRW")
    print(f"  Position size     : {config.POSITION_SIZE_RATIO * 100:.0f}% of available cash")
    print(f"  Max pyramid levels: {config.MAX_POSITION_LEVELS}")
    print(f"  RSI oversold      : {config.RSI_OVERSOLD} (BUY threshold)")
    print(f"  RSI overbought    : {config.RSI_OVERBOUGHT} (SELL threshold)")
    print(f"  Stop-loss         : {config.STOP_LOSS * 100:.1f}%")
    print(f"  Take-profit       : {config.TAKE_PROFIT_2 * 100:.1f}% (full)")
    print("=" * 56)

    # ── Component assembly (same order as main.py) ────────────────────────────

    feeder = BacktestDataFeeder(
        start=args.start,
        end=args.end,
        interval=config.CANDLE_INTERVAL,
    )

    indicator = IndicatorEngine()
    strategy = EMARSIStrategy()
    risk_manager = RiskManager()
    portfolio = Portfolio(initial_cash=config.INITIAL_CASH)
    executor = SimulationOrderExecutor()
    logger = BacktestLogger()

    runner = BacktestRunner(
        feeder=feeder,
        indicator=indicator,
        strategy=strategy,
        risk_manager=risk_manager,
        portfolio=portfolio,
        executor=executor,
        logger=logger,
    )

    # ── Run ───────────────────────────────────────────────────────────────────
    print(f"\n[Runner] Starting backtest over {feeder.total:,} candles…\n")
    result = runner.run()

    # ── Print final report ────────────────────────────────────────────────────
    logger.print_report(result)


if __name__ == "__main__":
    main()

"""main.py — Component assembly and entry point.

All concrete objects are created here and wired together (Composition Root).

DIP: components depend on abstractions defined in core/interfaces.py.
     Only main.py knows which concrete implementations to use.
SRP: main.py is responsible solely for assembly and startup — no business logic.
"""

import config
from agent import TradingAgent
from components.data_collector import UpbitDataCollector
from components.executors.simulation_executor import SimulationOrderExecutor
from components.indicator_engine import IndicatorEngine
from components.logger import Logger
from components.portfolio import Portfolio
from components.risk_manager import RiskManager
from components.strategies.rsi_strategy import RSIStrategy


def main() -> None:
    # ── Startup banner ────────────────────────────────────────────────────────
    print("=" * 56)
    print("  Coin Auto-Trading Simulation Agent")
    print("=" * 56)
    print(f"  Initial cash      : {config.INITIAL_CASH:,.0f} KRW")
    print(f"  Position size     : {config.POSITION_SIZE_RATIO * 100:.0f}% of available cash")
    print(f"  RSI oversold      : {config.RSI_OVERSOLD} (BUY threshold)")
    print(f"  RSI overbought    : {config.RSI_OVERBOUGHT} (SELL threshold)")
    print(f"  Stop-loss         : {config.STOP_LOSS * 100:.1f}%")
    print(f"  Take-profit       : {config.TAKE_PROFIT * 100:.1f}%")
    print(f"  Loop interval     : {config.INTERVAL_SEC}s")
    print("=" * 56)

    # ── Component instantiation (dependency order — no circular deps) ─────────

    # 1. Logger first: other components may need it for error reporting.
    logger = Logger()

    # 2. Data layer: fetches raw market data from Upbit.
    collector = UpbitDataCollector()

    # 3. Indicator engine: stateless transformer (candles → IndicatorResult).
    indicator = IndicatorEngine()

    # 4. Strategy: interprets indicators and emits trading signals.
    #    OCP: swap RSIStrategy for any other BaseStrategy without changing agent.py.
    strategy = RSIStrategy()

    # 5. Risk manager: price-based exit rules (stop-loss / take-profit).
    risk_manager = RiskManager()

    # 6. Portfolio: mutable state (cash, BTC, entry price, trade history).
    portfolio = Portfolio(initial_cash=config.INITIAL_CASH)

    # 7. Executor: converts Action decisions into TradeLog records (simulation mode).
    #    LSP: replacing with a live UpbitOrderExecutor requires no changes upstream.
    #    FEE_RATE is read directly from config inside SimulationOrderExecutor.
    executor = SimulationOrderExecutor()

    # 8. Agent: wires all components together via constructor DI.
    #    DIP: TradingAgent receives abstractions — it never imports concretes.
    agent = TradingAgent(
        collector=collector,
        indicator=indicator,
        strategy=strategy,
        risk_manager=risk_manager,
        portfolio=portfolio,
        executor=executor,
        logger=logger,
    )

    # ── Run ───────────────────────────────────────────────────────────────────
    try:
        agent.run()
    except KeyboardInterrupt:
        print("\n[Agent] Shutdown requested. Goodbye.")


if __name__ == "__main__":
    main()

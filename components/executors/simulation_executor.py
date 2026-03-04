# components/executors/simulation_executor.py

from datetime import datetime

from config import FEE_RATE, POSITION_SIZE_RATIO
from core.interfaces import BaseOrderExecutor
from core.models import Action, TradeLog


class SimulationOrderExecutor(BaseOrderExecutor):
    """
    Virtual order executor for back-testing and dry-run simulation.

    Implements BaseOrderExecutor using pure arithmetic — no real exchange
    calls, no I/O, no side effects.  All trade math happens here so that
    TradingAgent stays decoupled from execution details.

    Swap contract: replace this with UpbitOrderExecutor (same interface)
    to go live without changing any other component.
    """

    def execute(self, action: Action, price: float, cash: float, btc: float) -> TradeLog:
        now = datetime.now()

        if action == Action.BUY:
            # Guard: skip if there is not enough cash to buy a meaningful amount
            if cash < price * 1e-8:
                return TradeLog(
                    timestamp=now,
                    action=action.value,
                    price=price,
                    amount=0,
                    fee=0,
                    cash_after=cash,
                    btc_after=btc,
                    total_value=cash + btc * price,
                    reason="BUY skipped: insufficient cash",
                )

            buy_value_krw = cash * POSITION_SIZE_RATIO          # KRW to spend on this buy
            btc_amount    = buy_value_krw / price               # BTC units acquired
            fee           = buy_value_krw * FEE_RATE            # exchange fee in KRW
            cash_after    = cash - buy_value_krw - fee          # deduct spend + fee
            btc_after     = btc + btc_amount                    # add newly bought BTC
            total_value   = cash_after + btc_after * price      # portfolio value in KRW

            return TradeLog(
                timestamp=now,
                action=action.value,
                price=price,
                amount=btc_amount,
                fee=fee,
                cash_after=cash_after,
                btc_after=btc_after,
                total_value=total_value,
                reason=f"BUY executed: {btc_amount:.8f} BTC @ {price:,.0f} KRW (fee: {fee:.2f} KRW)",
            )

        if action in (Action.SELL, Action.FORCE_SELL):
            # Guard: skip if there is no BTC to sell
            if btc == 0.0:
                return TradeLog(
                    timestamp=now,
                    action=action.value,
                    price=price,
                    amount=0,
                    fee=0,
                    cash_after=cash,
                    btc_after=0.0,
                    total_value=cash,
                    reason="SELL skipped: no BTC position",
                )

            sell_value_krw = btc * price                        # gross KRW from selling all BTC
            fee            = sell_value_krw * FEE_RATE          # exchange fee in KRW
            cash_after     = cash + sell_value_krw - fee        # add proceeds minus fee
            btc_amount     = btc                                # quantity sold (stored positively)
            btc_after      = 0.0                                # entire position liquidated
            total_value    = cash_after                         # no BTC remaining

            return TradeLog(
                timestamp=now,
                action=action.value,
                price=price,
                amount=btc_amount,
                fee=fee,
                cash_after=cash_after,
                btc_after=btc_after,
                total_value=total_value,
                reason=f"{action.value} executed: {btc:.8f} BTC @ {price:,.0f} KRW (fee: {fee:.2f} KRW)",
            )

        raise ValueError(f"Unsupported action for executor: {action}")

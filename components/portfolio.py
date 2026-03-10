from typing import Optional

from core.models import Action


class Portfolio:
    """Manages portfolio state: cash, BTC holdings, avg entry price, position count.

    SRP: This class only tracks state. It does not calculate position sizes,
    compute fees, or decide when to trade — those responsibilities belong to
    SimulationOrderExecutor. Fees are accepted as pre-computed values via update().

    Single-entry strategy:
    - position_count is 0 (flat) or 1 (in position).
    - Full sells (SELL / FORCE_SELL) reset both avg_entry_price and position_count.
    """

    def __init__(self, initial_cash: float) -> None:
        self._cash: float = initial_cash
        self._btc_amount: float = 0.0
        self._avg_entry_price: Optional[float] = None  # None means no open position
        self._position_count: int = 0                  # 0 = flat; 1 = in position
        self._wins: int = 0
        self._losses: int = 0

    # ── Accessors ─────────────────────────────────────────────────────────────

    def get_cash(self) -> float:
        return self._cash

    def get_btc_amount(self) -> float:
        return self._btc_amount

    def get_avg_entry_price(self) -> Optional[float]:
        return self._avg_entry_price

    def get_entry_price(self) -> Optional[float]:
        """Alias for get_avg_entry_price() — backwards compatibility."""
        return self._avg_entry_price

    def get_position_count(self) -> int:
        return self._position_count

    def has_position(self) -> bool:
        return self._btc_amount > 0


    # ── State mutations ────────────────────────────────────────────────────────

    def update(self, action: Action, price: float, amount: float, fee: float) -> None:
        """Apply an executed trade to the portfolio state.

        Args:
            action: The action that was executed.
            price:  Execution price (KRW per BTC).
            amount: BTC quantity transacted.
            fee:    Absolute fee in KRW, already computed by the caller.
        """
        if action == Action.BUY:
            cost = price * amount + fee
            self._cash -= cost
            self._avg_entry_price = price
            self._btc_amount += amount
            self._position_count += 1

        elif action in (Action.SELL, Action.FORCE_SELL):
            proceeds = price * amount - fee
            self._cash += proceeds

            # Win/loss counted only on full exit
            if self._avg_entry_price is not None and price > self._avg_entry_price:
                self._wins += 1
            else:
                self._losses += 1

            # Full exit: reset all position state
            self._btc_amount = 0.0
            self._avg_entry_price = None
            self._position_count = 0

        # HOLD: no state change

    # ── Portfolio metrics ──────────────────────────────────────────────────────

    def get_total_value(self, current_price: float) -> float:
        """Mark-to-market total portfolio value in KRW."""
        return self._cash + self._btc_amount * current_price

    def get_win_rate(self) -> float:
        """Returns fraction of completed trades that were profitable (0.0–1.0).

        Returns 0.0 if no trades have been completed yet.
        """
        total = self._wins + self._losses
        if total == 0:
            return 0.0
        return self._wins / total

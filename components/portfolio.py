from typing import Optional

from core.models import Action


class Portfolio:
    """Manages portfolio state: cash, BTC holdings, avg entry price, position count.

    SRP: This class only tracks state. It does not calculate position sizes,
    compute fees, or decide when to trade — those responsibilities belong to
    SimulationOrderExecutor. Fees are accepted as pre-computed values via update().

    Pyramid support:
    - avg_entry_price is recalculated as a weighted average on each BUY.
    - position_count tracks how many pyramid levels are open (0 = flat).
    - partial_sell() sells a fraction of BTC and resets position_count to 0 (re-entry allowed).
    - Full sells (SELL / FORCE_SELL) reset both avg_entry_price and position_count.
    """

    def __init__(self, initial_cash: float) -> None:
        self._cash: float = initial_cash
        self._btc_amount: float = 0.0
        self._avg_entry_price: Optional[float] = None  # None means no open position
        self._position_count: int = 0                  # 0 = flat; max = MAX_POSITION_LEVELS
        self._is_partially_sold: bool = False          # True after first take-profit partial sell
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

    def is_partially_sold(self) -> bool:
        return self._is_partially_sold

    def has_position(self) -> bool:
        return self._position_count > 0

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

            # Weighted-average entry price across all pyramid levels
            if self._avg_entry_price is None or self._btc_amount == 0.0:
                self._avg_entry_price = price
            else:
                total_btc = self._btc_amount + amount
                self._avg_entry_price = (
                    (self._btc_amount * self._avg_entry_price + amount * price) / total_btc
                )

            self._btc_amount += amount
            self._position_count += 1

        elif action == Action.PARTIAL_SELL:
            # Partial exit: sell a fraction of BTC, keep position open
            proceeds = price * amount - fee
            self._cash += proceeds
            self._btc_amount -= amount
            self._is_partially_sold = True
            # avg_entry_price kept — guards TAKE_PROFIT_2 and FORCE_SELL correctly.
            # position_count reset to 0 so the strategy can re-enter on the next
            # valid RSI crossover signal after the partial sell.
            self._position_count = 0

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
            self._is_partially_sold = False

        # HOLD: no state change

    def partial_sell(self, ratio: float, price: float, fee: float) -> None:
        """Convenience wrapper: sell `ratio` of current BTC holdings.

        Delegates to update() with the computed BTC amount so the win/loss
        and position_count logic stays in one place.
        """
        amount = self._btc_amount * ratio
        self.update(Action.PARTIAL_SELL, price, amount, fee)

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

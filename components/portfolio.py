from typing import Optional

from core.models import Action


class Portfolio:
    """Manages portfolio state: cash, BTC holdings, entry price, and trade results.

    SRP: This class only tracks state. It does not calculate position sizes,
    compute fees, or decide when to trade — those responsibilities belong to
    SimulationOrderExecutor. Fees are accepted as pre-computed values via update().
    """

    def __init__(self, initial_cash: float) -> None:
        self._cash: float = initial_cash
        self._btc_amount: float = 0.0
        self._entry_price: Optional[float] = None  # None means no open position
        self._wins: int = 0
        self._losses: int = 0

    def get_cash(self) -> float:
        return self._cash

    def get_btc_amount(self) -> float:
        return self._btc_amount

    def get_entry_price(self) -> Optional[float]:
        return self._entry_price

    def has_position(self) -> bool:
        return self._entry_price is not None

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
            self._btc_amount += amount
            self._entry_price = price

        elif action in (Action.SELL, Action.FORCE_SELL):
            proceeds = price * amount - fee
            self._cash += proceeds

            # Win if net sell price per BTC exceeds entry price
            if self._entry_price is not None and price > self._entry_price:
                self._wins += 1
            else:
                self._losses += 1

            self._btc_amount = 0.0
            self._entry_price = None  # No position after selling

        # HOLD: no state change

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

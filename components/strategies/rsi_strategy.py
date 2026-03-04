# components/strategies/rsi_strategy.py
# SRP: RSI 크로스오버 기반 시그널 생성만 책임 — 포트폴리오 상태 조회/로깅 없음

from datetime import datetime

from config import RSI_OVERBOUGHT, RSI_OVERSOLD
from core.interfaces import BaseStrategy
from core.models import Action, IndicatorResult, Signal


class RSIStrategy(BaseStrategy):
    """
    RSI 크로스오버 로직으로 BUY/SELL/HOLD 시그널을 생성한다.

    무상태(stateless) 설계 이유: 외부 상태에 의존하지 않으면
    IndicatorResult만으로 결정이 완전히 재현되므로 단위 테스트가 용이하다.
    포트폴리오 보유 여부 등 상태 기반 필터링은 TradingAgent의 책임이다.
    """

    def generate_signal(self, indicator: IndicatorResult, position_count: int = 0) -> Signal:
        prev_rsi = indicator.prev_rsi
        current_rsi = indicator.rsi

        # BUY: RSI가 과매도 기준선을 아래에서 위로 돌파
        if prev_rsi < RSI_OVERSOLD and current_rsi >= RSI_OVERSOLD:
            return Signal(
                action=Action.BUY,
                reason=f"RSI {prev_rsi:.1f} → {current_rsi:.1f} 상향 돌파 (기준: {RSI_OVERSOLD:.0f})",
                timestamp=datetime.now(),
            )

        # SELL: RSI가 과매수 기준선을 위에서 아래로 돌파
        if prev_rsi > RSI_OVERBOUGHT and current_rsi <= RSI_OVERBOUGHT:
            return Signal(
                action=Action.SELL,
                reason=f"RSI {prev_rsi:.1f} → {current_rsi:.1f} 하향 돌파 (기준: {RSI_OVERBOUGHT:.0f})",
                timestamp=datetime.now(),
            )

        # HOLD: 돌파 조건 미충족
        return Signal(
            action=Action.HOLD,
            reason=f"RSI {current_rsi:.1f}, 돌파 조건 미충족",
            timestamp=datetime.now(),
        )

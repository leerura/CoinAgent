# components/strategies/ema_rsi_strategy.py
# SRP: EMA(200) 추세 필터 + RSI 크로스오버 기반 시그널 생성만 책임 — 포트폴리오 상태 조회/로깅 없음

from datetime import datetime

from config import RSI_OVERBOUGHT, RSI_OVERSOLD
from core.interfaces import BaseStrategy
from core.models import Action, IndicatorResult, Signal


class EMARSIStrategy(BaseStrategy):
    """
    EMA(200) 추세 필터 + RSI(14) 크로스오버로 BUY/SELL/HOLD 시그널을 생성한다.

    설계 원칙:
    - SRP: 시그널 생성만 담당 — 실행/리스크 로직 없음.
    - OCP: BaseStrategy 인터페이스 구현 — main.py에서 DI로 교체 가능.

    전략 논리:
    - BUY : 가격이 EMA(200) 위에 있고(상승 추세), RSI가 과매도(40) 기준선을 하→상 돌파.
    - SELL: RSI가 과매수(60) 기준선을 상→하 돌파 (추세 무관하게 차익 실현).
    - HOLD: 위 조건 미충족.
    """

    def generate_signal(self, indicator: IndicatorResult) -> Signal:
        price_above_ema = indicator.current_price > indicator.ema_200
        rsi_cross_up    = indicator.prev_rsi < RSI_OVERSOLD  and indicator.rsi >= RSI_OVERSOLD
        rsi_cross_down  = indicator.prev_rsi > RSI_OVERBOUGHT and indicator.rsi <= RSI_OVERBOUGHT

        # BUY: 상승 추세(EMA200 위) + RSI 과매도 상향 돌파
        if price_above_ema and rsi_cross_up:
            return Signal(
                action=Action.BUY,
                reason=(
                    f"EMA200({indicator.ema_200:,.0f}) 위, "
                    f"RSI {indicator.prev_rsi:.1f} → {indicator.rsi:.1f} 상향 돌파 (기준: {RSI_OVERSOLD:.0f})"
                ),
                timestamp=datetime.now(),
            )

        # SELL: RSI 과매수 하향 돌파 (추세 조건 없음 — 보유 포지션 차익 실현)
        if rsi_cross_down:
            return Signal(
                action=Action.SELL,
                reason=(
                    f"RSI {indicator.prev_rsi:.1f} → {indicator.rsi:.1f} 하향 돌파 (기준: {RSI_OVERBOUGHT:.0f})"
                ),
                timestamp=datetime.now(),
            )

        # HOLD: 돌파 조건 미충족
        return Signal(
            action=Action.HOLD,
            reason=f"RSI {indicator.rsi:.1f}, 돌파 조건 미충족",
            timestamp=datetime.now(),
        )

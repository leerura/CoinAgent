# components/strategies/ema_rsi_strategy.py
# SRP: EMA(200) 추세 필터 + RSI 크로스오버 기반 시그널 생성만 책임 — 포트폴리오 상태 조회/로깅 없음

from datetime import datetime
from typing import Optional

from config import MAX_POSITION_LEVELS, RSI_OVERSOLD
from core.interfaces import BaseStrategy
from core.models import Action, IndicatorResult, Signal


class EMARSIStrategy(BaseStrategy):
    """
    EMA(200) 추세 필터 + RSI(14) 크로스오버로 BUY/HOLD 시그널을 생성한다.

    설계 원칙:
    - SRP: 시그널 생성만 담당 — 실행/리스크 로직 없음.
    - OCP: BaseStrategy 인터페이스 구현 — main.py에서 DI로 교체 가능.

    전략 논리:
    - BUY : 가격이 EMA(200) 위에 있고(상승 추세), RSI가 과매도(35) 기준선을 하→상 돌파.
            position_count < MAX_POSITION_LEVELS일 때만 허용.
    - HOLD: 위 조건 미충족, 또는 동일 캔들 중복 진입 방지.

    중복 진입 방지 (deduplication guard):
    - 동일한 캔들 타임스탬프에서 BUY 시그널이 이미 발생한 경우 HOLD를 반환한다.
    - 5분봉 캔들 사용 시 한 캔들 내 복수 진입을 원천 차단한다.
    """

    def __init__(self) -> None:
        self._last_signal_candle_ts: Optional[datetime] = None

    def generate_signal(self, indicator: IndicatorResult, position_count: int = 0) -> Signal:
        # Guard: 최대 포지션 레벨 도달 → 추가 진입 금지
        if position_count >= MAX_POSITION_LEVELS:
            return Signal(
                action=Action.HOLD,
                reason=f"최대 포지션 레벨 도달 ({position_count}/{MAX_POSITION_LEVELS}), 추가 진입 생략",
                timestamp=datetime.now(),
            )

        price_above_ema = indicator.current_price > indicator.ema_200
        rsi_cross_up    = indicator.prev_rsi < RSI_OVERSOLD and indicator.rsi >= RSI_OVERSOLD

        # BUY: 상승 추세(EMA200 위) + RSI 과매도 상향 돌파
        if price_above_ema and rsi_cross_up:
            # Deduplication guard: 동일 캔들에서 이미 BUY 발행 → 중복 방지
            if self._last_signal_candle_ts == indicator.timestamp:
                return Signal(
                    action=Action.HOLD,
                    reason=f"동일 캔들 중복 BUY 방지 (ts={indicator.timestamp})",
                    timestamp=datetime.now(),
                )

            self._last_signal_candle_ts = indicator.timestamp
            return Signal(
                action=Action.BUY,
                reason=(
                    f"EMA200({indicator.ema_200:,.0f}) 위, "
                    f"RSI {indicator.prev_rsi:.1f} → {indicator.rsi:.1f} 상향 돌파 (기준: {RSI_OVERSOLD:.0f}), "
                    f"level={position_count}/{MAX_POSITION_LEVELS}"
                ),
                timestamp=datetime.now(),
            )

        # HOLD: 돌파 조건 미충족
        return Signal(
            action=Action.HOLD,
            reason=f"RSI {indicator.rsi:.1f}, 돌파 조건 미충족",
            timestamp=datetime.now(),
        )

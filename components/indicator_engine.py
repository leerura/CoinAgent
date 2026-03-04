# components/indicator_engine.py
# SRP: 기술적 지표 계산만 책임 — 데이터 수집/시그널 생성은 관여하지 않음
# No ABC exists for IndicatorEngine in core/interfaces.py — plain concrete class.

import pandas as pd
import ta.momentum

import config
from core.models import CandleData, IndicatorResult


class IndicatorEngine:
    """
    CandleData 리스트에서 기술적 지표(RSI)를 계산한다.
    DataCollector와 Strategy 사이의 중간 계층 역할 (SRP).
    """

    def calculate(self, candles: list[CandleData]) -> IndicatorResult:
        """
        최신 RSI와 직전 RSI를 계산해 IndicatorResult로 반환한다.

        :param candles: CandleData 리스트. 오름차순 정렬(oldest→newest) 가정.
                        UpbitDataCollector.get_candles()가 이 순서를 보장한다
                        (components/data_collector.py line 45 주석 참고).
        :raises ValueError: RSI 계산에 충분한 캔들이 없을 때.
        """
        # Guard: ta 라이브러리는 첫 번째 유효한 RSI 값을 내려면 RSI_PERIOD+1개가 필요하다.
        # prev_rsi([-2] 인덱스)까지 안전하게 읽으려면 한 개 더 필요하므로 RSI_PERIOD+2가 최솟값.
        if len(candles) < config.RSI_PERIOD + 2:
            raise ValueError(
                f"RSI 계산에 최소 {config.RSI_PERIOD + 2}개의 캔들이 필요합니다. "
                f"현재: {len(candles)}개."
            )

        # close 가격을 pandas Series로 추출 (ta 라이브러리 입력 타입 요구사항).
        # 캔들이 이미 오름차순(oldest→newest)이므로 별도 역순 정렬 불필요.
        close = pd.Series([c.close for c in candles])

        # config.RSI_PERIOD(기본 14)를 사용해 RSI 계산.
        rsi_series = ta.momentum.RSIIndicator(close=close, window=config.RSI_PERIOD).rsi()

        # 최신값[-1]과 직전값[-2]: Strategy의 크로스오버 감지에 사용된다.
        rsi: float = float(rsi_series.iloc[-1])
        prev_rsi: float = float(rsi_series.iloc[-2])

        # 가장 최근 캔들의 timestamp를 사용 — RSI 값과 동일한 시점을 가리킴.
        return IndicatorResult(
            rsi=rsi,
            prev_rsi=prev_rsi,
            timestamp=candles[-1].timestamp,
        )

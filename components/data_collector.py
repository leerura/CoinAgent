# components/data_collector.py
# SRP: 데이터 수집만 책임, API 세부사항은 이 클래스 안에 캡슐화
# OCP: DataCollector ABC 구현 - 거래소 변경 시 이 파일만 교체

import pyupbit
from core.interfaces import DataCollector
from core.models import CandleData


class UpbitDataCollector(DataCollector):
    """
    업비트 API를 통해 BTC/KRW 1분 캔들 데이터를 수집한다.
    pyupbit 라이브러리에 대한 의존을 이 클래스 안에 격리 (Facade 패턴).
    """

    TICKER = "KRW-BTC"#TODO: config.py에서 추출
    INTERVAL = "minute1"

    def get_candles(self, count: int) -> list[CandleData]:
        """
        최신 캔들 데이터를 count개 반환한다.
        API 호출 실패 시 빈 리스트 반환 (상위 레이어에서 HOLD 처리).

        :param count: 가져올 캔들 수 (RSI 14 계산 시 최소 15개 이상 권장)
        :return: 오래된 순으로 정렬된 CandleData 리스트
        """
        df = pyupbit.get_ohlcv(self.TICKER, interval=self.INTERVAL, count=count)

        # pyupbit는 실패 시 None 반환 — 빈 리스트로 처리
        if df is None or df.empty:
            return []

        candles = [
            CandleData(
                timestamp=index.to_pydatetime(),
                open=row["open"],
                high=row["high"],
                low=row["low"],
                close=row["close"],
                volume=row["volume"],
            )
            for index, row in df.iterrows()
        ]

        return candles  # pyupbit 반환이 이미 오름차순 (오래된 → 최신)
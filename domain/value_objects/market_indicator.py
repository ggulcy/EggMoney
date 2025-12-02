"""Market Indicator Value Objects - VIX와 RSI만 사용"""
from dataclasses import dataclass


@dataclass(frozen=True)
class VixIndicator:
    """VIX 변동성 지수"""
    value: float
    level: str  # "안정 🤩", "중립 😊", "불안 😟", "공포 😱"

    @staticmethod
    def from_value(vix_value: float) -> 'VixIndicator':
        """VIX 값으로부터 지표 생성"""
        if vix_value < 15:
            level = "안정 🤩"
        elif vix_value < 20:
            level = "중립 😊"
        elif vix_value < 30:
            level = "불안 😟"
        else:
            level = "공포 😱"

        return VixIndicator(value=vix_value, level=level)


@dataclass(frozen=True)
class RsiIndicator:
    """RSI 지수"""
    value: float
    level: str  # "극단적 공포 😱", "공포 😨", "중립 😐", "탐욕 😄", "극단적 탐욕 🤩"

    @staticmethod
    def from_value(rsi_value: float) -> 'RsiIndicator':
        """RSI 값으로부터 지표 생성"""
        if rsi_value >= 70:
            level = "극단적 탐욕 🤩"
        elif rsi_value >= 60:
            level = "탐욕 😄"
        elif rsi_value >= 50:
            level = "중립 😐"
        elif rsi_value >= 40:
            level = "공포 😨"
        else:
            level = "극단적 공포 😱"

        return RsiIndicator(value=rsi_value, level=level)

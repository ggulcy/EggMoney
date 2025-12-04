"""Market Indicator Value Objects - VIX와 RSI만 사용"""
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class VixIndicator:
    """VIX 변동성 지수"""
    value: float
    level: str  # "안정 🤩", "중립 😊", "불안 😟", "공포 😱"
    cached_at: Optional[str] = None  # ISO 형식 타임스탬프
    elapsed_hours: Optional[float] = None  # 캐시 경과 시간 (시간 단위)

    @staticmethod
    def from_value(
        vix_value: float,
        cached_at: Optional[str] = None,
        elapsed_hours: Optional[float] = None
    ) -> 'VixIndicator':
        """VIX 값으로부터 지표 생성

        Args:
            vix_value: VIX 값
            cached_at: 캐시 생성 시간 (ISO 형식)
            elapsed_hours: 캐시 경과 시간 (시간 단위)
        """
        if vix_value < 15:
            level = "안정 🤩"
        elif vix_value < 20:
            level = "중립 😊"
        elif vix_value < 30:
            level = "불안 😟"
        else:
            level = "공포 😱"

        return VixIndicator(
            value=vix_value,
            level=level,
            cached_at=cached_at,
            elapsed_hours=elapsed_hours
        )


@dataclass(frozen=True)
class RsiIndicator:
    """RSI 지수"""
    value: float
    level: str  # "극단적 공포 😱", "공포 😨", "중립 😐", "탐욕 😄", "극단적 탐욕 🤩"
    cached_at: Optional[str] = None  # ISO 형식 타임스탬프
    elapsed_hours: Optional[float] = None  # 캐시 경과 시간 (시간 단위)

    @staticmethod
    def from_value(
        rsi_value: float,
        cached_at: Optional[str] = None,
        elapsed_hours: Optional[float] = None
    ) -> 'RsiIndicator':
        """RSI 값으로부터 지표 생성

        Args:
            rsi_value: RSI 값
            cached_at: 캐시 생성 시간 (ISO 형식)
            elapsed_hours: 캐시 경과 시간 (시간 단위)
        """
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

        return RsiIndicator(
            value=rsi_value,
            level=level,
            cached_at=cached_at,
            elapsed_hours=elapsed_hours
        )

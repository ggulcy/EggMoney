"""IndicatorLevel Value Object - 시장 지표 레벨"""
from dataclasses import dataclass


@dataclass
class IndicatorLevel:
    """
    시장 지표 레벨 값 객체

    RSI, VIX 등의 현재 값과 해당 레벨 정보를 표현
    """
    value: float
    level: str
    emoji: str
    css_class: str

    def to_dict(self) -> dict:
        """딕셔너리로 변환 (JSON 직렬화용)"""
        return {
            "value": self.value,
            "level": self.level,
            "emoji": self.emoji,
            "css_class": self.css_class
        }

    @staticmethod
    def from_rsi(rsi: float) -> "IndicatorLevel":
        """RSI 값으로부터 레벨 생성"""
        if rsi >= 80:
            return IndicatorLevel(rsi, "극단적 탐욕", "🤩", "greed")
        elif rsi >= 60:
            return IndicatorLevel(rsi, "탐욕", "😄", "greed")
        elif rsi >= 40:
            return IndicatorLevel(rsi, "중립", "😐", "neutral")
        elif rsi >= 25:
            return IndicatorLevel(rsi, "공포", "😨", "fear")
        else:
            return IndicatorLevel(rsi, "극단적 공포", "😱", "fear")

    @staticmethod
    def from_vix(vix: float) -> "IndicatorLevel":
        """VIX 값으로부터 레벨 생성"""
        if vix <= 12:  #Lv1 0~12
            return IndicatorLevel(vix, "탐욕", "🤩", "greed")
        elif vix <= 18: #Lv2 12~18
            return IndicatorLevel(vix, "중립", "😐", "neutral")
        elif vix <= 24: #Lv3 18~24
            return IndicatorLevel(vix, "불안", "😟", "fear")
        elif vix <= 30: #Lv4 24~
            return IndicatorLevel(vix, "공포", "😨", "fear")
        else:
            return IndicatorLevel(vix, "극단적 공포", "😱", "fear")
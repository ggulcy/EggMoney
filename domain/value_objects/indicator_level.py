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
        if rsi >= 70:
            return IndicatorLevel(rsi, "극단적 탐욕", "🤩", "greed")
        elif rsi >= 55:
            return IndicatorLevel(rsi, "탐욕", "😄", "greed")
        elif rsi >= 45:
            return IndicatorLevel(rsi, "중립", "😐", "neutral")
        elif rsi >= 30:
            return IndicatorLevel(rsi, "공포", "😨", "fear")
        else:
            return IndicatorLevel(rsi, "극단적 공포", "😱", "fear")

    @staticmethod
    def from_vix(vix: float) -> "IndicatorLevel":
        """VIX 값으로부터 레벨 생성"""
        if vix <= 15:  #Lv0 ~ 15
            return IndicatorLevel(vix, "안정", "🤩", "greed")
        elif vix <= 20: #Lv2 15~20
            return IndicatorLevel(vix, "중립", "😐", "neutral")
        elif vix <= 30: #Lv3 20~30
            return IndicatorLevel(vix, "높은변동성", "😟", "fear")
        else:
            return IndicatorLevel(vix, "극단적변동성", "😱", "fear")

    @staticmethod
    def from_moving_average(current_price: float, ma20: float, ma60: float) -> "IndicatorLevel":
        """
        이평선 추세 분석

        Args:
            current_price: 현재 주가
            ma20: 20일 이동평균선
            ma60: 60일 이동평균선

        Returns:
            IndicatorLevel: 추세 정보
        """
        # 주가 > 20일선 > 60일선: 강한 상승
        if current_price > ma20 and ma20 > ma60:
            return IndicatorLevel(current_price, "강한 상승 (매수 위주)", "🚀", "strong-uptrend")

        # 주가 > 20일선, 20일선 < 60일선: 약한 상승/전환
        elif current_price > ma20 and ma20 < ma60:
            return IndicatorLevel(current_price, "약한 상승/전환 (매수 조심)", "📈", "weak-uptrend")

        # 주가 < 20일선, 20일선 > 60일선: 약한 하락/전환
        elif current_price < ma20 and ma20 > ma60:
            return IndicatorLevel(current_price, "약한 하락/전환 (매도 조심)", "📉", "weak-downtrend")

        # 주가 < 20일선 < 60일선: 강한 하락
        else:  # current_price < ma20 and ma20 < ma60
            return IndicatorLevel(current_price, "강한 하락 (매도 위주)", "💥", "strong-downtrend")
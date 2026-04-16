"""BotInfo ORM Model - 봇 정보 SQLAlchemy 모델"""
from sqlalchemy import Column, String, Float, Integer, Boolean, Text
from data.persistence.sqlalchemy.core.base import Base


class BotInfoModel(Base):
    """BotInfo 테이블 ORM 모델"""

    __tablename__ = 'bot_info'

    # Primary Key
    name = Column(String, primary_key=True, nullable=False)

    # 기본 정보
    symbol = Column(String, nullable=False, index=True)  # 종목 심볼
    seed = Column(Float, nullable=False)                 # 기본 시드
    profit_rate = Column(Float, nullable=False)          # 목표 수익률
    t_div = Column(Integer, nullable=False)              # 티어 분할 수
    max_tier = Column(Integer, nullable=False)           # 최대 티어
    active = Column(Boolean, nullable=False, default=False, index=True)  # 활성화 상태

    # 매수 조건 체크 플래그
    is_check_buy_avr_price = Column(Boolean, nullable=False, default=True)        # 평균 가격 체크
    is_check_buy_t_div_price = Column(Boolean, nullable=False, default=True)      # 티어 분할 가격 체크

    # 포인트 위치 (p1, p1_2, p2_3)
    point_loc = Column(String, nullable=False)

    # 추가 시드 및 옵션
    added_seed = Column(Float, nullable=False, default=0.0)  # 추가 시드
    skip_sell = Column(Boolean, nullable=False, default=False)  # 매도 스킵 여부

    # 장마감 급락 매수 설정 (JSON 배열: [{"drop_rate": 0.05, "seed_rate": 0.3}, ...])
    closing_buy_conditions = Column(Text, nullable=False, default='[]')

    # 매도 후 쿨다운
    sell_cooldown_days = Column(Integer, nullable=False, default=0)        # 0이면 비활성화
    sell_cooldown_loss_only = Column(Boolean, nullable=False, default=False)  # True면 손절 매도 시에만 적용

    # ATR 트레일링 스탑 설정
    trailing_enabled = Column(Boolean, nullable=False, default=False)          # UI에서 on/off
    trailing_t_threshold = Column(Float, nullable=False, default=0.3)           # T 진입 기준 (max_tier 대비 비율, 0.3=30%)
    trailing_atr_multiplier = Column(Float, nullable=False, default=1.0)       # ATR × N
    trailing_floor_rate = Column(Float, nullable=False, default=0.10)          # 평단 하단 기준

    # ATR 트레일링 스탑 상태 (매일 갱신)
    trailing_mode = Column(Boolean, nullable=False, default=False)             # 현재 트레일링 중 여부
    trailing_high_watermark = Column(Float, nullable=False, default=0.0)       # 고점 워터마크
    trailing_stop = Column(Float, nullable=False, default=0.0)                 # 전날 계산된 스탑가

    def __repr__(self):
        return f"<BotInfoModel(name={self.name}, symbol={self.symbol}, active={self.active})>"

"""BotInfo Entity - 봇 정보 엔티티"""
from typing import Optional
from domain.value_objects.point_loc import PointLoc


class BotInfo:
    """
    봇 정보 엔티티

    egg 프로젝트의 모든 필드를 포함하며, Clean Architecture의 Domain Layer에 위치
    """

    def __init__(
        self,
        name: str,
        symbol: str,
        seed: float,
        profit_rate: float,
        t_div: int,
        max_tier: int,
        active: bool,
        is_check_buy_avr_price: bool,
        is_check_buy_t_div_price: bool,
        point_loc: PointLoc,
        added_seed: float = 0.0,
        skip_sell: bool = False,
        dynamic_seed_max: float = 0.0
    ):
        self.name = name
        self.symbol = symbol
        self.seed = seed
        self.profit_rate = profit_rate
        self.t_div = t_div
        self.max_tier = max_tier
        self.active = active
        self.is_check_buy_avr_price = is_check_buy_avr_price
        self.is_check_buy_t_div_price = is_check_buy_t_div_price
        self.point_loc = point_loc
        self.added_seed = added_seed
        self.skip_sell = skip_sell
        self.dynamic_seed_max = dynamic_seed_max

        self._validate()

    def _validate(self):
        """비즈니스 규칙 검증"""
        if not self.name:
            raise ValueError("name은 필수입니다")
        if not self.symbol:
            raise ValueError("symbol은 필수입니다")
        if self.seed <= 0:
            raise ValueError("seed는 0보다 커야 합니다")
        if self.profit_rate <= 0:
            raise ValueError("profit_rate는 0보다 커야 합니다")
        if self.t_div <= 0:
            raise ValueError("t_div는 0보다 커야 합니다")
        if self.max_tier <= 0:
            raise ValueError("max_tier는 0보다 커야 합니다")
        if not isinstance(self.point_loc, PointLoc):
            raise ValueError("point_loc은 PointLoc Enum이어야 합니다")

    def update_added_seed(self, amount: float):
        """추가 시드 업데이트 (증가)"""
        if amount <= 0:
            raise ValueError("추가 시드는 0보다 커야 합니다")
        self.added_seed += amount

    def remove_added_seed(self):
        """추가 시드 제거 (초기화)"""
        self.added_seed = 0.0

    def get_total_seed(self) -> float:
        """전체 시드 반환 (seed + added_seed)"""
        return self.seed + self.added_seed

    def activate(self):
        """봇 활성화"""
        self.active = True

    def deactivate(self):
        """봇 비활성화"""
        self.active = False

    def __repr__(self):
        return (
            f"BotInfo(name={self.name}, symbol={self.symbol}, "
            f"seed={self.seed}, active={self.active})"
        )

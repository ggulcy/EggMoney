"""PointLoc Value Object - 매수 포인트 위치"""
from enum import Enum


class PointLoc(Enum):
    """매수 포인트 위치 (밴드 내 위치)"""
    P1 = 'P1'          # 포인트 1 (하단)
    P1_2 = 'P1_2'      # 포인트 1-2 (중하단)
    P2_3 = 'P2_3'      # 포인트 2-3 (중상단)

    def __str__(self):
        return self.value

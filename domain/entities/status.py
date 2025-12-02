"""Status Entity - 입출금 상태"""


class Status:
    """입출금 상태 엔티티 (단일 레코드)"""

    def __init__(
        self,
        deposit_won: float,
        deposit_dollar: float,
        withdraw_won: float,
        withdraw_dollar: float,
        id: int = None
    ):
        # 검증
        if deposit_won < 0:
            raise ValueError("deposit_won cannot be negative")
        if deposit_dollar < 0:
            raise ValueError("deposit_dollar cannot be negative")
        if withdraw_won < 0:
            raise ValueError("withdraw_won cannot be negative")
        if withdraw_dollar < 0:
            raise ValueError("withdraw_dollar cannot be negative")

        self.id = id
        self.deposit_won = round(float(deposit_won), 2)
        self.deposit_dollar = round(float(deposit_dollar), 2)
        self.withdraw_won = round(float(withdraw_won), 2)
        self.withdraw_dollar = round(float(withdraw_dollar), 2)

    def get_net_won(self) -> float:
        """순 원화 금액 (입금 - 출금)"""
        return self.deposit_won - self.withdraw_won

    def get_net_dollar(self) -> float:
        """순 달러 금액 (입금 - 출금)"""
        return self.deposit_dollar - self.withdraw_dollar

    def get_total_deposit(self, exchange_rate: float = 0.0) -> float:
        """총 입금액 (원화를 달러로 환산하여 합산)"""
        won_in_dollar = self.deposit_won / exchange_rate if exchange_rate > 0 else 0
        return self.deposit_dollar + won_in_dollar

    def get_total_withdraw(self, exchange_rate: float = 0.0) -> float:
        """총 출금액 (원화를 달러로 환산하여 합산)"""
        won_in_dollar = self.withdraw_won / exchange_rate if exchange_rate > 0 else 0
        return self.withdraw_dollar + won_in_dollar

    def __repr__(self):
        return (f"<Status(id={self.id}, "
                f"deposit_won=₩{self.deposit_won:,.0f}, deposit_dollar=${self.deposit_dollar:,.0f}, "
                f"withdraw_won=₩{self.withdraw_won:,.0f}, withdraw_dollar=${self.withdraw_dollar:,.0f})>")

    def __str__(self):
        return self.__repr__()

"""Trade Repository Implementation - 거래 정보 저장소 구현체"""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func

from domain.entities.trade import Trade
from domain.repositories.trade_repository import TradeRepository
from domain.value_objects.trade_type import TradeType
from data.persistence.sqlalchemy.models.trade_model import TradeModel


class SQLAlchemyTradeRepositoryImpl(TradeRepository):
    """SQLAlchemy 기반 Trade 저장소 구현체"""

    def __init__(self, session: Session):
        """
        Repository 초기화

        Args:
            session: SQLAlchemy 세션 (외부에서 주입)
        """
        self.session = session

    def save(self, trade: Trade) -> None:
        """
        Trade 저장 (신규 또는 업데이트)

        Late Commit 패턴 적용:
        - Primary Key(date_added, name, symbol)가 같은 레코드가 있으면 업데이트
        - 없으면 신규 생성

        Note:
            Primary Key는 불변이므로 date_added, name, symbol은 업데이트하지 않음
        """
        # Primary Key 전체를 사용해서 기존 레코드 조회
        existing = self.session.query(TradeModel).filter_by(
            date_added=trade.date_added,
            name=trade.name,
            symbol=trade.symbol
        ).first()

        if existing:
            # 업데이트: Late Commit 패턴
            # Primary Key(date_added, name, symbol)는 변경하지 않음
            existing.purchase_price = trade.purchase_price
            existing.amount = trade.amount
            existing.total_price = trade.total_price
            existing.trade_type = trade.trade_type
            existing.latest_date_trade = trade.latest_date_trade
        else:
            # 신규 생성
            model = self._to_model(trade)
            self.session.add(model)

        try:
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            raise

    def find_by_name(self, name: str) -> Optional[Trade]:
        """이름으로 Trade 조회 (purchase_price 오름차순 첫 번째)"""
        model = (
            self.session.query(TradeModel)
            .filter_by(name=name)
            .order_by(TradeModel.purchase_price)
            .first()
        )
        return self._to_entity(model) if model else None

    def find_by_symbol(self, symbol: str) -> Optional[Trade]:
        """심볼로 Trade 조회 (purchase_price 오름차순 첫 번째)"""
        model = (
            self.session.query(TradeModel)
            .filter_by(symbol=symbol)
            .order_by(TradeModel.purchase_price)
            .first()
        )
        return self._to_entity(model) if model else None

    def find_all_by_symbol(self, symbol: str) -> List[Trade]:
        """심볼로 모든 Trade 조회 (purchase_price 오름차순)"""
        models = (
            self.session.query(TradeModel)
            .filter_by(symbol=symbol)
            .order_by(TradeModel.purchase_price)
            .all()
        )
        return [self._to_entity(model) for model in models]

    def find_latest_by_symbol(self, symbol: str) -> Optional[Trade]:
        """심볼로 최신 Trade 조회 (date_added 내림차순 첫 번째)"""
        model = (
            self.session.query(TradeModel)
            .filter_by(symbol=symbol)
            .order_by(TradeModel.date_added.desc())
            .first()
        )
        return self._to_entity(model) if model else None

    def find_highest_price_by_symbol(self, symbol: str) -> Optional[Trade]:
        """심볼로 최고가 Trade 조회 (purchase_price 내림차순 첫 번째)"""
        model = (
            self.session.query(TradeModel)
            .filter_by(symbol=symbol)
            .order_by(TradeModel.purchase_price.desc())
            .first()
        )
        return self._to_entity(model) if model else None

    def find_all(self) -> List[Trade]:
        """모든 Trade 조회 (RP는 맨 뒤, 나머지는 name, date_added 오름차순)"""
        from sqlalchemy import case

        models = (
            self.session.query(TradeModel)
            .order_by(
                case((TradeModel.name == 'RP', 1), else_=0),  # RP는 1(뒤), 나머지는 0(앞)
                TradeModel.name,
                TradeModel.date_added
            )
            .all()
        )
        return [self._to_entity(model) for model in models]

    def find_active_trades(self) -> List[Trade]:
        """활성 Trade 조회 (amount > 0, name != "RP")"""
        models = (
            self.session.query(TradeModel)
            .filter(TradeModel.amount > 0, TradeModel.name != "RP")
            .all()
        )
        return [self._to_entity(model) for model in models]

    def get_active_trade_count(self) -> int:
        """활성 Trade 개수 조회"""
        return (
            self.session.query(TradeModel)
            .filter(TradeModel.amount > 0, TradeModel.name != "RP")
            .count()
        )

    def get_total_investment(self, name: str) -> float:
        """총 투자금 조회 (amount * purchase_price의 합계)"""
        total = (
            self.session.query(
                func.sum(TradeModel.amount * TradeModel.purchase_price)
            )
            .filter_by(name=name)
            .scalar()
        )
        return total if total is not None else 0.0

    def get_average_purchase_price(self, name: str) -> Optional[float]:
        """평균 매수 단가 조회"""
        total_amount = (
            self.session.query(func.sum(TradeModel.amount))
            .filter_by(name=name)
            .scalar()
        )
        total_value = (
            self.session.query(
                func.sum(TradeModel.purchase_price * TradeModel.amount)
            )
            .filter_by(name=name)
            .scalar()
        )

        if total_amount is None or total_value is None or total_amount == 0:
            return None

        return round(total_value / total_amount, 2)

    def get_total_amount(self, name: str) -> float:
        """총 보유 수량 조회"""
        total = (
            self.session.query(func.sum(TradeModel.amount))
            .filter_by(name=name)
            .scalar()
        )
        return total if total is not None else 0.0

    def delete_all_by_name(self, name: str) -> None:
        """이름으로 모든 Trade 삭제"""
        try:
            self.session.query(TradeModel).filter_by(name=name).delete()
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

    def get_all_tickers(self) -> List[str]:
        """모든 고유 티커(심볼) 조회"""
        tickers = self.session.query(TradeModel.symbol).distinct().all()
        return [ticker[0] for ticker in tickers]

    def delete_by_name(self, name: str) -> None:
        """
        이름으로 Trade 삭제 (단일 레코드)

        Args:
            name: 봇 이름
        """
        try:
            self.session.query(TradeModel).filter(TradeModel.name == name).delete()
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            raise

    def rebalance_trade(
        self,
        name: str,
        symbol: str,
        prev_trade: Optional[Trade],
        trade_result: 'TradeResult'
    ) -> Trade:
        """
        Trade 리밸런싱 (매수/매도 후 평단가 재계산)

        Args:
            name: 봇 이름
            symbol: 종목 심볼
            prev_trade: 이전 거래 정보 (없으면 None)
            trade_result: 거래 결과

        Returns:
            Trade: 리밸런싱된 Trade

        egg/repository/trade_repository.py의 re_balancing_trade() 이관 (148-191번 줄)
        """
        from datetime import datetime
        from domain.value_objects.trade_type import TradeType

        if prev_trade is None:
            # prev_trade가 None일 경우, trade_result 값을 그대로 사용
            new_amount = trade_result.amount
            new_total = trade_result.total_price
            new_unit_price = trade_result.unit_price
            new_date_added = datetime.now()
        else:
            # prev_trade가 존재할 경우, 기존 값을 기반으로 리밸런싱 계산
            is_buy = trade_result.trade_type.is_buy()
            if is_buy:
                new_amount = prev_trade.amount + trade_result.amount
                new_total = prev_trade.total_price + trade_result.total_price
                new_unit_price = round(new_total / new_amount, 2)
                new_date_added = prev_trade.date_added
            else:
                new_amount = prev_trade.amount - trade_result.amount
                new_total = new_amount * prev_trade.purchase_price
                new_unit_price = prev_trade.purchase_price
                new_date_added = prev_trade.date_added

            # 리밸런싱 결과를 간략하게 출력
            print(
                f"[{trade_result.trade_type}] 리밸런싱:\n"
                f"수량 {prev_trade.amount} -> {new_amount}\n"
                f"전체가격 {prev_trade.total_price:.2f} -> {new_total:.2f}\n"
                f"단가 {prev_trade.purchase_price:.2f} -> {new_unit_price:.2f}")

        # 최종적으로 Trade 객체 반환
        from domain.entities.trade import Trade
        return Trade(
            date_added=new_date_added,
            latest_date_trade=datetime.now(),
            name=name,
            purchase_price=new_unit_price,
            amount=new_amount,
            total_price=new_total,
            trade_type=trade_result.trade_type,
            symbol=symbol
        )

    def sync_all(self, trades: List[Trade]) -> None:
        """
        전체 Trade 동기화 (기존 데이터 삭제 후 새 데이터 삽입)

        Args:
            trades: Trade 리스트
        """
        try:
            # 1. 기존 데이터 삭제
            self.session.query(TradeModel).delete()

            # 2. 새 데이터 삽입
            for trade in trades:
                model = self._to_model(trade)
                self.session.add(model)

            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            raise

    # ===== Mapper: ORM Model ↔ Domain Entity =====

    def _to_entity(self, model: TradeModel) -> Trade:
        """ORM Model → Domain Entity"""
        return Trade(
            name=model.name,
            symbol=model.symbol,
            purchase_price=model.purchase_price,
            amount=model.amount,
            trade_type=model.trade_type,
            total_price=model.total_price,
            date_added=model.date_added,
            latest_date_trade=model.latest_date_trade
        )

    def _to_model(self, entity: Trade) -> TradeModel:
        """Domain Entity → ORM Model"""
        return TradeModel(
            name=entity.name,
            symbol=entity.symbol,
            purchase_price=entity.purchase_price,
            amount=entity.amount,
            trade_type=entity.trade_type,
            total_price=entity.total_price,
            date_added=entity.date_added,
            latest_date_trade=entity.latest_date_trade
        )

    def find_today_buys(self) -> List[Trade]:
        """
        오늘 매수한 Trade 리스트 조회

        SQLAlchemy의 extract()를 사용하여 latest_date_trade의
        year, month, day가 오늘과 일치하는 레코드 조회

        Returns:
            List[Trade]: 오늘 매수한 Trade 엔티티 리스트
        """
        from datetime import datetime
        from sqlalchemy import extract, and_

        today = datetime.now().date()

        # SQLAlchemy 쿼리: latest_date_trade가 오늘인 것
        models = (
            self.session.query(TradeModel)
            .filter(
                and_(
                    extract('year', TradeModel.latest_date_trade) == today.year,
                    extract('month', TradeModel.latest_date_trade) == today.month,
                    extract('day', TradeModel.latest_date_trade) == today.day
                )
            )
            .order_by(TradeModel.latest_date_trade.desc())  # 최신순 정렬
            .all()
        )

        # ORM Model → Domain Entity 변환 (Mapper 패턴)
        return [self._to_entity(model) for model in models]

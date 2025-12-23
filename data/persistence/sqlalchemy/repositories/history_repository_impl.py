"""History Repository Implementation"""
from datetime import datetime
from typing import List, Optional

from sqlalchemy import func, extract, and_, desc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from domain.entities.history import History
from domain.repositories.history_repository import HistoryRepository
from domain.value_objects.trade_type import TradeType
from data.persistence.sqlalchemy.models.history_model import HistoryModel


class SQLAlchemyHistoryRepositoryImpl(HistoryRepository):
    """SQLAlchemy 기반 History Repository 구현체"""

    def __init__(self, session: Session):
        self.session = session

    def save(self, history: History) -> None:
        """히스토리 저장 (Late Commit)"""
        # 복합 PK로 기존 레코드 조회
        existing = self.session.query(HistoryModel).filter_by(
            date_added=history.date_added,
            trade_date=history.trade_date,
            trade_type=history.trade_type,
            name=history.name
        ).first()

        if existing:
            # 업데이트 (Late Commit)
            existing.symbol = history.symbol
            existing.buy_price = history.buy_price
            existing.sell_price = history.sell_price
            existing.amount = history.amount
            existing.profit = history.profit
            existing.profit_rate = history.profit_rate
        else:
            # 신규 삽입
            model = self._to_model(history)
            self.session.add(model)

        self.session.commit()

    def find_by_name(self, name: str) -> Optional[History]:
        """name으로 첫 번째 히스토리 조회 (date_added 오름차순)"""
        model = self.session.query(HistoryModel).filter_by(name=name).order_by(HistoryModel.date_added).first()
        return self._to_entity(model) if model else None

    def find_all(self) -> List[History]:
        """전체 히스토리 조회 (trade_date 역순, name 정렬)"""
        models = self.session.query(HistoryModel).order_by(
            desc(HistoryModel.trade_date),
            HistoryModel.name
        ).all()
        return [self._to_entity(model) for model in models]

    def find_by_name_all(self, name: str) -> List[History]:
        """name으로 모든 히스토리 조회 (최신순)"""
        models = self.session.query(HistoryModel).filter_by(name=name).order_by(HistoryModel.trade_date.desc()).all()
        return [self._to_entity(model) for model in models]

    def find_by_name_and_date(self, name: str, date: datetime) -> List[History]:
        """name과 date_added로 히스토리 조회"""
        models = self.session.query(HistoryModel).filter_by(
            name=name,
            date_added=date
        ).order_by(HistoryModel.trade_date).all()
        return [self._to_entity(model) for model in models]

    def find_today_sell_by_name(self, name: str) -> Optional[History]:
        """오늘의 첫 번째 매도 히스토리 조회 (매도 거래만)"""
        today = datetime.now().date()
        model = self.session.query(HistoryModel).filter(
            and_(
                HistoryModel.name == name,
                extract('year', HistoryModel.trade_date) == today.year,
                extract('month', HistoryModel.trade_date) == today.month,
                extract('day', HistoryModel.trade_date) == today.day,
                self._get_sell_type_filter()
            )
        ).first()
        return self._to_entity(model) if model else None

    def find_by_year_month(self, year: int, month: int, symbol: Optional[str] = None) -> List[History]:
        """연월별 히스토리 조회 (선택적 symbol 필터)"""
        query = self.session.query(HistoryModel).filter(
            extract('year', HistoryModel.trade_date) == year,
            extract('month', HistoryModel.trade_date) == month
        )

        if symbol:
            query = query.filter(HistoryModel.symbol == symbol)

        models = query.order_by(
            desc(HistoryModel.trade_date),
            HistoryModel.name
        ).all()
        return [self._to_entity(model) for model in models]

    def _get_sell_type_filter(self):
        """매도 타입 필터 조건 반환"""
        sell_types = [t for t in TradeType if t.is_sell()]
        return HistoryModel.trade_type.in_(sell_types)

    def get_total_sell_profit(self) -> float:
        """전체 매도 총 수익 (매도 거래만)"""
        total = self.session.query(func.sum(HistoryModel.profit)).filter(
            self._get_sell_type_filter()
        ).scalar()
        return total if total is not None else 0.0

    def get_total_sell_profit_by_name(self, name: str) -> float:
        """name별 매도 총 수익 (매도 거래만)"""
        total = self.session.query(func.sum(HistoryModel.profit)).filter(
            and_(
                HistoryModel.name == name,
                self._get_sell_type_filter()
            )
        ).scalar()
        return total if total is not None else 0.0

    def get_total_sell_profit_by_symbol(self, symbol: str) -> float:
        """symbol별 매도 총 수익 (매도 거래만)"""
        total = self.session.query(func.sum(HistoryModel.profit)).filter(
            and_(
                HistoryModel.symbol == symbol,
                self._get_sell_type_filter()
            )
        ).scalar()
        return total if total is not None else 0.0

    def get_total_sell_profit_by_name_and_date(self, name: str, date: datetime) -> float:
        """name과 date_added별 매도 총 수익 (매도 거래만)"""
        total = self.session.query(func.sum(HistoryModel.profit)).filter(
            and_(
                HistoryModel.name == name,
                HistoryModel.date_added == date,
                self._get_sell_type_filter()
            )
        ).scalar()
        return total if total is not None else 0.0

    def get_total_sell_profit_by_year(self, year: int) -> float:
        """연도별 매도 총 수익 (매도 거래만)"""
        total = self.session.query(func.sum(HistoryModel.profit)).filter(
            and_(
                extract('year', HistoryModel.trade_date) == year,
                self._get_sell_type_filter()
            )
        ).scalar()
        return total if total is not None else 0.0

    def get_monthly_sell_profit_by_year(self, year: int) -> List[tuple]:
        """연도별 월별 매도 수익 [(month, total_profit), ...] (매도 거래만)"""
        results = self.session.query(
            extract('month', HistoryModel.trade_date).label('month'),
            func.sum(HistoryModel.profit).label('total_profit')
        ).filter(
            and_(
                extract('year', HistoryModel.trade_date) == year,
                self._get_sell_type_filter()
            )
        ).group_by(
            extract('month', HistoryModel.trade_date)
        ).order_by(
            extract('month', HistoryModel.trade_date)
        ).all()
        return [(int(month), float(total_profit)) for month, total_profit in results]

    def get_years_from_sell_date(self) -> List[int]:
        """trade_date에서 연도 목록 추출 (중복 제거, 정렬)"""
        years = self.session.query(
            extract('year', HistoryModel.trade_date).distinct().label('year')
        ).order_by('year').all()
        return [int(year.year) for year in years]

    def delete_by_name(self, name: str) -> None:
        """name으로 모든 히스토리 삭제"""
        try:
            self.session.query(HistoryModel).filter_by(name=name).delete()
            self.session.commit()
        except Exception as e:
            self.session.rollback()
            raise e

    def delete(self, name: str, date_added: datetime) -> None:
        """특정 히스토리 삭제 (PK 기반)"""
        try:
            record = self.session.query(HistoryModel).filter(
                and_(
                    HistoryModel.name == name,
                    HistoryModel.date_added == date_added
                )
            ).first()

            if record:
                self.session.delete(record)
                self.session.commit()
        except Exception as e:
            self.session.rollback()
            raise e

    def sync_all(self, history_list: List[History]) -> None:
        """전체 동기화 (기존 데이터 삭제 후 재삽입)"""
        try:
            # 1. 기존 데이터 삭제
            self.session.query(HistoryModel).delete()

            # 2. 새 데이터 삽입
            for history in history_list:
                model = self._to_model(history)
                self.session.add(model)

            self.session.commit()
        except IntegrityError as e:
            self.session.rollback()
            raise e

    def _to_entity(self, model: HistoryModel) -> History:
        """ORM Model → Entity 변환 (Mapper)"""
        return History(
            date_added=model.date_added,
            trade_date=model.trade_date,
            trade_type=model.trade_type,
            name=model.name,
            symbol=model.symbol,
            buy_price=model.buy_price,
            sell_price=model.sell_price,
            amount=model.amount,
            profit=model.profit,
            profit_rate=model.profit_rate
        )

    def _to_model(self, entity: History) -> HistoryModel:
        """Entity → ORM Model 변환 (Mapper)"""
        return HistoryModel(
            date_added=entity.date_added,
            trade_date=entity.trade_date,
            trade_type=entity.trade_type,
            name=entity.name,
            symbol=entity.symbol,
            buy_price=entity.buy_price,
            sell_price=entity.sell_price,
            amount=entity.amount,
            profit=entity.profit,
            profit_rate=entity.profit_rate
        )

    def find_today_sells(self) -> List[History]:
        """
        오늘 매도한 History 리스트 조회

        SQLAlchemy의 extract()를 사용하여 trade_date의
        year, month, day가 오늘과 일치하고 매도 타입인 레코드 조회

        Returns:
            List[History]: 오늘 매도한 History 엔티티 리스트
        """
        today = datetime.now().date()

        # SQLAlchemy 쿼리: trade_date가 오늘이고 매도 타입인 것
        models = (
            self.session.query(HistoryModel)
            .filter(
                and_(
                    extract('year', HistoryModel.trade_date) == today.year,
                    extract('month', HistoryModel.trade_date) == today.month,
                    extract('day', HistoryModel.trade_date) == today.day,
                    self._get_sell_type_filter()
                )
            )
            .order_by(HistoryModel.trade_date.desc())  # 최신순 정렬
            .all()
        )

        # ORM Model → Domain Entity 변환 (Mapper 패턴)
        return [self._to_entity(model) for model in models]

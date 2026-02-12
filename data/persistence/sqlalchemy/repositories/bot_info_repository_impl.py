"""BotInfo Repository Implementation - 봇 정보 저장소 구현체"""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from domain.entities.bot_info import BotInfo
from domain.repositories.bot_info_repository import BotInfoRepository
from domain.value_objects.point_loc import PointLoc
from data.persistence.sqlalchemy.models.bot_info_model import BotInfoModel


class SQLAlchemyBotInfoRepositoryImpl(BotInfoRepository):
    """SQLAlchemy 기반 BotInfo 저장소 구현체"""

    def __init__(self, session: Session):
        """
        Repository 초기화

        Args:
            session: SQLAlchemy 세션 (외부에서 주입)
        """
        self.session = session

    def save(self, bot_info: BotInfo) -> None:
        """
        BotInfo 저장 (신규 또는 업데이트)

        Late Commit 패턴 적용:
        - 기존 레코드가 있으면 필드 업데이트 후 commit
        - 없으면 신규 생성 후 commit
        """
        existing = self.session.query(BotInfoModel).filter_by(name=bot_info.name).first()

        if existing:
            # 업데이트: Late Commit 패턴
            existing.symbol = bot_info.symbol
            existing.seed = bot_info.seed
            existing.profit_rate = bot_info.profit_rate
            existing.t_div = bot_info.t_div
            existing.max_tier = bot_info.max_tier
            existing.active = bot_info.active
            existing.is_check_buy_avr_price = bot_info.is_check_buy_avr_price
            existing.is_check_buy_t_div_price = bot_info.is_check_buy_t_div_price
            existing.point_loc = bot_info.point_loc.value
            existing.added_seed = bot_info.added_seed
            existing.skip_sell = bot_info.skip_sell
            existing.dynamic_seed_max = bot_info.dynamic_seed_max
            existing.dynamic_seed_enabled = bot_info.dynamic_seed_enabled
            existing.dynamic_seed_multiplier = bot_info.dynamic_seed_multiplier
            existing.dynamic_seed_t_threshold = bot_info.dynamic_seed_t_threshold
            existing.dynamic_seed_drop_rate = bot_info.dynamic_seed_drop_rate
            existing.closing_buy_drop_rate = bot_info.closing_buy_drop_rate
            existing.closing_buy_seed_rate = bot_info.closing_buy_seed_rate
        else:
            # 신규 생성
            model = self._to_model(bot_info)
            self.session.add(model)

        try:
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            raise

    def find_by_name(self, name: str) -> Optional[BotInfo]:
        """이름으로 BotInfo 조회"""
        model = self.session.query(BotInfoModel).filter_by(name=name).first()
        return self._to_entity(model) if model else None

    def find_all(self) -> List[BotInfo]:
        """모든 BotInfo 조회"""
        models = self.session.query(BotInfoModel).all()
        return [self._to_entity(model) for model in models]

    def find_by_symbol(self, symbol: str) -> List[BotInfo]:
        """심볼로 BotInfo 리스트 조회"""
        models = self.session.query(BotInfoModel).filter_by(symbol=symbol).all()
        return [self._to_entity(model) for model in models]

    def find_active_bots(self) -> List[BotInfo]:
        """활성화된 BotInfo 리스트 조회"""
        models = self.session.query(BotInfoModel).filter_by(active=True).all()
        return [self._to_entity(model) for model in models]

    def delete(self, name: str) -> None:
        """BotInfo 삭제"""
        model = self.session.query(BotInfoModel).filter_by(name=name).first()
        if model:
            self.session.delete(model)
            self.session.commit()

    # ===== Mapper: ORM Model ↔ Domain Entity =====

    def _to_entity(self, model: BotInfoModel) -> BotInfo:
        """ORM Model → Domain Entity"""
        return BotInfo(
            name=model.name,
            symbol=model.symbol,
            seed=model.seed,
            profit_rate=model.profit_rate,
            t_div=model.t_div,
            max_tier=model.max_tier,
            active=model.active,
            is_check_buy_avr_price=model.is_check_buy_avr_price,
            is_check_buy_t_div_price=model.is_check_buy_t_div_price,
            point_loc=PointLoc(model.point_loc),
            added_seed=model.added_seed,
            skip_sell=model.skip_sell,
            dynamic_seed_max=model.dynamic_seed_max,
            dynamic_seed_enabled=model.dynamic_seed_enabled,
            dynamic_seed_multiplier=model.dynamic_seed_multiplier,
            dynamic_seed_t_threshold=model.dynamic_seed_t_threshold,
            dynamic_seed_drop_rate=model.dynamic_seed_drop_rate,
            closing_buy_drop_rate=model.closing_buy_drop_rate,
            closing_buy_seed_rate=model.closing_buy_seed_rate,
        )

    def _to_model(self, entity: BotInfo) -> BotInfoModel:
        """Domain Entity → ORM Model"""
        return BotInfoModel(
            name=entity.name,
            symbol=entity.symbol,
            seed=entity.seed,
            profit_rate=entity.profit_rate,
            t_div=entity.t_div,
            max_tier=entity.max_tier,
            active=entity.active,
            is_check_buy_avr_price=entity.is_check_buy_avr_price,
            is_check_buy_t_div_price=entity.is_check_buy_t_div_price,
            point_loc=entity.point_loc.value,
            added_seed=entity.added_seed,
            skip_sell=entity.skip_sell,
            dynamic_seed_max=entity.dynamic_seed_max,
            dynamic_seed_enabled=entity.dynamic_seed_enabled,
            dynamic_seed_multiplier=entity.dynamic_seed_multiplier,
            dynamic_seed_t_threshold=entity.dynamic_seed_t_threshold,
            dynamic_seed_drop_rate=entity.dynamic_seed_drop_rate,
            closing_buy_drop_rate=entity.closing_buy_drop_rate,
            closing_buy_seed_rate=entity.closing_buy_seed_rate,
        )

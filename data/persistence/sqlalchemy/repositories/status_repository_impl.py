"""Status Repository Implementation"""
from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from domain.entities.status import Status
from domain.repositories.status_repository import StatusRepository
from data.persistence.sqlalchemy.models.status_model import StatusModel


class SQLAlchemyStatusRepository(StatusRepository):
    """SQLAlchemy 기반 Status Repository 구현체"""

    def __init__(self, session: Session):
        self.session = session

    def get_status(self) -> Optional[Status]:
        """상태 조회 (단일 레코드 - 첫 번째 레코드 반환)"""
        model = self.session.query(StatusModel).first()
        return self._to_entity(model) if model else None

    def sync_status(self, status: Status) -> None:
        """상태 동기화 (기존 데이터 전체 삭제 후 새로 저장)"""
        try:
            # 1. 기존 데이터 전체 삭제
            self.session.query(StatusModel).delete()

            # 2. 새 데이터 삽입
            model = self._to_model(status)
            self.session.add(model)

            self.session.commit()
        except IntegrityError as e:
            self.session.rollback()
            raise e

    def _to_entity(self, model: StatusModel) -> Status:
        """ORM Model → Entity 변환 (Mapper)"""
        return Status(
            id=model.id,
            deposit_won=model.deposit_won,
            deposit_dollar=model.deposit_dollar,
            withdraw_won=model.withdraw_won,
            withdraw_dollar=model.withdraw_dollar
        )

    def _to_model(self, entity: Status) -> StatusModel:
        """Entity → ORM Model 변환 (Mapper)"""
        model = StatusModel(
            deposit_won=entity.deposit_won,
            deposit_dollar=entity.deposit_dollar,
            withdraw_won=entity.withdraw_won,
            withdraw_dollar=entity.withdraw_dollar
        )
        if entity.id is not None:
            model.id = entity.id
        return model

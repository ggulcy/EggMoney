"""SQLAlchemy 세션 팩토리"""
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from data.persistence.sqlalchemy.core.base import Base
from config import item

# 모든 모델을 import하여 테이블 생성 시 인식되도록 함
from data.persistence.sqlalchemy.models import BotInfoModel, TradeModel, HistoryModel, OrderModel, StatusModel


class SessionFactory:
    """데이터베이스 세션 생성 및 관리"""

    def __init__(self, db_name: str = None):
        # DB 파일명 결정 (사용자별 자동 생성)
        # db_name이 지정되지 않으면 기본값 사용: egg_<admin>.db
        if db_name is None:
            db_name = f"egg_{item.admin.value}.db"
        # db_name이 '_'를 포함하지 않으면 관리자 이름 추가 (예: "egg" -> "egg_chan.db")
        elif "_" not in db_name and not db_name.endswith(".db"):
            db_name = f"{db_name}_{item.admin.value}.db"
        # db_name이 '.db'로 끝나지 않으면 추가
        elif not db_name.endswith(".db"):
            db_name = f"{db_name}.db"

        # DB 파일 경로 설정 (프로젝트 루트 기준)
        # __file__: .../data/persistence/sqlalchemy/core/session_factory.py
        # 프로젝트 루트: .../EggMoney
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
        base_dir = os.path.join(project_root, "data", "persistence", "sqlalchemy", "db")


        os.makedirs(base_dir, exist_ok=True)

        db_path = os.path.join(base_dir, db_name)

        database_url = f'sqlite:///{db_path}'

        # 엔진 생성
        self.engine = create_engine(database_url, echo=False)

        # busy_timeout 설정 (DB 잠김 방지)
        with self.engine.connect() as conn:
            conn.execute(text('PRAGMA busy_timeout = 5000'))

        # 세션 팩토리 생성
        self.SessionLocal = sessionmaker(bind=self.engine)

        # 테이블 생성
        Base.metadata.create_all(self.engine)

    def create_session(self) -> Session:
        """새로운 세션 생성"""
        return self.SessionLocal()

    def __call__(self) -> Session:
        """SessionFactory를 함수처럼 호출 가능하게"""
        return self.create_session()

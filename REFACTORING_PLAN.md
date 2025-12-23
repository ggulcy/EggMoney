# EggMoney 클린 아키텍처 리팩토링 계획서

## 현재 문제점

Presentation/Usecase 레이어에서 Data 레이어의 구현체를 직접 참조하고 있어 증권사 변경 등 외부 서비스 교체 시 대규모 수정이 필요함.

### 직접 참조 현황

| 구현체 | 참조 위치 | 문제점 |
|--------|----------|--------|
| `HantooService` | usecase 5개, routes 5개, scheduler 1개 | 증권사 변경 시 11곳 수정 필요 |
| `send_message_sync` | usecase 3개, routes 1개, scheduler 3개 | 메시지 서비스 변경 시 7곳 수정 필요 |
| `MarketIndicatorRepositoryImpl` | routes 2개, scheduler 1개 | 이미 인터페이스 존재, DI만 개선 필요 |

---

## 리팩토링 목표

1. **ExchangeRepository 인터페이스** 도입 (HantooService 추상화)
2. **MessageRepository 인터페이스** 도입 (send_message_sync 추상화)
3. **중앙 DI 컨테이너** 구축 (의존성 주입 일원화)

### 네이밍 규칙

모든 외부 의존성을 Repository 패턴으로 통일:
- **Repository** = 인터페이스 (domain 레이어)
- **RepositoryImpl** = 구현체 (data 레이어)

| 인터페이스 (domain) | 구현체 (data) |
|---------------------|---------------|
| `BotInfoRepository` | `SQLAlchemyBotInfoRepositoryImpl` |
| `ExchangeRepository` | `HantooExchangeRepositoryImpl` |
| `MessageRepository` | `TelegramMessageRepositoryImpl` |

| 현재 이름 | 변경 후 | 역할 |
|-----------|---------|------|
| `HantooService` | `HantooExchangeRepositoryImpl` | ExchangeRepository 구현체 |
| `HantooClient` | `HantooDataSource` | API 호출, 토큰 관리 |
| `send_message_sync` | `TelegramMessageRepositoryImpl` | MessageRepository 구현체 |
| (내부 함수들) | `TelegramDataSource` | 텔레그램 API 호출 |

---

## 1단계: 인터페이스 정의

### 1.1 ExchangeRepository (증권사 API)

**파일**: `domain/repositories/exchange_repository.py`

```python
from abc import ABC, abstractmethod
from typing import Optional, List
from domain.value_objects import TradeResult

class ExchangeRepository(ABC):
    """증권사 거래 API 인터페이스"""

    # 가격 조회
    @abstractmethod
    def get_price(self, symbol: str) -> Optional[float]: ...

    @abstractmethod
    def get_prev_price(self, symbol: str) -> Optional[float]: ...

    @abstractmethod
    def get_available_buy(self, symbol: str) -> Optional[float]: ...

    @abstractmethod
    def get_available_sell(self, symbol: str) -> Optional[float]: ...

    # 주문 실행
    @abstractmethod
    def buy(self, symbol: str, amount: float, request_price: float) -> Optional[TradeResult]: ...

    @abstractmethod
    def sell(self, symbol: str, amount: float, request_price: float) -> Optional[TradeResult]: ...

    @abstractmethod
    def buy_request_only_odno(self, symbol: str, amount: float, request_price: float) -> Optional[str]: ...

    @abstractmethod
    def sell_request_only_odno(self, symbol: str, amount: float, request_price: float) -> Optional[str]: ...

    # 포트폴리오 조회
    @abstractmethod
    def get_amount_data(self, symbol: str) -> Optional[BalanceResult]: ...

    @abstractmethod
    def get_balance(self, symbol: str, price: float) -> float: ...

    @abstractmethod
    def get_ticker_list_info(self, ticker_list: List[str]) -> List[TickerItem]: ...

    @abstractmethod
    def get_amount_ticker_balance(self, ticker_list: List[str]) -> List[TickerItem]: ...
```

### 1.2 MessageRepository (메시지 발송)

**파일**: `domain/repositories/message_repository.py`

```python
from abc import ABC, abstractmethod
from typing import Optional

class MessageRepository(ABC):
    """메시지 발송 인터페이스"""

    @abstractmethod
    def send_message(self, message: str, photo_path: Optional[str] = None) -> None: ...
```

---

## 2단계: 구현체 수정

### 2.1 HantooService → HantooExchangeRepositoryImpl

**파일 변경:**
- `hantoo_service.py` → `hantoo_exchange_repository_impl.py`
- `hantoo_client.py` → `hantoo_data_source.py`

**hantoo_exchange_repository_impl.py:**
```python
from domain.repositories import ExchangeRepository
from data.external.hantoo.hantoo_data_source import HantooDataSource

class HantooExchangeRepositoryImpl(ExchangeRepository):
    """한국투자증권 ExchangeRepository 구현체"""

    def __init__(self, test_mode: bool = False):
        self.test_mode = test_mode
        self.data_source = HantooDataSource()

    # 기존 메서드들 그대로 유지 (이미 인터페이스와 시그니처 일치)
    def get_price(self, symbol: str) -> Optional[float]: ...
    def buy(self, symbol: str, amount: float, request_price: float) -> Optional[TradeResult]: ...
    # ...
```

**hantoo_data_source.py:**
```python
class HantooDataSource:
    """한국투자증권 API 호출 및 토큰 관리"""
    # 기존 HantooClient 코드 그대로 유지
```

### 2.2 send_message_sync → TelegramMessageRepositoryImpl

**파일 변경:**
- `telegram_client.py` → `telegram_data_source.py`
- 신규: `telegram_message_repository_impl.py`

**telegram_message_repository_impl.py:**
```python
from domain.repositories import MessageRepository
from data.external.telegram.telegram_data_source import TelegramDataSource

class TelegramMessageRepositoryImpl(MessageRepository):
    """텔레그램 MessageRepository 구현체"""

    def __init__(self):
        self.data_source = TelegramDataSource()

    def send_message(self, message: str, photo_path: Optional[str] = None) -> None:
        self.data_source.send_message(message, photo_path)
```

**telegram_data_source.py:**
```python
class TelegramDataSource:
    """텔레그램 API 호출"""
    # 기존 telegram_client.py의 함수들을 클래스로 래핑

    def send_message(self, message: str, photo_path: Optional[str] = None) -> None:
        # 기존 send_message_sync 로직
```

---

## 3단계: DI 컨테이너 구축

**파일**: `config/dependencies.py`

```python
from dataclasses import dataclass
from typing import Optional
from domain.repositories import ExchangeRepository, MessageRepository
from domain.repositories import (
    BotInfoRepository, TradeRepository,
    HistoryRepository, OrderRepository,
    MarketIndicatorRepository
)

@dataclass
class Dependencies:
    """애플리케이션 의존성 컨테이너"""

    # Repositories
    bot_info_repo: BotInfoRepository
    trade_repo: TradeRepository
    history_repo: HistoryRepository
    order_repo: OrderRepository
    market_indicator_repo: MarketIndicatorRepository

    # External Repositories
    exchange_repo: ExchangeRepository
    message_repo: MessageRepository


# 싱글톤 인스턴스
_dependencies: Optional[Dependencies] = None


def init_dependencies(test_mode: bool = False) -> Dependencies:
    """의존성 초기화 (앱 시작 시 한 번만 호출)"""
    global _dependencies

    from data.persistence.sqlalchemy.core import SessionFactory
    from data.persistence.sqlalchemy.repositories import (
        SQLAlchemyBotInfoRepositoryImpl,
        SQLAlchemyTradeRepositoryImpl,
        SQLAlchemyHistoryRepositoryImpl,
        SQLAlchemyOrderRepositoryImpl,
    )
    from data.external.market_data import MarketIndicatorRepositoryImpl
    from data.external.hantoo import HantooExchangeRepositoryImpl
    from data.external.telegram import TelegramMessageRepositoryImpl

    session = SessionFactory().create_session()

    _dependencies = Dependencies(
        bot_info_repo=SQLAlchemyBotInfoRepositoryImpl(session),
        trade_repo=SQLAlchemyTradeRepositoryImpl(session),
        history_repo=SQLAlchemyHistoryRepositoryImpl(session),
        order_repo=SQLAlchemyOrderRepositoryImpl(session),
        market_indicator_repo=MarketIndicatorRepositoryImpl(),
        exchange_repo=HantooExchangeRepositoryImpl(test_mode=test_mode),
        message_repo=TelegramMessageRepositoryImpl(),
    )
    return _dependencies


def get_dependencies() -> Dependencies:
    """의존성 컨테이너 조회 (초기화 후 어디서든 호출 가능)"""
    if _dependencies is None:
        raise RuntimeError("Dependencies not initialized. Call init_dependencies() first.")
    return _dependencies
```

### 3.1 엔트리포인트에서 초기화

**파일**: `main_egg.py` (수정)

```python
# Before: 없음

# After: 앱 시작 시 한 번만 초기화
from config.dependencies import init_dependencies
from config.item import is_test

# 앱 시작 시 의존성 초기화
init_dependencies(test_mode=is_test)
```

### 3.2 기존 직접 주입 코드 제거

**현재 문제**: 각 routes/scheduler에서 매번 직접 생성

```python
# index_routes.py (Before)
session = SessionFactory().create_session()
bot_info_repo = SQLAlchemyBotInfoRepository(session)
trade_repo = SQLAlchemyTradeRepository(session)
history_repo = SQLAlchemyHistoryRepository(session)
hantoo_service = HantooService(test_mode=is_test)
market_usecase = MarketUsecase(
    market_indicator_repo=MarketIndicatorRepositoryImpl(),
    hantoo_service=hantoo_service
)

# index_routes.py (After)
from config.dependencies import get_dependencies
deps = get_dependencies()
market_usecase = MarketUsecase(
    market_indicator_repo=deps.market_indicator_repo,
    exchange_repo=deps.exchange_repo
)
```

### 3.3 제거 대상: 직접 생성 코드

| 파일 | 제거할 코드 |
|------|------------|
| `presentation/web/routes/index_routes.py` | `SessionFactory()`, `SQLAlchemyXxxRepository()`, `HantooService()`, `MarketIndicatorRepositoryImpl()` 직접 생성 |
| `presentation/web/routes/trade_routes.py` | 동일 |
| `presentation/web/routes/history_routes.py` | 동일 |
| `presentation/web/routes/bot_info_routes.py` | 동일 |
| `presentation/web/routes/external_routes.py` | 동일 |
| `presentation/scheduler/scheduler_config.py` | `_initialize_dependencies()` 함수 전체 → `get_dependencies()` 호출로 대체 |
| `presentation/scheduler/message_jobs.py` | `send_message_sync` 직접 import → `deps.message_repo.send_message()` 사용 |
| `presentation/scheduler/trading_jobs.py` | 동일 |

---

## 4단계: Usecase 수정

### 수정 대상 파일

| 파일 | 변경 내용 |
|------|----------|
| `usecase/trading_usecase.py` | `HantooService` → `ExchangeRepository`, `send_message_sync` → `MessageRepository` |
| `usecase/order_usecase.py` | 동일 |
| `usecase/bot_management_usecase.py` | 동일 |
| `usecase/portfolio_status_usecase.py` | `HantooService` → `ExchangeRepository` |
| `usecase/market_usecase.py` | `HantooService` → `ExchangeRepository` (TYPE_CHECKING) |

### 변경 예시 (trading_usecase.py)

```python
# Before
from data.external.hantoo.hantoo_service import HantooService
from data.external import send_message_sync

class TradingUsecase:
    def __init__(self, ..., hantoo_service: HantooService):
        self.hantoo_service = hantoo_service

    def some_method(self):
        price = self.hantoo_service.get_price("AAPL")
        send_message_sync("거래 완료")

# After
from domain.repositories import ExchangeRepository, MessageRepository

class TradingUsecase:
    def __init__(self, ..., exchange_repo: ExchangeRepository, message_repo: MessageRepository):
        self.exchange_repo = exchange_repo
        self.message_repo = message_repo

    def some_method(self):
        price = self.exchange_repo.get_price("AAPL")
        self.message_repo.send_message("거래 완료")
```

**내부 호출 변경 사항:**
- `self.hantoo_service.xxx()` → `self.exchange_repo.xxx()`
- `send_message_sync(msg)` → `self.message_repo.send_message(msg)`

---

## 5단계: Presentation 수정

### 수정 대상 파일

| 파일 | 변경 내용 |
|------|----------|
| `presentation/web/routes/index_routes.py` | DI 컨테이너 사용 |
| `presentation/web/routes/trade_routes.py` | DI 컨테이너 사용 |
| `presentation/web/routes/history_routes.py` | DI 컨테이너 사용 |
| `presentation/web/routes/bot_info_routes.py` | DI 컨테이너 사용 |
| `presentation/web/routes/external_routes.py` | DI 컨테이너 사용 |
| `presentation/scheduler/scheduler_config.py` | DI 컨테이너 사용 |
| `presentation/scheduler/message_jobs.py` | `MessageRepository` 주입 |
| `presentation/scheduler/trading_jobs.py` | `MessageRepository` 주입 |

### 변경 예시 (routes)

```python
# Before
from data.external.hantoo.hantoo_service import HantooService
hantoo_service = HantooService(test_mode=is_test)

# After
from config.dependencies import get_dependencies
deps = get_dependencies()
# deps.exchange_repo, deps.message_repo 사용
```

---

## 파일 구조 (최종)

```
EggMoney/
├── domain/
│   ├── repositories/            # Repository 인터페이스
│   │   ├── __init__.py
│   │   ├── bot_info_repository.py
│   │   ├── trade_repository.py
│   │   ├── exchange_repository.py   # [NEW] 증권사 API
│   │   └── message_repository.py    # [NEW] 메시지 발송
│   ├── entities/
│   └── value_objects/
│
├── data/
│   ├── external/
│   │   ├── hantoo/
│   │   │   ├── hantoo_exchange_repository_impl.py  # [RENAME] ExchangeRepository 구현체
│   │   │   ├── hantoo_data_source.py               # [RENAME] API 호출, 토큰 관리
│   │   │   └── hantoo_models.py
│   │   ├── telegram/
│   │   │   ├── telegram_message_repository_impl.py # [NEW] MessageRepository 구현체
│   │   │   └── telegram_data_source.py             # [RENAME] 텔레그램 API 호출
│   │   └── market_data/
│   └── persistence/
│
├── config/
│   ├── dependencies.py          # [NEW] DI 컨테이너
│   └── item.py
│
├── usecase/                     # [수정] 인터페이스 의존으로 변경
│
└── presentation/                # [수정] DI 컨테이너 사용
```

---

## 작업 순서

### Phase 1: 인터페이스 정의
1. `domain/repositories/exchange_repository.py` 인터페이스 생성
2. `domain/repositories/message_repository.py` 인터페이스 생성
3. `domain/repositories/__init__.py` 수정 (새 인터페이스 export 추가)

### Phase 2: 구현체 리네임 및 수정
4. `hantoo_service.py` → `hantoo_exchange_repository_impl.py` 리네임 및 ExchangeRepository 상속 추가
5. `hantoo_client.py` → `hantoo_data_source.py` 리네임
6. `data/external/hantoo/__init__.py` 수정 (export 변경)
7. `telegram_client.py` → `telegram_data_source.py` 리네임 및 클래스화
8. `telegram_message_repository_impl.py` 신규 생성
9. `data/external/telegram/__init__.py` 생성 (export 추가)
10. 기존 SQLAlchemy Repository 구현체들 Impl 접미사 추가
    - `bot_info_repository_impl.py`: `SQLAlchemyBotInfoRepository` → `SQLAlchemyBotInfoRepositoryImpl`
    - `trade_repository_impl.py`: `SQLAlchemyTradeRepository` → `SQLAlchemyTradeRepositoryImpl`
    - `history_repository_impl.py`: `SQLAlchemyHistoryRepository` → `SQLAlchemyHistoryRepositoryImpl`
    - `order_repository_impl.py`: `SQLAlchemyOrderRepository` → `SQLAlchemyOrderRepositoryImpl`
11. `data/persistence/sqlalchemy/repositories/__init__.py` 수정 (export 변경)

### Phase 3: DI 컨테이너
12. `config/dependencies.py` DI 컨테이너 신규 생성
13. `main_egg.py`에 `init_dependencies()` 호출 추가

### Phase 4: Usecase 레이어 수정 (5개 파일)
14. `usecase/trading_usecase.py` - import 및 생성자, 내부 호출 변경
15. `usecase/order_usecase.py` - 동일
16. `usecase/bot_management_usecase.py` - 동일
17. `usecase/portfolio_status_usecase.py` - 동일
18. `usecase/market_usecase.py` - 동일

### Phase 5: Presentation 레이어 수정 (8개 파일)
19. `presentation/web/routes/index_routes.py` - DI 컨테이너 사용으로 변경
20. `presentation/web/routes/trade_routes.py` - 동일
21. `presentation/web/routes/history_routes.py` - 동일
22. `presentation/web/routes/bot_info_routes.py` - 동일
23. `presentation/web/routes/external_routes.py` - 동일
24. `presentation/scheduler/scheduler_config.py` - `_initialize_dependencies()` 제거, `get_dependencies()` 사용
25. `presentation/scheduler/message_jobs.py` - `send_message_sync` → `message_repo.send_message()`
26. `presentation/scheduler/trading_jobs.py` - 동일

### Phase 6: 검증
27. 전체 import 오류 확인
28. 앱 실행 테스트
29. 주요 기능 동작 확인

---

## 예상 효과

| 항목 | Before | After |
|------|--------|-------|
| 증권사 변경 시 수정 파일 | 11개 | 1개 (`config/dependencies.py`) |
| 메시지 서비스 변경 시 | 7개 | 1개 |
| 테스트 Mock 주입 | 어려움 | 용이 (인터페이스 기반) |
| 새 증권사 추가 | 전체 수정 | 구현체만 추가 |

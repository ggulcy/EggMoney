# EggMoney

기술지표 기반 자동 매매 시스템 (Clean Architecture)

## 프로젝트 개요

| 항목 | 내용 |
|------|------|
| 언어 | Python 3.13 |
| 아키텍처 | Clean Architecture |
| 핵심 기능 | 기술지표 기반 자동 매매, TWAP 분할 매매, DCA 전략 |

## 기술 스택

| 카테고리 | 기술 |
|---------|------|
| 웹 프레임워크 | Flask |
| ORM | SQLAlchemy |
| 스케줄러 | APScheduler |
| 외부 API | 한국투자증권, Google Sheets, Telegram, yfinance |
| 데이터 분석 | pandas, numpy, ta (기술지표) |

## 프로젝트 구조

```
EggMoney/
├── config/                                 # 환경 설정 및 유틸리티
│   ├── __init__.py
│   ├── item.py                             # 전역 상수 (BotAdmin, ticker_list, is_test)
│   ├── key_store.py                        # API 키 저장 (shelve 기반)
│   ├── print_db.py                         # DB 데이터 출력 유틸
│   ├── logging_config.py                   # 로깅 설정
│   └── util.py                             # 유틸 함수 (get_schedule_times 등)
│
├── domain/                                 # 비즈니스 로직 (Clean Architecture 핵심)
│   ├── __init__.py
│   ├── entities/                           # 엔티티 (비즈니스 객체)
│   │   ├── __init__.py
│   │   ├── bot_info.py                     # 봇 설정 정보 (name, symbol, seed, profit_rate...)
│   │   ├── trade.py                        # 거래 정보 (보유 중인 포지션)
│   │   ├── order.py                        # TWAP 분할 주문
│   │   ├── history.py                      # 완료된 거래 기록
│   │   └── status.py                       # 포트폴리오 상태 (시간별 스냅샷)
│   │
│   ├── repositories/                       # 저장소 인터페이스 (추상 클래스)
│   │   ├── __init__.py
│   │   ├── bot_info_repository.py          # BotInfo CRUD 인터페이스
│   │   ├── trade_repository.py             # Trade CRUD + 평단가/총투자금 조회
│   │   ├── order_repository.py             # Order CRUD (TWAP 주문)
│   │   ├── history_repository.py           # History 조회 (거래 이력)
│   │   └── status_repository.py            # Status 저장/조회
│   │
│   └── value_objects/                      # 값 객체
│       ├── __init__.py
│       ├── point_loc.py                    # PointLoc Enum (p1, p1_2, p2_3)
│       ├── trade_type.py                   # TradeType Enum (Buy, Sell, Sell_1_4, Sell_3_4)
│       ├── trade_result.py                 # TradeResult (체결가, 수량, 총액)
│       └── order_type.py                   # OrderType Enum (TWAP 주문 타입)
│
├── data/                                   # 데이터 접근 계층
│   ├── __init__.py
│   │
│   ├── persistence/                        # DB 영속성
│   │   ├── __init__.py
│   │   └── sqlalchemy/
│   │       ├── __init__.py
│   │       ├── core/                       # SQLAlchemy 기반
│   │       │   ├── __init__.py
│   │       │   ├── base.py                 # ORM Base 클래스
│   │       │   └── session_factory.py      # 세션 팩토리 (egg_[admin].db)
│   │       │
│   │       ├── models/                     # ORM 모델 (테이블 매핑)
│   │       │   ├── __init__.py
│   │       │   ├── bot_info_model.py       # bot_info 테이블
│   │       │   ├── trade_model.py          # trade 테이블
│   │       │   ├── order_model.py          # order 테이블
│   │       │   ├── history_model.py        # history 테이블
│   │       │   └── status_model.py         # status 테이블
│   │       │
│   │       └── repositories/               # 저장소 구현체
│   │           ├── __init__.py
│   │           ├── bot_info_repository_impl.py
│   │           ├── trade_repository_impl.py
│   │           ├── order_repository_impl.py
│   │           ├── history_repository_impl.py
│   │           └── status_repository_impl.py
│   │
│   └── external/                           # 외부 API
│       ├── __init__.py
│       ├── telegram_client.py              # 텔레그램 메시지 전송
│       │
│       ├── hantoo/                         # 한국투자증권 API
│       │   ├── __init__.py
│       │   ├── hantoo_client.py            # REST API 클라이언트
│       │   ├── hantoo_models.py            # 데이터 모델 (Pydantic)
│       │   └── hantoo_service.py           # 서비스 (가격조회, 매수/매도, 잔고)
│       │
│       ├── sheets/                         # Google Sheets API
│       │   ├── __init__.py
│       │   ├── sheets_client.py            # Sheets API 클라이언트
│       │   ├── sheets_models.py            # 데이터 모델
│       │   └── sheets_service.py           # 서비스 (잔고 동기화)
│       │
│       └── market_data/                    # 시장 데이터 (yfinance)
│           ├── __init__.py
│           ├── market_data_client.py       # yfinance 클라이언트
│           ├── market_data_service.py      # 지표 계산 서비스
│           └── market_indicator_repository_impl.py  # 기술지표 저장소
│
├── usecase/                                # 비즈니스 유스케이스
│   ├── __init__.py
│   ├── trading_usecase.py                  # 매매 조건 판단 (execute_trading, force_sell)
│   ├── order_usecase.py                    # TWAP 주문 실행 + DB 저장
│   ├── market_analysis_usecase.py          # 시장 지표 분석 (VIX, RSI)
│   ├── bot_management_usecase.py           # 봇 관리 (check_bot_sync, update)
│   └── portfolio_status_usecase.py         # 포트폴리오 조회 + 시트 동기화
│
├── presentation/                           # 프레젠테이션 계층
│   ├── __init__.py
│   │
│   ├── scheduler/                          # APScheduler 자동화
│   │   ├── __init__.py
│   │   ├── scheduler_config.py             # 스케줄러 설정 + 의존성 초기화 (DI)
│   │   ├── trading_jobs.py                 # 거래 작업 (trade_job, twap_job, force_sell_job)
│   │   └── message_jobs.py                 # 메시지 작업 (daily_job, sync 등)
│   │
│   └── web/                                # Flask 웹 서버
│       ├── __init__.py
│       ├── routes/
│       │   ├── __init__.py                 # Blueprint 노출
│       │   ├── index_routes.py             # 메인 페이지
│       │   ├── bot_info_routes.py          # 봇 정보 CRUD
│       │   ├── trade_routes.py             # 거래 관리 (Trade + History)
│       │   └── status_routes.py            # 포트폴리오 상태 조회
│       │
│       ├── templates/                      # HTML 템플릿 (Jinja2)
│       │   ├── index.html                  # 메인 네비게이션
│       │   ├── bot_info.html               # 봇 정보 페이지
│       │   ├── trade.html                  # 거래 페이지
│       │   └── status.html                 # 입출금 관리 페이지
│       │
│       └── static/
│           └── style.css                   # 스타일 (모바일 반응형)
│
├── main_egg.py                             # Flask + APScheduler 진입점
├── migrate_from_egg.py                     # egg → EggMoney DB 마이그레이션 스크립트
├── requirements.txt                        # 의존성 패키지
└── .env                                    # 환경 변수
```

## Clean Architecture 레이어

**의존성 방향:**
```
Domain ← Data ← Usecase ← Presentation
```

| 레이어 | 역할 | 예시 |
|--------|------|------|
| **Domain** | 비즈니스 핵심 (엔티티, 인터페이스) | BotInfo, Trade, TradeRepository |
| **Data** | 데이터 소스 구현 | SQLAlchemyTradeRepository, HantooService |
| **Usecase** | 비즈니스 로직 구현 | TradingUsecase, OrderUsecase |
| **Presentation** | 사용자 인터페이스 | Flask Routes, APScheduler Jobs |

## 주요 엔티티

| 엔티티 | 설명 | 주요 필드 |
|--------|------|----------|
| **BotInfo** | 봇 설정 | name, symbol, seed, profit_rate, t_div, max_tier, active, point_loc |
| **Trade** | 보유 중인 거래 | name, purchase_price, amount, total_price, trade_type |
| **Order** | TWAP 분할 주문 | name, total_amount, executed_count, order_type |
| **History** | 완료된 거래 | name, buy_price, sell_price, profit, profit_rate, timestamp |
| **Status** | 포트폴리오 상태 | timestamp, total_value, daily_profit |

## 핵심 Usecase

| Usecase | 역할 | 주요 메서드 |
|---------|------|------------|
| **TradingUsecase** | 매매 조건 판단 | `execute_trading()`, `force_sell()` |
| **OrderUsecase** | TWAP 주문 실행 | `create_buy_order()`, `create_sell_order()`, `execute_order()` |
| **BotManagementUsecase** | 봇 관리 | `check_bot_sync()`, `get_all_bot_info_with_t()`, `update_bot_info()` |
| **PortfolioStatusUsecase** | 포트폴리오 조회 | `get_portfolio_summary()`, `sync_balance_to_sheets()` |
| **MarketAnalysisUsecase** | 시장 지표 분석 | `get_vix_indicator()`, `get_rsi_indicator()` |

## 매매 알고리즘

### 매도 조건
1. **익절가 돌파**: 현재가 > 평단가 × (1 + profit_rate)
2. **%지점가 돌파**: 현재가 > 평단가 × (1 + point)
3. **T가 Max Tier 이상**: 손절 (레버리지 초과)

### 매도 수량
| 조건 | 매도 비율 |
|------|----------|
| 조건 2개 만족 | 전체 매도 (100%) |
| 익절가만 만족 | 3/4 매도 |
| %지점만 만족 | 1/4 매도 |

### 매수 조건
1. **평단가보다 낮음** (is_check_buy_avr_price)
2. **%지점가보다 낮음** (is_check_buy_t_div_price)

### 매수 금액
- 만족 조건 수 / 활성 조건 수 × 시드
- 급락 시 (T < 2/3 Max Tier): 시드 30~50% 증액

### 리밸런싱
- **T = 총 투자금 / 시드** (레버리지 배수)
- 점진적 매수로 평단가 낮춤 (DCA 전략)

## 거래 흐름

```
scheduler/trade_job (정해진 시간에 실행)
    │
    ▼
TradingUsecase.execute_trading()
    ├── _execute_sell() → 매도 조건 체크
    │   └── _calculate_sell_amount() → 매도 수량 결정
    └── _execute_buy() → 매수 조건 체크
        └── _check_big_drop() → 급락 시 시드 조정
    │
    ▼
OrderUsecase.create_buy/sell_order()
    └── Order 테이블에 주문 저장
    │
    ▼
scheduler/twap_job (5분마다 실행)
    │
    ▼
OrderUsecase.execute_order()
    ├── HantooService.buy/sell() → 실제 매매 실행
    └── Trade/History DB 업데이트
```

## 실행 방법

```bash
# 1. 의존성 설치
pip install -r requirements.txt

# 2. 환경 변수 설정 (.env 파일 생성)
IS_TEST=false
ADMIN=chan
API_KEY=your_api_key
SECRET_KEY=your_secret_key
HOST=0.0.0.0
PORT=5000

# 3. 실행
python main_egg.py
```

## DB 스키마

**DB 파일**: `egg_[admin].db` (SQLite, 5개 테이블 통합)

| 테이블 | 용도 | Primary Key |
|--------|------|-------------|
| bot_info | 봇 설정 정보 | name (String) |
| trade | 보유 중인 거래 | name (String) |
| order | TWAP 미체결 주문 | id (Integer) |
| history | 완료된 거래 기록 | id (Integer) |
| status | 포트폴리오 스냅샷 | id (Integer) |

## 핵심 패턴

| 패턴 | 설명 |
|------|------|
| **Dependency Injection** | scheduler_config.py에서 모든 의존성 초기화 및 주입 |
| **Repository Pattern** | 추상 인터페이스 (domain) + 구현체 (data) 분리 |
| **Late Commit** | 모든 변경 후 한 번에 commit |
| **Mapper Pattern** | ORM Model ↔ Domain Entity 분리 (`_to_entity()`, `_to_model()`) |

## 스케줄러 작업

| 작업 | 실행 시간 | 역할 |
|------|----------|------|
| **trade_job** | 설정된 시간 | 매매 조건 판단 + 주문서 생성 |
| **twap_job** | 5분마다 | TWAP 분할 주문 실행 |
| **daily_job** | 하루 1회 | 포트폴리오 메시지 + 시트 동기화 + 봇 sync |

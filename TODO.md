================================================================================
📋 EggMoney 프로젝트 - Clean Architecture 마이그레이션 TODO
================================================================================

## 🎯 작업 목표

**egg 프로젝트를 EggMoney로 Clean Architecture 기반으로 완전히 재구축**

- ✅ **전략 유지**: egg의 기술지표 기반 단기 반복 매매(DCA) 전략은 그대로 유지
- ✅ **아키텍처 변경**: 함수형/절차적 구조 → Clean Architecture (Domain/Data/Usecase/Presentation)
- ✅ **DB 통합**: 5개 분리 DB → 1개 통합 DB (egg_chan.db, 5개 테이블)
- ✅ **TWAP 매매**: Order Entity를 통한 분할 매매 구현
- ✅ **참고 프로젝트**: **vr → ValueRebalancing 마이그레이션 사례 필수 참고**

## 📝 프로젝트 요약

### 배경
- **원본 (egg)**: `/Users/chanhypark/workspace/private/python/egg` (레거시 프로젝트)
- **목표 (EggMoney)**: `/Users/chanhypark/workspace/private/python/EggMoney` (Clean Architecture)
- **참고 사례**:
  - **vr (레거시)**: `/Users/chanhypark/workspace/private/python/vr`
  - **ValueRebalancing (완료)**: `/Users/chanhypark/workspace/private/python/ValueRebalancing`
  - ⭐ vr → ValueRebalancing 마이그레이션 과정을 egg → EggMoney에 동일하게 적용

### 왜 마이그레이션을 하는가?
1. **유지보수성 향상**: 레이어 분리로 코드 변경 시 영향 범위 최소화
2. **테스트 용이성**: Repository 패턴과 DI로 Mock 주입 가능
3. **확장성**: 새로운 기능 추가 시 기존 코드 수정 최소화
4. **일관성**: ValueRebalancing과 동일한 구조로 프로젝트 통일

### 핵심 원칙
- **vr → ValueRebalancing 마이그레이션을 반드시 참고**
  - `/Users/chanhypark/workspace/private/python/ValueRebalancing/STRUCTURE.txt` 필수 읽기
  - Domain/Data/Usecase/Presentation 레이어 구조 동일하게 적용
  - Late Commit, DI, Mapper, Repository Pattern 모두 적용

## 🚀 시작 방법

1. **ValueRebalancing STRUCTURE.txt 먼저 읽기**
   ```bash
   cat /Users/chanhypark/workspace/private/python/ValueRebalancing/STRUCTURE.txt
   ```

2. **egg 프로젝트 구조 파악**
   - main.py: Flask 앱
   - seed_module.py: 기술지표 분석
   - trade_module.py: 매매 로직
   - db_usecase.py: DB 저장 로직

3. **Phase 1부터 순차 진행**
   - Domain Layer → Data Layer → Usecase Layer → Presentation Layer

## 📊 전체 진행률: 88/88 파일 (100%) ✅ 프로젝트 완성!

================================================================================

```
EggMoney/
│
├── config/                                      🟢 100% (6개 파일) ✅
│   ├── [✓] __init__.py                          전역 설정 노출
│   ├── [✓] item.py                              전역 상수 (BotAdmin, ticker_list)
│   ├── [✓] key_store.py                         API 키, 플래그 저장 (shelve 기반) - egg 이관 ✅
│   ├── [✓] print_db.py                          DB 데이터 출력 유틸 ✅
│   ├── [✓] logging_config.py                    로깅 설정 (파일+콘솔) - 제거됨 (print로 통일)
│   └── [✓] util.py                              유틸 함수 - egg/utils/util.py 이관 ✅
│       - get_schedule_times()                   스케줄 시간 설정 (msg_times, job_times, twap_times)
│
├── domain/                                      🟢 100% (18개 파일) ✅
│   ├── entities/
│   │   ├── [✓] __init__.py
│   │   ├── [✓] bot_info.py                      BotInfo 엔티티
│   │   ├── [✓] trade.py                         Trade 엔티티
│   │   ├── [✓] order.py                         Order 엔티티 (TWAP 매매) ✅
│   │   ├── [✓] history.py                       History 엔티티 (거래 이력) ✅
│   │   └── [✓] status.py                        Status 엔티티 (포트폴리오) ✅
│   ├── repositories/
│   │   ├── [✓] __init__.py
│   │   ├── [✓] bot_info_repository.py           BotInfo 저장소 인터페이스
│   │   ├── [✓] trade_repository.py              Trade 저장소 인터페이스
│   │   ├── [✓] order_repository.py              Order 저장소 인터페이스 ✅
│   │   ├── [✓] history_repository.py            History 저장소 인터페이스 ✅
│   │   └── [✓] status_repository.py             Status 저장소 인터페이스 ✅
│   ├── value_objects/
│   │   ├── [✓] __init__.py
│   │   ├── [✓] point_loc.py                     PointLoc Enum (P1, P1_2, P2_3)
│   │   ├── [✓] trade_type.py                    TradeType Enum (BUY/SELL/SELL_1_4/SELL_3_4)
│   │   ├── [✓] trade_result.py                  TradeResult 값 객체
│   │   └── [✓] order_type.py                    OrderType Enum (TWAP용) ✅
│   └── [✓] __init__.py
│
├── data/                                        🟢 100% (29개 파일) ✅
│   ├── persistence/
│   │   └── sqlalchemy/
│   │       ├── core/
│   │       │   ├── [✓] __init__.py
│   │       │   ├── [✓] base.py                  SQLAlchemy Base
│   │       │   └── [✓] session_factory.py       세션 팩토리 (egg_[admin].db)
│   │       ├── models/
│   │       │   ├── [✓] __init__.py
│   │       │   ├── [✓] bot_info_model.py        BotInfo ORM 모델
│   │       │   ├── [✓] trade_model.py           Trade ORM 모델
│   │       │   ├── [✓] order_model.py           Order ORM 모델 (TWAP) ✅
│   │       │   ├── [✓] history_model.py         History ORM 모델 ✅
│   │       │   └── [✓] status_model.py          Status ORM 모델 ✅
│   │       ├── repositories/
│   │       │   ├── [✓] __init__.py
│   │       │   ├── [✓] bot_info_repository_impl.py  BotInfo 저장소 구현
│   │       │   ├── [✓] trade_repository_impl.py     Trade 저장소 구현
│   │       │   ├── [✓] order_repository_impl.py     Order 저장소 구현 (TWAP) ✅
│   │       │   ├── [✓] history_repository_impl.py   History 저장소 구현 ✅
│   │       │   └── [✓] status_repository_impl.py    Status 저장소 구현 ✅
│   │       └── [✓] __init__.py
│   ├── external/
│   │   ├── [✓] __init__.py                      ✅
│   │   ├── [✓] telegram_client.py               텔레그램 클라이언트 - 하나의 함수로 통합 ✅
│   │   ├── hantoo/
│   │   │   ├── [✓] __init__.py                  ✅
│   │   │   ├── [✓] hantoo_client.py             한투 API 클라이언트 - egg 이관 ✅
│   │   │   ├── [✓] hantoo_models.py             한투 데이터 모델 - egg 이관 ✅
│   │   │   └── [✓] hantoo_service.py            한투 서비스 (가격, 매매) - 새로 작성 ✅
│   │   └── sheets/
│   │       ├── [✓] __init__.py                  ✅
│   │       ├── [✓] sheets_client.py             Google Sheets 클라이언트 - VR 이관 ✅
│   │       ├── [✓] sheets_models.py             Sheets 데이터 모델 - VR 이관 ✅
│   │       └── [✓] sheets_service.py            Sheets 서비스 (잔고 동기화) - VR 참고 + egg 수정 ✅
│   ├── [✓] __init__.py
│   └── [✓] persistence/__init__.py
│
├── usecase/                                     🟢 100% (6개 파일) ✅
│   ├── [✓] __init__.py                          ✅
│   ├── [✓] trading_usecase.py                   매매 조건 판단 + 주문 정보 반환 (튜플) ✅
│       - execute_trading()                      매매 실행 (매도 → 매수)
│       - force_sell()                           강제 매도 → Optional[tuple[amount, type]] 반환
│       - _execute_sell()                        매도 조건 체크 및 실행
│       - _execute_buy()                         매수 조건 체크 및 실행
│       - _calculate_sell_amount()               매도 수량 계산
│       - _check_big_drop()                      급락 시 시드 조정
│       - _request_buy()                         매수 정보 튜플 반환 (seed, type)
│       - _request_sell()                        매도 정보 튜플 반환 (amount, type)
│   ├── [✓] order_usecase.py                     TWAP 주문 실행 + DB 저장 ✅
│       - create_buy_order()                     매수 주문서 생성
│       - create_sell_order()                    매도 주문서 생성
│       - execute_order()                        TWAP 주문 1회 실행
│       - _execute_single_buy()                  개별 매수 실행
│       - _execute_single_sell()                 개별 매도 실행
│       - _complete_order()                      주문 완료 처리
│       - _save_buy_to_db()                      매수 DB 저장 (Trade 리밸런싱)
│       - _save_sell_to_db()                     매도 DB 저장 + History
│       - _save_history()                        History 저장 + added_seed 업데이트
│       - _finish_cycle()                        사이클 종료 메시지
│       - _merge_trade_results()                 거래 결과 병합 (order.order_type 사용)
│   ├── [✓] market_analysis_usecase.py           시장 지표 분석 (VIX, RSI) ✅
│       - get_vix_indicator()                    VIX 변동성 지수 조회
│       - get_rsi_indicator()                    RSI 지수 계산 및 조회
│       - get_moving_average_price()             이동평균가 계산 (트레이드용)
│       - get_market_indicators_summary()        시장 지표 요약 (VIX + RSI)
│   ├── [✓] bot_management_usecase.py            봇 관리 (자동화 + 라우터) ✅
│       - check_bot_sync()                       T값 기반 조건 자동 조정
│       - get_all_bot_info_with_t()              모든 봇 정보 + T값 조회 (라우터용)
│       - update_bot_info()                      봇 정보 업데이트 (라우터용)
│       - get_bot_info_by_name()                 이름으로 봇 정보 조회
│   └── [✓] portfolio_status_usecase.py          포트폴리오 현황 + 시트 동기화 ✅
│       - get_trade_status()                     거래 상태 조회
│       - get_portfolio_summary()                포트폴리오 요약 조회
│       - get_today_profit()                     오늘의 수익 조회
│       - get_profit_summary()                   연도별/월별 수익 요약 조회
│       - sync_balance_to_sheets()               잔고 → Sheets 동기화
│       - sync_status_from_sheets()              Sheets → Status DB 동기화
│
├── presentation/                                🟢 100% (16/16개 파일) ✅
│   ├── web/
│   │   ├── [✓] __init__.py                      ✅
│   │   ├── routes/
│   │   │   ├── [✓] __init__.py                  ✅ (bot_info_bp, trade_bp, status_bp, index_bp export)
│   │   │   ├── [✓] index_routes.py              메인 페이지 라우터 ✅
│   │   │   ├── [✓] bot_info_routes.py           봇 정보 관리 라우터 ✅
│   │   │   ├── [✓] trade_routes.py              거래 관리 라우터 (Trade + History CRUD) ✅
│   │   │   └── [✓] status_routes.py             입출금 관리 라우터 ✅
│   │   ├── templates/
│   │   │   ├── [✓] index.html                   메인 네비게이션 - 카드 그리드 디자인 ✅
│   │   │   ├── [✓] bot_info.html                봇 정보 페이지 - egg 개선 완료 ✅
│   │   │   ├── [✓] trade.html                   거래 페이지 (티커 그룹화 + CRUD) ✅
│   │   │   └── [✓] status.html                  입출금 관리 페이지 - egg 개선 완료 ✅
│   │   └── static/
│   │       └── [✓] style.css                    통일 스타일 (모바일 반응형) ✅
│   ├── scheduler/
│   │   ├── [✓] __init__.py                      ✅ (scheduler_config export 추가)
│   │   ├── [✓] scheduler_config.py              APScheduler 설정 (egg의 schedule_module.py 이관) ✅
│   │       - _initialize_dependencies()         의존성 초기화 (tuple 반환)
│   │       - _create_trade_job()                trade_job 팩토리 (클로저)
│   │       - _create_twap_job()                 twap_job 팩토리 (클로저)
│   │       - _create_msg_job()                  msg_job 팩토리 (클로저)
│   │       - _register_jobs()                   CronTrigger 방식 작업 등록 (중복 제거)
│   │       - start_scheduler()                  스케줄러 시작 + 초기화 job 실행
│   │       - stop_scheduler()                   스케줄러 중지
│   │   ├── [✓] trading_jobs.py                  거래 작업 (Usecase 조합) ✅
│   │       - trade_job()                        메인 거래 (조건 판단 + 주문서 생성)
│   │       - twap_job()                         TWAP 실행 (주문서 실행)
│   │       - force_sell_job()                   강제 매도 (라우터용)
│   │       - _execute_trade_for_bot()           개별 봇 거래 실행
│   │   └── [✓] message_jobs.py                  메시지 + 시트 동기화 작업 ✅
│   │       - send_trade_status_message()        거래 상태 메시지
│   │       - send_portfolio_summary_message()   포트폴리오 요약 메시지 (시장 지표 포함)
│   │       - send_today_profit_message()        오늘의 수익 메시지 (사진 포함)
│   │       - sync_balance_to_sheets()           잔고 → Sheets 동기화
│   │       - sync_status_from_sheets()          Sheets → Status DB 동기화
│   │       - sync_bots()                        봇 동기화 체크 (daily_job에 통합)
│   │       - daily_job()                        일일 통합 작업 (메시지 + 봇동기화)
│   └── [✓] __init__.py                          ✅
│
├── [✓] migrate_from_egg.py                      egg DB → EggMoney DB 마이그레이션 스크립트 ✅
├── [✓] test_message.py                          메시지 전송 테스트 (함수형) ✅
├── [✓] test_sheets.py                           시트 동기화 테스트 (함수형) ✅
├── [✓] test_send_message.py                     통합 테스트 (daily_job 포함) ✅
├── [✓] test_portfolio_status.py                 포트폴리오 상태 테스트 ✅
├── [✓] test_bot_management.py                   봇 관리 테스트 ✅
├── [✓] test_trading.py                          매매 조건 판단 테스트 ✅
├── [✓] test_order_usecase.py                    매수 주문서 생성 테스트 ✅
├── [✓] test_full_flow.py                        매수/매도 전체 플로우 통합 테스트 ✅
├── [✓] test_trading_jobs.py                     TradingJobs 기본 테스트 ✅
├── [✓] test_complete_flow.py                    완전한 거래 플로우 통합 테스트 ✅
├── [✓] main_egg.py                              Flask + APScheduler 통합 ✅ (egg의 APScheduler 스타일 적용)
│   - get_schedule_times()                       스케줄 시간 설정 읽기 (config_store/util)
│   - run_initial_jobs()                         초기화 작업 (메시지, CSV, 봇 sync 등)
│   - start_scheduler()                          APScheduler 시작 (Lock으로 동시 호출 방지)
│   - job(), msg_job(), twap_job()               스케줄 작업들 (TradingJobs/MessageJobs 조합)
│   - remove_csv()                               CSV 파일 정리
├── [✓] requirements.txt                         의존성 패키지 ✅ (APScheduler 추가)
├── [✓] .gitignore                               Git 무시 파일 (google_api_secret.json 포함) ✅
└── [ ] README.md                                프로젝트 설명
```

================================================================================
📌 Clean Architecture 레이어 구조
================================================================================

의존성 방향: Domain ← Data ← Usecase ← Presentation

1. Domain Layer (가장 내부, 비즈니스 핵심)
   - 역할: 엔티티, Repository 인터페이스, 값 객체
   - 특징: 외부 의존성 없음, 순수 비즈니스 로직
   - 예시: BotInfo, Trade, History, Status 엔티티

2. Data Layer (인프라)
   - 역할: 데이터 소스 구현
   - Persistence: SQLAlchemy ORM, 저장소 구현체
   - External: Telegram, Hantoo API, Google Sheets 클라이언트
   - 예시: SQLAlchemyTradeRepository, HantooService

3. Usecase Layer (애플리케이션 비즈니스 로직)
   - 역할: 유즈케이스별 워크플로우 구현
   - 특징: Domain + Data 조합, 트랜잭션 관리
   - 예시: TradingUsecase (조건 판단), OrderUsecase (실행 + DB 저장)
   - 의존성: TradingUsecase → OrderUsecase → Repository + Service

4. Presentation Layer (사용자 인터페이스)
   - Web: Flask 기반 웹 UI (CRUD, 조회)
   - Scheduler: APScheduler 자동화 (Usecase 조합)
   - 예시: TradingJobs (trade_job, twap_job), MessageJobs

5. Config (Cross-Cutting Concerns)
   - 역할: 전역 설정, 로깅, 유틸리티
   - 특징: 모든 레이어에서 접근 가능

================================================================================
📊 egg → EggMoney 매핑표
================================================================================

egg (레거시)                    EggMoney (Clean Architecture)
─────────────────────────────────────────────────────────────
item.py                      →  config/item.py
seed_module.py               →  usecase/market_analysis_usecase.py
trade_module.py              →  usecase/trading_usecase.py (조건 판단)
order_module.py              →  usecase/order_usecase.py (TWAP 실행)
db_usecase.py                →  usecase/order_usecase.py (DB 저장 내부 메서드)
market_usecase.py            →  data/external/hantoo/hantoo_service.py
repository/bot_info_*.py     →  domain/repositories/bot_info_repository.py + 구현체
repository/trade_*.py        →  domain/repositories/trade_repository.py + 구현체
repository/order_*.py        →  domain/repositories/order_repository.py + 구현체 (TWAP)
repository/history_*.py      →  domain/repositories/history_repository.py + 구현체
repository/status_*.py       →  domain/repositories/status_repository.py + Usecase
repository/sheet_*.py        →  data/external/sheets/sheets_service.py
utils/telegram_module.py     →  data/external/telegram_client.py (egg 전용, VR과 다름)
utils/util.py                →  config/util.py
utils/config_store.py        →  config/key_store.py (shelve 기반)
hantoo/hantoo_market.py      →  data/external/hantoo/hantoo_service.py
hantoo/hantoo_request.py     →  data/external/hantoo/hantoo_client.py
hantoo/hantoo_item.py        →  data/external/hantoo/hantoo_models.py
schedule_module.py           →  presentation/scheduler/scheduler_config.py
main.py (job, twap_job)      →  presentation/scheduler/trading_jobs.py
main.py (Flask)              →  presentation/web/routes/*.py + main_egg.py

================================================================================
🔑 핵심 패턴
================================================================================

1. Dependency Injection
   - 모든 Usecase는 생성자를 통해 Repository와 Service 주입
   - 예: TradingUsecase(hantoo_service, bot_info_repo, trade_repo, history_repo)

2. Late Commit Pattern
   - 모든 변경 후 한 번에 commit
   - 예: existing.symbol = bot_info.symbol → ... → session.commit()

3. Mapper Pattern
   - ORM Model ↔ Domain Entity 분리
   - 예: _to_entity(model), _to_model(entity)

4. Repository Pattern
   - 추상 인터페이스와 구현 분리
   - 예: BotInfoRepository(ABC) / SQLAlchemyBotInfoRepository

================================================================================
⚠️ 주의사항
================================================================================

[DB 파일 관리]
- 기존: trade_chan.db, history_chan.db, status_chan.db, bot_info_chan.db, order_chan.db (5개 분리)
- 신규: egg_chan.db (1개 통합, 5개 테이블: bot_info, trade, order, history, status)
- 위치: data/persistence/sqlalchemy/db/

[스케줄러 리팩토링 (2025-12-02)]
- ✅ schedule (1.2.2) → **APScheduler (3.10.4)** 변경 완료 ✅
- **scheduler_config.py 최적화**:
  - 전역 변수 6개 → 1개 (_scheduler만)
  - `_initialize_dependencies()` 반환값을 tuple로 변경
  - `_get_schedule_times()` → `config/util.py:get_schedule_times()`로 이동
  - `_register_jobs()` 함수로 for 루프 중복 제거 (3줄로 축소)
  - Job 팩토리 함수 (클로저) 도입
  - start_scheduler() 시 daily_job 한 번 실행 (초기화)
- **예외 처리 개선**:
  - 시트 동기화: 실패해도 무시 (Google API 불안정)
  - 거래/메시지 작업: raise로 job 자동 중단 (APScheduler)
  - 텔레그램으로 에러 즉시 알림
- **MessageJobs 최적화**:
  - `initialize_on_startup()` 제거 → daily_job으로 통일
  - `sync_bots()` 메서드 추가
  - daily_job: 메시지 → 시트 → 봇동기화 → CSV정리
- **BotManagementUsecase 의존성 수정**:
  - bot_info_repo + trade_repo 모두 전달 (T값 계산용)

[테스트 코드 작성 규칙]
- 테스트 코드는 항상 함수 형태로 나눠서 개별 실행할 수 있게 만든다
- 예시: test_message.py (메시지 전송), test_sheets.py (시트 동기화)
- 각 함수는 독립적으로 실행 가능해야 함

[기능 유지 필수]
- seed_module: 8개 조건 체크, RSI/VIX/공탐지수 분석, CSV 캐싱
- order_module: TWAP 분할 매매 (make_buy/sell_order_list, check_order_request)
- history: 거래 이력 추적, 사이클 종료 메시지
- status: 입출금 관리, 일일 수익
- 자동 시작: 조건 충족 시 다음 봇 자동 활성화
- telegram: egg 전용 메시지 포맷 (ValueRebalancing과 다름)

[보안]
- google_api_secret.json은 .gitignore에 포함 필수
- Hantoo 계좌 정보는 환경 변수로 분리 고려

================================================================================
📚 참고 파일
================================================================================

[ValueRebalancing - 참고용]
- /Users/chanhypark/workspace/private/python/ValueRebalancing/STRUCTURE.txt
- /Users/chanhypark/workspace/private/python/ValueRebalancing/domain/entities/*.py
- /Users/chanhypark/workspace/private/python/ValueRebalancing/data/persistence/sqlalchemy/repositories/*.py
- /Users/chanhypark/workspace/private/python/ValueRebalancing/usecase/*.py

[egg - 원본]
- /Users/chanhypark/workspace/private/python/egg/main.py
- /Users/chanhypark/workspace/private/python/egg/seed_module.py
- /Users/chanhypark/workspace/private/python/egg/trade_module.py
- /Users/chanhypark/workspace/private/python/egg/order_module.py (TWAP - 중요!)
- /Users/chanhypark/workspace/private/python/egg/db_usecase.py
- /Users/chanhypark/workspace/private/python/egg/repository/*.py
- /Users/chanhypark/workspace/private/python/egg/utils/telegram_module.py

================================================================================

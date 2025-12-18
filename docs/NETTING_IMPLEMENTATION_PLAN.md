# 장부거래(Netting) 기능 구현 계획서

> **작성일**: 2024-12
> **전략**: Greedy 1:1 매칭 (가장 많이 상쇄되는 쌍 반복 선택)
> **상태**: 구현 대기

---

## 1. 개요

### 1.1 목표
동일 symbol에 대해 매수/매도 주문서가 동시에 존재할 때, 겹치는 수량은 **실제 증권사 API 호출 없이 내부 장부거래로 처리**하여 불필요한 거래 비용 절감.

### 1.2 예시 시나리오
```
[주문서 생성 완료 후]
- bot1: TQQQ 30개 매수 (seed $3,000)
- bot2: TQQQ 50개 매도

[장부거래 처리]
- 30개는 내부 상쇄 (bot1에 +30개, bot2에 -30개)
- bot2의 남은 20개만 실제 증권사 API로 매도

[효과]
- API 호출 횟수: 60회 → 20회 (66% 감소)
- 거래 수수료 절감
```

### 1.3 선택된 전략: Greedy 1:1 매칭

| 항목 | 설명 |
|------|------|
| 매칭 방식 | 1:1 (한 번에 하나의 Buy-Sell 쌍) |
| 선택 기준 | **가장 많이 상쇄되는 쌍 우선** (Greedy) |
| 반복 처리 | 더 이상 상쇄 가능한 쌍이 없을 때까지 반복 |
| 다중 쌍 지원 | 같은 symbol에 매수 2개 + 매도 2개면 모두 상쇄 가능 |

---

## 2. 현재 시스템 구조 분석

### 2.1 관련 파일 구조
```
/Users/chanhypark/workspace/private/python/EggMoney/
├── domain/
│   ├── entities/
│   │   ├── order.py           # Order 엔티티 (symbol, remain_value, order_type 등)
│   │   ├── trade.py           # Trade 엔티티 (보유 종목 정보)
│   │   └── bot_info.py        # BotInfo 엔티티 (봇 설정)
│   ├── repositories/
│   │   └── order_repository.py    # OrderRepository 인터페이스
│   └── value_objects/
│       ├── trade_result.py    # TradeResult (거래 결과)
│       ├── trade_type.py      # TradeType (BUY, SELL, SELL_1_4 등)
│       └── order_type.py      # OrderType (주문 유형)
├── data/
│   └── persistence/sqlalchemy/repositories/
│       └── order_repository_impl.py   # OrderRepository 구현체
├── usecase/
│   ├── order_usecase.py       # 주문서 생성 Usecase
│   └── trading_usecase.py     # 거래 실행 Usecase
└── presentation/
    └── scheduler/
        └── trading_jobs.py    # 스케줄러 Job (make_order_job, twap_job)
```

### 2.2 현재 거래 흐름
```
scheduler_config.py
    │
    ├── make_order_job (예: 09:00)
    │   └── TradingJobs.make_order_job()
    │       ├── 거래일 체크
    │       ├── 동적시드 적용
    │       └── for 활성봇:
    │           └── OrderUsecase.create_order() → Order DB 저장
    │
    └── twap_job (예: 09:10, 09:20, ...)
        └── TradingJobs.twap_job()
            └── for 활성봇 (Order 있는 경우):
                └── TradingUsecase.execute_twap()
                    ├── HantooService.buy() or .sell()  ← 실제 API 호출
                    └── Trade/History DB 저장
```

### 2.3 핵심 엔티티 분석

#### Order 엔티티 (`domain/entities/order.py`)
```python
@dataclass
class Order:
    date_added: datetime
    name: str                    # 봇 이름 (PK)
    symbol: str                  # 종목 심볼 (예: "TQQQ")
    trade_result_list: List[Dict]
    order_type: OrderType        # BUY, SELL, SELL_1_4, SELL_3_4 등
    trade_count: int             # 남은 TWAP 분할 횟수
    total_count: int             # 전체 TWAP 분할 횟수
    remain_value: float          # 남은 금액(매수) 또는 수량(매도)
    total_value: float           # 전체 금액 또는 수량

    def is_buy_order(self) -> bool
    def is_sell_order(self) -> bool
```

**중요**:
- 매수 Order의 `remain_value`는 **금액($)**
- 매도 Order의 `remain_value`는 **수량(개)**

#### TradeResult 값 객체 (`domain/value_objects/trade_result.py`)
```python
@dataclass
class TradeResult:
    trade_type: TradeType    # BUY, SELL, SELL_PART 등
    amount: float            # 거래 수량
    unit_price: float        # 단가
    total_price: float       # 총 거래금액
```

#### TradeType 값 객체 (`domain/value_objects/trade_type.py`)
```python
class TradeType(Enum):
    SELL = 'Sell'           # 전체 매도
    SELL_1_4 = 'Sell_1_4'   # 1/4 매도
    SELL_3_4 = 'Sell_3_4'   # 3/4 매도
    SELL_PART = 'Sell_Part' # 부분 매도
    BUY = 'Buy'             # 일반 매수
    BUY_FORCE = 'Buy_Force' # 강제 매수
```

### 2.4 기존 DB 저장 메서드 분석

#### TradingUsecase._save_buy_to_db() (라인 390-421)
```python
def _save_buy_to_db(self, bot_info: BotInfo, trade_result: TradeResult) -> None:
    """매수 거래 결과를 DB에 저장"""
    # 1. 이전 Trade 조회
    prev_trade = self.trade_repo.find_by_name(bot_info.name)

    # 2. Trade 리밸런싱 (기존 + 신규 합산, 평단가 재계산)
    re_balancing_trade = self.trade_repo.rebalance_trade(
        name=bot_info.name,
        symbol=bot_info.symbol,
        prev_trade=prev_trade,
        trade_result=trade_result
    )

    # 3. Trade 저장
    self.trade_repo.save(re_balancing_trade)

    # 4. History 저장 (buy_price만, sell_price=0)
    self._save_buy_history(bot_info, trade_result)
```

#### TradingUsecase._save_sell_to_db() (라인 422-465)
```python
def _save_sell_to_db(self, bot_info: BotInfo, trade_result: TradeResult) -> None:
    """매도 거래 결과를 DB에 저장"""
    prev_trade = self.trade_repo.find_by_name(bot_info.name)

    if trade_result.trade_type.is_partial_sell():
        # 부분 매도: Trade 리밸런싱
        new_trade = self.trade_repo.rebalance_trade(...)
        if new_trade.amount > 0:
            self.trade_repo.save(new_trade)
        else:
            self.trade_repo.delete_by_name(bot_info.name)
    else:
        # 전체 매도: Trade 삭제
        self.trade_repo.delete_by_name(bot_info.name)

    # History 저장 + 손익 계산 + added_seed 업데이트
    self._save_sell_history(bot_info, trade_result, prev_trade, is_update_added_seed)
```

---

## 3. 구현 계획

### 3.1 변경할 거래 흐름
```
scheduler_config.py
    │
    ├── make_order_job (예: 09:00)
    │   └── TradingJobs.make_order_job()
    │       ├── 거래일 체크
    │       ├── 동적시드 적용
    │       ├── for 활성봇:
    │       │   └── OrderUsecase.create_order() → Order DB 저장
    │       │
    │       └── ★ self._execute_netting_if_needed()  ← 신규 추가
    │           ├── OrderUsecase.find_netting_orders() → NettingPair 리스트
    │           └── for pair in netting_pairs:
    │               ├── TradingUsecase.execute_netting(pair) → DB 저장
    │               └── OrderUsecase.update_order_after_netting() → Order 차감
    │
    └── twap_job (예: 09:10, 09:20, ...)
        └── TradingJobs.twap_job()
            └── for 활성봇 (Order 있는 경우):
                └── TradingUsecase.execute_twap()
                    └── 남은 수량만 실제 API 호출
```

### 3.2 신규 데이터 구조

#### NettingPair (신규 생성)
**파일**: `usecase/order_usecase.py` 또는 `domain/value_objects/netting_pair.py`

```python
from dataclasses import dataclass
from domain.entities.order import Order

@dataclass
class NettingPair:
    """장부거래 상쇄 쌍"""
    buy_order: Order       # 매수 주문서
    sell_order: Order      # 매도 주문서
    netting_amount: int    # 상쇄할 수량 (개)
    current_price: float   # 현재가 (장부거래 단가로 사용)
```

---

## 4. 상세 구현

### 4.1 OrderRepository 확장

#### 인터페이스 추가 (`domain/repositories/order_repository.py`)
```python
from abc import abstractmethod
from typing import List, Optional
from domain.entities.order import Order

class OrderRepository:
    # ... 기존 메서드 ...

    @abstractmethod
    def find_all_by_symbol(self, symbol: str) -> List[Order]:
        """
        같은 symbol의 모든 Order 조회

        Args:
            symbol: 종목 심볼 (예: "TQQQ")

        Returns:
            해당 symbol의 Order 리스트
        """
        pass
```

#### 구현체 추가 (`data/persistence/sqlalchemy/repositories/order_repository_impl.py`)
```python
def find_all_by_symbol(self, symbol: str) -> List[Order]:
    """같은 symbol의 모든 Order 조회"""
    models = self.session.query(OrderModel).filter(
        OrderModel.symbol == symbol.strip().upper()
    ).all()

    return [self._to_entity(model) for model in models]
```

---

### 4.2 OrderUsecase 확장

#### 파일: `usecase/order_usecase.py`

#### 4.2.1 NettingPair 정의 (파일 상단)
```python
from dataclasses import dataclass
from typing import List, Optional, Dict

@dataclass
class NettingPair:
    """장부거래 상쇄 쌍"""
    buy_order: 'Order'
    sell_order: 'Order'
    netting_amount: int      # 상쇄할 수량 (개)
    current_price: float     # 현재가
```

#### 4.2.2 find_netting_orders() 메서드
```python
def find_netting_orders(self) -> List[NettingPair]:
    """
    같은 symbol의 Buy/Sell Order 쌍 탐색 (Greedy 1:1 매칭)

    알고리즘:
    1. 모든 Order를 symbol별로 그룹핑
    2. 같은 symbol에 Buy와 Sell이 둘 다 있으면:
       - 반복: 상쇄 가능한 쌍이 없을 때까지
         - 모든 (Buy, Sell) 쌍 중 가장 많이 상쇄되는 쌍 선택
         - NettingPair 리스트에 추가
         - 해당 Order의 remain_value 임시 차감
    3. 현재가 조회하여 NettingPair에 포함

    Returns:
        List[NettingPair]: 상쇄할 (buy, sell, amount, price) 쌍 리스트
    """
    orders = self.order_repo.find_all()

    if not orders:
        return []

    # 1. symbol별 그룹핑
    symbol_groups: Dict[str, Dict[str, List[Order]]] = {}
    for order in orders:
        if order.symbol not in symbol_groups:
            symbol_groups[order.symbol] = {'buy': [], 'sell': []}

        if order.is_buy_order():
            symbol_groups[order.symbol]['buy'].append(order)
        elif order.is_sell_order():
            symbol_groups[order.symbol]['sell'].append(order)

    netting_pairs = []

    # 2. 각 symbol에 대해 상쇄 쌍 찾기
    for symbol, groups in symbol_groups.items():
        buy_orders = groups['buy']
        sell_orders = groups['sell']

        # Buy와 Sell 둘 다 있어야 상쇄 가능
        if not buy_orders or not sell_orders:
            continue

        # 현재가 조회 (symbol당 한 번만)
        current_price = self.hantoo_service.get_price(symbol)
        if not current_price:
            send_message_sync(f"⚠️ [{symbol}] 장부거래 현재가 조회 실패")
            continue

        # 임시 remain_value 추적 (실제 Order 수정 없이 계산용)
        # 매수: 금액 → 수량으로 변환
        buy_remains = {
            o.name: self._get_buy_amount_from_seed(o.remain_value, current_price)
            for o in buy_orders
        }
        # 매도: 수량 그대로
        sell_remains = {o.name: int(o.remain_value) for o in sell_orders}

        # 3. Greedy 반복: 가장 많이 상쇄되는 쌍 선택
        while True:
            best_pair = None
            best_amount = 0

            for buy in buy_orders:
                for sell in sell_orders:
                    buy_amt = buy_remains.get(buy.name, 0)
                    sell_amt = sell_remains.get(sell.name, 0)

                    if buy_amt <= 0 or sell_amt <= 0:
                        continue

                    netting_amt = min(buy_amt, sell_amt)
                    if netting_amt > best_amount:
                        best_amount = netting_amt
                        best_pair = (buy, sell)

            # 더 이상 상쇄 가능한 쌍 없음
            if best_pair is None or best_amount <= 0:
                break

            buy, sell = best_pair

            # NettingPair 생성
            netting_pairs.append(NettingPair(
                buy_order=buy,
                sell_order=sell,
                netting_amount=best_amount,
                current_price=current_price
            ))

            # 임시 remain 차감 (다음 반복에서 고려)
            buy_remains[buy.name] -= best_amount
            sell_remains[sell.name] -= best_amount

    return netting_pairs

def _get_buy_amount_from_seed(self, seed: float, current_price: float) -> int:
    """매수 금액(seed)을 수량으로 변환"""
    if current_price <= 0:
        return 0
    return int(seed / current_price)
```

#### 4.2.3 update_order_after_netting() 메서드
```python
def update_order_after_netting(
    self,
    order: Order,
    netted_amount: int,
    current_price: float
) -> None:
    """
    장부거래 후 Order 업데이트

    Args:
        order: 업데이트할 주문서
        netted_amount: 상쇄된 수량 (개)
        current_price: 상쇄 시 사용된 현재가

    Note:
        - 매수 Order: remain_value는 금액($) → 금액 차감
        - 매도 Order: remain_value는 수량(개) → 수량 차감
    """
    if order.is_buy_order():
        # 매수: 금액 차감 (수량 × 단가)
        deducted_value = netted_amount * current_price
        order.remain_value -= deducted_value

        send_message_sync(
            f"📝 [{order.name}] 매수 주문서 장부거래 반영\n"
            f"  - 상쇄 수량: {netted_amount}개\n"
            f"  - 차감 금액: ${deducted_value:,.2f}\n"
            f"  - 남은 금액: ${order.remain_value:,.2f}"
        )
    else:
        # 매도: 수량 차감
        order.remain_value -= netted_amount

        send_message_sync(
            f"📝 [{order.name}] 매도 주문서 장부거래 반영\n"
            f"  - 상쇄 수량: {netted_amount}개\n"
            f"  - 남은 수량: {int(order.remain_value)}개"
        )

    # Order 저장 또는 삭제
    if order.remain_value <= 0:
        self.order_repo.delete_by_name(order.name)
        send_message_sync(f"🗑️ [{order.name}] 주문서 전량 상쇄 → 삭제 완료")
    else:
        self.order_repo.save(order)
```

---

### 4.3 TradingUsecase 확장

#### 파일: `usecase/trading_usecase.py`

#### execute_netting() 메서드
```python
def execute_netting(self, netting_pair: 'NettingPair') -> None:
    """
    장부거래 실행 (API 호출 없이 내부 정산)

    Args:
        netting_pair: 상쇄할 Buy/Sell Order 쌍 + 수량 + 현재가

    처리 내용:
    1. 매수측 TradeResult 생성 → _save_buy_to_db() 호출
    2. 매도측 TradeResult 생성 → _save_sell_to_db() 호출
    3. 텔레그램 메시지 발송

    Note:
        Order 업데이트는 OrderUsecase.update_order_after_netting()에서 처리
    """
    buy_order = netting_pair.buy_order
    sell_order = netting_pair.sell_order
    amount = netting_pair.netting_amount
    price = netting_pair.current_price

    # 봇 정보 조회
    buy_bot_info = self.bot_info_repo.find_by_name(buy_order.name)
    sell_bot_info = self.bot_info_repo.find_by_name(sell_order.name)

    if not buy_bot_info or not sell_bot_info:
        send_message_sync(
            f"⚠️ 장부거래 실패: 봇 정보 조회 실패\n"
            f"  - 매수봇: {buy_order.name}\n"
            f"  - 매도봇: {sell_order.name}"
        )
        return

    # 장부거래 시작 메시지
    send_message_sync(
        f"🔄 [{buy_order.symbol}] 장부거래 시작\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📈 매수: {buy_order.name} +{amount}개\n"
        f"📉 매도: {sell_order.name} -{amount}개\n"
        f"💰 단가: ${price:,.2f}\n"
        f"💵 총액: ${amount * price:,.2f}\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )

    # 1. 매수측 TradeResult 생성 및 DB 저장
    buy_trade_result = TradeResult(
        trade_type=TradeType(buy_order.order_type.value),  # BUY or BUY_FORCE
        amount=amount,
        unit_price=price,
        total_price=round(amount * price, 2)
    )
    self._save_buy_to_db(buy_bot_info, buy_trade_result)

    # 2. 매도측 TradeResult 생성 및 DB 저장
    sell_trade_result = TradeResult(
        trade_type=TradeType(sell_order.order_type.value),  # SELL, SELL_1_4 등
        amount=amount,
        unit_price=price,
        total_price=round(amount * price, 2)
    )
    self._save_sell_to_db(sell_bot_info, sell_trade_result)

    send_message_sync(
        f"✅ [{buy_order.symbol}] 장부거래 완료\n"
        f"  - {buy_order.name}: Trade/History 저장 완료\n"
        f"  - {sell_order.name}: Trade/History 저장 완료"
    )
```

---

### 4.4 TradingJobs 수정

#### 파일: `presentation/scheduler/trading_jobs.py`

#### make_order_job() 수정
```python
def make_order_job(self) -> None:
    """
    메인 거래 작업

    수정사항: 주문서 생성 완료 후 장부거래 상쇄 로직 추가
    """
    if not is_trade_date():
        send_message_sync("설정한 거래요일이 아니라 종료 합니다")
        return

    self.bot_management_usecase.check_bot_sync()
    self.bot_management_usecase.apply_dynamic_seed()

    # 미처리 주문서 체크
    remaining_orders = self.order_repo.find_all()
    if remaining_orders:
        send_message_sync(
            f"⚠️ 메인 거래 시작 전 미처리 주문서 발견!\n"
            f"주문서 개수: {len(remaining_orders)}\n"
            f"주문서 목록: {[o.name for o in remaining_orders]}"
        )
    self.order_repo.delete_old_orders(before_date=date.today())

    # 모든 활성 봇에 대해 주문서 생성
    bot_infos = self.bot_info_repo.find_all()
    for bot_info in bot_infos:
        if bot_info.active:
            self._execute_trade_for_bot(bot_info)
            if not item.is_test:
                time.sleep(5)

    # ★ 신규 추가: 장부거래 상쇄 처리
    self._execute_netting_if_needed()
```

#### _execute_netting_if_needed() 추가
```python
def _execute_netting_if_needed(self) -> None:
    """
    주문서 상쇄 처리 (장부거래)

    make_order_job() 완료 후 호출되어:
    1. 같은 symbol의 매수/매도 Order 쌍 탐색
    2. 가능한 모든 쌍에 대해 장부거래 실행
    3. Order 업데이트 (remain_value 차감 또는 삭제)
    """
    send_message_sync("🔍 장부거래 가능한 주문서 탐색 중...")

    # 1. 상쇄 가능한 쌍 탐색
    netting_pairs = self.order_usecase.find_netting_orders()

    if not netting_pairs:
        send_message_sync("ℹ️ 장부거래 대상 없음 (같은 symbol 매수/매도 쌍 없음)")
        return

    send_message_sync(
        f"📋 장부거래 대상 발견: {len(netting_pairs)}쌍\n"
        f"상세: {[(p.buy_order.name, p.sell_order.name, p.netting_amount) for p in netting_pairs]}"
    )

    # 2. 각 쌍에 대해 장부거래 실행
    for pair in netting_pairs:
        try:
            # DB 저장 (Trade, History)
            self.trading_usecase.execute_netting(pair)

            # Order 업데이트 (OrderUsecase)
            self.order_usecase.update_order_after_netting(
                pair.buy_order,
                pair.netting_amount,
                pair.current_price
            )
            self.order_usecase.update_order_after_netting(
                pair.sell_order,
                pair.netting_amount,
                pair.current_price
            )

        except Exception as e:
            send_message_sync(
                f"❌ 장부거래 실패\n"
                f"  - 매수: {pair.buy_order.name}\n"
                f"  - 매도: {pair.sell_order.name}\n"
                f"  - 오류: {str(e)}"
            )
            # 실패해도 다음 쌍 계속 처리
            continue

    send_message_sync("✅ 장부거래 처리 완료")
```

---

## 5. 테스트 시나리오

### 5.1 기본 시나리오: 단순 1:1 상쇄
```
입력:
  - bot1: TQQQ 매수 주문서 (seed $3,000, 현재가 $100 → 30개)
  - bot2: TQQQ 매도 주문서 (50개)

기대 결과:
  - NettingPair: (bot1, bot2, 30개, $100)
  - bot1: Trade에 +30개 추가, 주문서 삭제 (전량 상쇄)
  - bot2: Trade에서 -30개, 주문서 remain_value = 20개 (남은 거래)
```

### 5.2 복잡 시나리오: 다중 쌍 상쇄
```
입력:
  - A: TQQQ 매수 30개
  - B: TQQQ 매수 20개
  - C: TQQQ 매도 50개
  - D: TQQQ 매도 10개

처리 과정 (Greedy):
  1차: (A:30, C:50) → 30개 상쇄
       - A: 전량 상쇄 → 삭제
       - C: remain = 20개
  2차: (B:20, C:20) → 20개 상쇄
       - B: 전량 상쇄 → 삭제
       - C: remain = 0개 → 삭제
  3차: D(10개) 매칭 대상 없음 → 실제 거래

기대 결과:
  - NettingPairs: [(A,C,30), (B,C,20)]
  - D만 남음 → TWAP으로 10개 매도
```

### 5.3 엣지 케이스: 같은 봇이 매수/매도
```
입력:
  - bot1: TQQQ 매수 30개
  - bot1: SOXL 매도 20개  (다른 symbol)

기대 결과:
  - 상쇄 없음 (symbol이 다름)
  - 둘 다 실제 거래
```

---

## 6. 주의사항

### 6.1 remain_value 처리
- **매수 Order**: remain_value = 금액($) → `차감 = 수량 × 현재가`
- **매도 Order**: remain_value = 수량(개) → `차감 = 수량`

### 6.2 Order 삭제 조건
- remain_value ≤ 0 이면 `order_repo.delete_by_name()` 호출
- 남은 값이 있으면 `order_repo.save()` 호출

### 6.3 trade_count 유지
- 부분 상쇄 후에도 `trade_count`는 변경하지 않음
- TWAP에서 남은 `remain_value`를 `trade_count`로 나눠 분할 거래

### 6.4 현재가 기준
- 장부거래 단가는 `hantoo_service.get_price(symbol)` 사용
- 매수측, 매도측 모두 동일한 현재가 적용

### 6.5 TradeType 보존
- 매수측: `order.order_type` (BUY or BUY_FORCE) 그대로 사용
- 매도측: `order.order_type` (SELL, SELL_1_4, SELL_3_4 등) 그대로 사용

---

## 7. 수정 파일 요약

| 파일 | 변경 내용 |
|------|----------|
| `domain/repositories/order_repository.py` | `find_all_by_symbol()` 인터페이스 추가 |
| `data/.../order_repository_impl.py` | `find_all_by_symbol()` 구현 |
| `usecase/order_usecase.py` | `NettingPair`, `find_netting_orders()`, `update_order_after_netting()` 추가 |
| `usecase/trading_usecase.py` | `execute_netting()` 추가 |
| `presentation/scheduler/trading_jobs.py` | `_execute_netting_if_needed()` 추가, `make_order_job()` 수정 |

---

## 8. 구현 순서

1. **OrderRepository 확장** - `find_all_by_symbol()` 추가
2. **OrderUsecase 확장** - `NettingPair`, `find_netting_orders()`, `update_order_after_netting()` 추가
3. **TradingUsecase 확장** - `execute_netting()` 추가
4. **TradingJobs 수정** - `_execute_netting_if_needed()` 추가, `make_order_job()` 연결
5. **테스트** - 단위 테스트 및 통합 테스트

---

## 9. 롤백 계획

문제 발생 시:
1. `make_order_job()`에서 `_execute_netting_if_needed()` 호출 주석 처리
2. 기존 TWAP 로직으로 즉시 복구 가능

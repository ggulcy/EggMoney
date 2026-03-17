# Reverse Mode 구현 명세

## 개요
T가 max_tier-1을 초과하면 평단가 기준 전략 대신 5일 평균가(ma5) 기준으로 전환.
적극적 분할 매도 + 여유자금 재매수 반복으로 평단가를 낮추는 전략.

---

## 변경 파일

- `usecase/order_usecase.py` (핵심)
- `presentation/scheduler/scheduler_config.py` (DI 주입)

---

## 구현 내용

### 1. `OrderUsecase.__init__` - market_indicator_repo 추가

```python
def __init__(
    self,
    bot_info_repo: BotInfoRepository,
    trade_repo: TradeRepository,
    history_repo: HistoryRepository,
    order_repo: OrderRepository,
    exchange_repo: ExchangeRepository,
    message_repo: MessageRepository,
    market_indicator_repo: MarketIndicatorRepository,  # 추가
):
```

---

### 2. `scheduler_config.py` - DI 주입

```python
order_usecase = OrderUsecase(
    bot_info_repo=deps.bot_info_repo,
    trade_repo=deps.trade_repo,
    history_repo=deps.history_repo,
    order_repo=deps.order_repo,
    exchange_repo=deps.exchange_repo,
    message_repo=deps.message_repo,
    market_indicator_repo=deps.market_indicator_repo,  # 추가
)
```

---

### 3. `create_order` - reverse mode 분기

```python
def create_order(self, bot_info: BotInfo):
    self._is_reverse_mode_switch(bot_info)  # 매 호출마다 mode 판단

    if bot_info.reverse_mode:
        return self._create_reverse_mode_order(bot_info)

    # 기존 일반 모드 로직
    if not bot_info.skip_sell:
        result = self._create_sell_order(bot_info)
        if result:
            return result
    ...
```

---

### 4. `_is_reverse_mode_switch` - 모드 전환 판단

```
total_amount == 0           → reverse_mode = False + save()  (전량 매도 후 일반 복귀)
T > max_tier-1              → reverse_mode = True  + save()  (리버스 모드 진입)
T <= max_tier-1
AND cur_price > avr*(1-profit_rate) → reverse_mode = False + save()  (탈출 조건)
```

---

### 5. `_create_reverse_mode_order` - 주문 생성

```
1. ma5 조회 (market_indicator_repo.get_average_close, days=5)
2. 현재가 조회 (exchange_repo.get_price)
3. total_amount, T 계산

[T > max_tier-1 구간]
    → ma5 무시, 강제 10% 매도
    → sell_amount = int(total_amount * 0.1) or int(total_amount)
    → TradeType.SELL_PART

[T <= max_tier-1 구간]
    cur_price > ma5 → SELL_PART  (보유량의 10%)
        sell_amount < 1인 경우   → SELL (잔여 전량 매도)

    cur_price < ma5 → BUY
        available_cash = seed × (max_tier - T)
        buy_seed = available_cash × 0.25

    cur_price == ma5 → None (HOLD)
```

---

### 6. `check_closing_drop` - 리버스 모드 중 장마감 급락 매수 차단

```python
if bot_info.reverse_mode:
    return None  # 리버스 모드 중 비활성화
```

---

### 7. `_create_sell_order` - reverse mode 관련 코드 제거

기존에 `_create_sell_order` 내부에 있던 reverse_mode 분기 및 `_create_sell_reverse_mode_order` 호출 제거.
mode 전환은 `_is_reverse_mode_switch`에서만 담당.

---

## 전체 흐름

```
create_order()
    └── _is_reverse_mode_switch()
            total_amount == 0           → reverse_mode = False
            T > max_tier-1              → reverse_mode = True
            T <= max_tier-1 AND 회복    → reverse_mode = False

    [reverse_mode = True]
    └── _create_reverse_mode_order()
            T > max_tier-1  → SELL_PART (강제 10%)
            cur > ma5       → SELL_PART (10%) or SELL (잔여 전량)
            cur < ma5       → BUY (여유금의 1/4)
            cur == ma5      → None (HOLD)

    [reverse_mode = False]
    └── 기존 로직
            _create_sell_order() → _create_buy_order()
```

---

## 핵심 계산식

```python
# T
t = util.get_T(total_investment, bot_info.seed)

# 매도 수량 (보유량의 10%)
sell_amount = int(total_amount * 0.1) or int(total_amount)

# 여유금 / 매수 금액
available_cash = bot_info.seed * (bot_info.max_tier - t)
buy_seed = available_cash * 0.25
```

---

## TradeType → DB 처리

| TradeType   | _save_sell_to_db         | 결과               |
|-------------|--------------------------|------------------  |
| SELL_PART   | is_partial_sell() = True | Trade 리밸런싱     |
| SELL        | is_partial_sell() = False| Trade 삭제 + 사이클 종료 |
| BUY         | _save_buy_to_db()        | Trade 리밸런싱     |

---

## 검증 시나리오

| 시나리오 | 기대 결과 |
|---------|----------|
| T > max_tier-1 진입 | reverse_mode = True 전환 |
| total_amount == 0 | reverse_mode = False, 일반모드 복귀 |
| reverse_mode + T > max_tier-1 | ma5 무시, 강제 10% SELL_PART |
| reverse_mode + cur_price > ma5 | SELL_PART (10%) |
| reverse_mode + total_amount <= 9 | SELL (잔여 전량) |
| reverse_mode + cur_price < ma5 | BUY (여유금 × 0.25) |
| T <= max_tier-1 + cur_price > avr×(1-profit_rate) | reverse_mode = False 탈출 |
| reverse_mode + 장마감 급락 | 차단 (None 반환) |

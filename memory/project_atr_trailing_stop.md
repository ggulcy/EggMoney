---
name: ATR Trailing Stop 구현 계획
description: 긴 하락장 후 상승장 전환 시 폭발적 상승분을 최대한 수익화하기 위한 ATR 트레일링 스탑 기능 설계 및 구현 계획
type: project
---

## 기능 의도

기존 고정 익절가(profit_price) 도달 시 즉시 3/4 매도하는 로직을, T가 충분히 쌓인 상태에서는 ATR 트레일링 스탑으로 추세가 꺾일 때까지 홀딩하는 로직으로 대체.

**Why:** 긴 하락장에서 DCA로 물탄 후 반등 시, 고정 익절가에서 팔면 이후 폭발적 상승분을 못 먹음.

## 확정된 설계

### 진입 조건
- `trailing_enabled = True`
- `T >= trailing_t_threshold`
- `cur_price > profit_price` (기존 profit_rate 그대로 트리거로 사용)

### 모드 중 동작
- 1/4 매도 비활성화
- 매수 정상 작동 (강한 상승 중엔 buy 조건이 자연 억제됨)
- high_watermark, trailing_stop 매일 재계산

### 탈출 조건 (둘 다 전량 매도 후 mode OFF, Normal Mode 복귀 없음)
```
ATR_stop    = trailing_high_watermark - (ATR × trailing_atr_multiplier)
avr_floor   = avr_price × (1 - trailing_floor_rate)  ← 매일 재계산
trailing_stop = max(ATR_stop, avr_floor)

cur_price < trailing_stop → 전량 매도, trailing_mode = False
```

### trailing_enabled = False 시
기존 로직 그대로: condition_3_4 → 3/4 매도

## BotInfo 추가 필드

```python
# 설정 파라미터
trailing_enabled: bool = False              # UI에서 on/off
trailing_t_threshold: float = 2.5          # T 진입 기준
trailing_atr_multiplier: float = 2.0       # ATR × N
trailing_floor_rate: float = 0.10          # 평단 하단 기준 (0.10 = -10%)

# 상태 필드 (DB 저장, 매일 갱신)
trailing_mode: bool = False
trailing_high_watermark: float = 0.0
trailing_stop: float = 0.0                 # 전날 계산된 스탑가 (다음날 비교용)
```

## trade_job 내 trailing 일일 흐름

```
진입일 (Day 0) - 이전 trailing_stop 없음:
  profit_price 도달 AND T >= trailing_t_threshold
  → trailing_mode = True
  → 1/4 매도 (진입 시 일부 수익 확정)
  → high_watermark = cur_price
  → trailing_stop = max(cur_price - N×ATR, avr_price×(1-floor_rate))
  → DB 저장

Day 1+:
  1. DB에서 trailing_stop 로드 (전날 저장값)
  2. cur_price < trailing_stop? → 전량 매도, mode OFF
  3. 매도 안 했으면:
       high_watermark = max(high_watermark, cur_price)
       new_stop = max(high_watermark - N×ATR, avr_price×(1-floor_rate))
       trailing_stop = max(trailing_stop, new_stop)  ← 스탑은 절대 후퇴 안 함
       DB 저장 (내일 비교용)

※ trailing mode 중 1/4 매도: 진입일(Day 0)에만 1회, 이후 비활성화
※ trailing mode 중 매수: 정상 작동 (강한 상승 중엔 buy 조건 자연 억제)
```

## 구현 투두리스트

| # | 작업 | 파일 | 상태 |
|---|------|------|------|
| 1 | ATR 인터페이스 추가 | `domain/repositories/market_indicator_repository.py` | ✅ 완료 |
| 2 | ATR 서비스 구현 | `data/external/market_data/market_data_service.py` | ✅ 완료 |
| 3 | ATR 레포지토리 구현 | `data/external/market_data/market_indicator_repository_impl.py` | ✅ 완료 |
| 4 | BotInfo 필드 추가 | `domain/entities/bot_info.py` | ⬜ 대기 |
| 5 | DB 모델 컬럼 추가 | `data/persistence/sqlalchemy/models/bot_info_model.py` | ⬜ 대기 |
| 6 | Repository 매퍼 업데이트 | `data/persistence/sqlalchemy/repositories/bot_info_repository_impl.py` | ⬜ 대기 |
| 7 | OrderUsecase trailing 로직 | `usecase/order_usecase.py` | ⬜ 대기 |
| 8 | UI 컨트롤 추가 | `presentation/web/templates/bot_info.html` | ⬜ 대기 |
| 9 | Routes 업데이트 | `presentation/web/routes/bot_info_routes.py` | ⬜ 대기 |

## ATR 계산 (구현 완료)

- `ta.volatility.AverageTrueRange` 사용, cache_hours=0 (항상 최신)
- trailing_stop은 DB에 저장 후 다음날 비교에 사용 (재계산 금지)
- trailing_stop은 한번 올라가면 절대 내려가지 않음 (max 보장)
- 확인 스크립트: `check_atr.py` (현재가, ATR$, ATR% 출력)

"""봇 팩토리 - 시장 상황에 따른 봇 설정 자동 생성"""
from typing import Dict, List, Any


# ============================================
# 티커별 리스크 가중치 설정
# ============================================
# 리스크 가중치: MaxTier 조정에 사용 (높을수록 MaxTier 증가 = 더 보수적)
TICKER_RISK_WEIGHTS = {
    "TQQQ": 1.0,  # 기본
    "SOXL": 1.5,  # 2배 리스크 (MaxTier 증가)
    "BITU": 2.0,  # 2배 리스크
    # 나머지 티커는 기본값 3.0 사용
}

DEFAULT_RISK_WEIGHT = 3.0


def get_ticker_risk_weight(ticker: str) -> float:
    """티커의 리스크 가중치 조회 (없으면 기본값 반환)"""
    return TICKER_RISK_WEIGHTS.get(ticker, DEFAULT_RISK_WEIGHT)


# ============================================
# 봇 레벨 정의 (1~3)
# ============================================
BOT_LEVEL_CONFIG = {
    1: {  # 수비적
        "name": "수비적",
        "max_tier": 40,
        "profit_rate": 0.10,  # 10%
        "point_loc": "P2_3",  # P1/2
    },
    2: {  # 중립
        "name": "중립",
        "max_tier": 30,
        "profit_rate": 0.12,  # 12%
        "point_loc": "P2_3",  # P2/3
    },
    3: {  # 공격적
        "name": "공격적",
        "max_tier": 20,
        "profit_rate": 0.15,  # 15%
        "point_loc": "P2_3",  # P2_#
    },
}

# ============================================
# 시장 단계별 봇 레벨 분배 비율
# ============================================
MARKET_LEVEL_DISTRIBUTION = {
    # [레벨1, 레벨2, 레벨3]
    0: [0.70, 0.30, 0.00],  # 수비: 레벨1 집중
    1: [0.30, 0.50, 0.20],  # 중립: 레벨1,2 균형
    2: [0.20, 0.40, 0.40],  # 공격: 레벨2,3 중심
    3: [0.10, 0.30, 0.60],  # 매우공격: 레벨3 집중
}

# ============================================
# 시장 단계별 현금 비율
# ============================================
CASH_RATIO = {
    0: 0.40,  # 수비: 25%
    1: 0.30,  # 중립: 15%
    2: 0.20,  # 공격: 10%
    3: 0.00,  # 매우공격: 5%
}


def distribute_bot_levels(market_stage: int, total_bots: int) -> Dict[int, int]:
    """시장 상황에 따라 봇 레벨별 개수 분배"""
    distribution = MARKET_LEVEL_DISTRIBUTION[market_stage]

    level_counts = {}
    assigned = 0

    # 레벨 1~3 순서대로 계산 (반올림)
    for level in range(1, 4):
        ratio = distribution[level - 1]

        # 마지막 레벨은 남은 개수 모두
        if level == 3:
            count = total_bots - assigned
        else:
            # 반올림 사용
            count = round(total_bots * ratio)
            # 남은 개수를 초과하지 않도록
            count = min(count, total_bots - assigned)

        if count > 0:
            level_counts[level] = count
            assigned += count

    return level_counts


def allocate_ticker_bot_count(tickers: List[Dict[str, Any]], max_count: int) -> List[Dict[str, Any]]:
    """우선 가중치에 따라 티커별 봇 개수 분배"""
    total_weight = sum(t["priority_weight"] for t in tickers)

    allocations = []
    remaining = max_count

    # 가중치 큰 순으로 정렬
    sorted_tickers = sorted(tickers, key=lambda t: t["priority_weight"], reverse=True)

    for i, ticker_info in enumerate(sorted_tickers):
        if i == len(sorted_tickers) - 1:
            # 마지막 티커는 남은 개수 모두
            count = remaining
        else:
            # 비율로 계산 (반올림)
            ratio = ticker_info["priority_weight"] / total_weight
            count = round(max_count * ratio)

            # 최소 1개 보장하되, 남은 개수 고려
            if count == 0 and remaining > 0:
                count = 1

            # 남은 개수를 초과하지 않도록
            count = min(count, remaining)

        if count > 0:
            allocations.append({
                "ticker": ticker_info["ticker"],
                "priority_weight": ticker_info["priority_weight"],
                "risk_weight": ticker_info["risk_weight"],
                "bot_count": count
            })
            remaining -= count

        if remaining <= 0:
            break

    return allocations


def assign_levels_to_tickers(ticker_allocations: List[Dict[str, Any]],
                             level_counts: Dict[int, int]) -> Dict[str, List[int]]:
    """티커별 봇들에게 레벨 배정

    전략:
    - 높은 레벨(공격적)부터 우선가중치 높은 티커에 배정
    - 각 티커 내에서도 다양한 레벨 분산
    """

    # 레벨을 높은 순으로 정렬 (4 -> 1)
    sorted_levels = sorted(level_counts.keys(), reverse=True)

    # 티커별 봇 레벨 리스트
    ticker_bot_levels = {t["ticker"]: [] for t in ticker_allocations}

    # 전체 레벨에 걸쳐 순환 배정을 위한 ticker_idx
    ticker_idx = 0

    # 각 레벨의 봇들을 티커에 분배
    for level in sorted_levels:
        count = level_counts[level]

        # 이 레벨의 봇들을 티커에 순환 배정
        for _ in range(count):
            ticker = ticker_allocations[ticker_idx]["ticker"]
            ticker_bot_levels[ticker].append(level)

            # 다음 티커로 (순환)
            ticker_idx = (ticker_idx + 1) % len(ticker_allocations)

    # 각 티커 내에서 레벨 정렬 (높은 레벨 먼저)
    for ticker in ticker_bot_levels:
        ticker_bot_levels[ticker].sort(reverse=True)

    return ticker_bot_levels


def calculate_max_tier(base_tier: int, risk_weight: float) -> int:
    """리스크 가중치에 따른 MaxTier 미세 조정"""
    # 리스크가 높을수록 약간 증가 (최대 +20%)
    adjustment = 1.0 + (risk_weight - 1.0) * 0.2
    tier = int(base_tier * adjustment)
    # 20~40 범위로 제한
    return max(20, min(40, tier))


def calculate_profit_rate(base_rate: float, risk_weight: float) -> float:
    """리스크 가중치에 따른 수익률 미세 조정

    Args:
        base_rate: 기본 수익률 (0.10~0.15)
        risk_weight: 리스크 가중치 (1.0~3.0)

    Returns:
        조정된 수익률 (10~20% 범위)
    """
    # 리스크가 높을수록 수익률 증가 (최대 +33%)
    # risk_weight 1.0 -> 조정 없음
    # risk_weight 3.0 -> +33% 증가
    adjustment = 1.0 + (risk_weight - 1.0) * 0.165
    rate = base_rate * adjustment
    # 10~20% 범위로 제한
    return max(0.10, min(0.20, rate))


def create_bot_config(ticker: str, risk_weight: float, level: int,
                     budget: float, bot_index: int, t_div: int) -> Dict[str, Any]:
    """단일 봇 설정 생성

    핵심 로직:
    - 예산이 먼저 배정됨 (균등 분배)
    - seed = 예산 / MaxTier
    - 레벨에 따라 MaxTier가 다르므로 seed 크기도 자동으로 달라짐
    """

    level_config = BOT_LEVEL_CONFIG[level]

    # MaxTier 계산 (리스크 보정)
    max_tier = calculate_max_tier(level_config["max_tier"], risk_weight)

    # Profit Rate 계산 (리스크 보정)
    profit_rate = calculate_profit_rate(level_config["profit_rate"], risk_weight)

    # Seed 계산
    # budget = seed × MaxTier
    seed = budget / max_tier

    return {
        "name": f"{ticker}_L{level}_{bot_index}",
        "symbol": ticker,
        "level": level,
        "level_name": level_config["name"],
        "budget": budget,
        "seed": round(seed, 2),
        "max_tier": max_tier,
        "profit_rate": round(profit_rate, 4),
        "t_div": t_div,
        "point_loc": level_config["point_loc"],
        "risk_weight": risk_weight,
    }


def create_bot_configs_for_renewal(market_stage: int, total_budget: float,
                                  ticker_bot_counts: Dict[str, int],
                                  t_div: int) -> Dict[str, Any]:
    """리뉴얼용 봇 설정 생성 함수 (티커별 봇 개수 고정)

    Args:
        market_stage: 시장 단계 (0=수비, 1=중립, 2=공격, 3=매우공격)
        total_budget: 총 예산
        ticker_bot_counts: 티커별 봇 개수 {"TQQQ": 2, "SOXL": 2}
        t_div: T_DIV 값

    Returns:
        create_bot_configs()와 동일한 구조
    """
    max_bot_count = sum(ticker_bot_counts.values())

    # 1. 현금 비율 계산
    cash_reserve = total_budget * CASH_RATIO[market_stage]
    investable = total_budget - cash_reserve

    # 2. 봇 레벨별 개수 분배
    level_counts = distribute_bot_levels(market_stage, max_bot_count)

    # 3. 티커별 봇 개수는 이미 정해져 있음 (allocate_ticker_bot_count 스킵)
    ticker_allocations = []
    for ticker, bot_count in ticker_bot_counts.items():
        ticker_allocations.append({
            "ticker": ticker,
            "bot_count": bot_count,
            "risk_weight": get_ticker_risk_weight(ticker)
        })

    # 4. 티커별 봇들에게 레벨 배정
    ticker_bot_levels = assign_levels_to_tickers(ticker_allocations, level_counts)

    # 5. 예산 균등 분배
    per_bot_budget = investable / max_bot_count

    bot_budgets = []
    for allocation in ticker_allocations:
        ticker = allocation["ticker"]
        risk_weight = allocation["risk_weight"]
        levels = ticker_bot_levels[ticker]

        for level in levels:
            bot_budgets.append({
                "ticker": ticker,
                "risk_weight": risk_weight,
                "level": level,
                "budget": per_bot_budget
            })

    # 6. 봇 설정 생성
    bots = []
    bot_index = 1

    for bot_budget in bot_budgets:
        bot = create_bot_config(
            ticker=bot_budget["ticker"],
            risk_weight=bot_budget["risk_weight"],
            level=bot_budget["level"],
            budget=bot_budget["budget"],
            bot_index=bot_index,
            t_div=t_div
        )

        bots.append(bot)
        bot_index += 1

    return {
        "market_stage": market_stage,
        "total_budget": total_budget,
        "cash_reserve": cash_reserve,
        "investable": investable,
        "per_bot_budget": per_bot_budget,
        "level_counts": level_counts,
        "ticker_allocations": ticker_allocations,
        "ticker_bot_levels": ticker_bot_levels,
        "bots": bots
    }


def create_bot_configs(market_stage: int, total_budget: float,
                      max_bot_count: int, tickers: List[Dict[str, Any]],
                      t_div: int) -> Dict[str, Any]:
    """봇 설정 생성 메인 함수

    Args:
        market_stage: 시장 단계 (0=수비, 1=중립, 2=공격, 3=매우공격)
        total_budget: 총 예산
        max_bot_count: 봇 최대 개수
        tickers: 티커 리스트 [{"ticker": str, "priority_weight": int, "risk_weight": float}]
        t_div: T_DIV 값 (현재 봇에서 가져옴)

    Returns:
        {
            "market_stage": int,
            "total_budget": float,
            "cash_reserve": float,
            "investable": float,
            "per_bot_budget": float,
            "level_counts": Dict[int, int],
            "ticker_allocations": List[Dict],
            "ticker_bot_levels": Dict[str, List[int]],
            "bots": List[Dict]
        }
    """

    # 1. 현금 비율 계산
    cash_reserve = total_budget * CASH_RATIO[market_stage]
    investable = total_budget - cash_reserve

    # 2. 봇 레벨별 개수 분배
    level_counts = distribute_bot_levels(market_stage, max_bot_count)

    # 3. 티커별 봇 개수 분배
    ticker_allocations = allocate_ticker_bot_count(tickers, max_bot_count)

    # 4. 티커별 봇들에게 레벨 배정
    ticker_bot_levels = assign_levels_to_tickers(ticker_allocations, level_counts)

    # 5. 예산 균등 분배
    per_bot_budget = investable / max_bot_count

    bot_budgets = []
    for allocation in ticker_allocations:
        ticker = allocation["ticker"]
        risk_weight = allocation["risk_weight"]
        levels = ticker_bot_levels[ticker]

        for level in levels:
            bot_budgets.append({
                "ticker": ticker,
                "risk_weight": risk_weight,
                "level": level,
                "budget": per_bot_budget
            })

    # 6. 봇 설정 생성
    bots = []
    bot_index = 1

    for bot_budget in bot_budgets:
        bot = create_bot_config(
            ticker=bot_budget["ticker"],
            risk_weight=bot_budget["risk_weight"],
            level=bot_budget["level"],
            budget=bot_budget["budget"],
            bot_index=bot_index,
            t_div=t_div
        )

        bots.append(bot)
        bot_index += 1

    return {
        "market_stage": market_stage,
        "total_budget": total_budget,
        "cash_reserve": cash_reserve,
        "investable": investable,
        "per_bot_budget": per_bot_budget,
        "level_counts": level_counts,
        "ticker_allocations": ticker_allocations,
        "ticker_bot_levels": ticker_bot_levels,
        "bots": bots
    }

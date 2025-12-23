"""External Hantoo API Integration"""
from data.external.hantoo.hantoo_models import (
    HantooExd,
    PriceOutput,
    Balance1,
    Balance2,
    BalanceResult,
    OrderDetail,
    AvailableAmount,
    BalanceForTickers,
    BalanceForTickerOutput1,
    BalanceForTickerOutput2,
    BalanceForTickerOutput3,
    TickerItem
)
from data.external.hantoo.hantoo_data_source import HantooDataSource, HantooAccountInfo
from data.external.hantoo.hantoo_exchange_repository_impl import HantooExchangeRepositoryImpl

# 하위 호환성을 위한 별칭 (deprecated, 추후 제거 예정)
HantooClient = HantooDataSource
HantooService = HantooExchangeRepositoryImpl

__all__ = [
    # Models
    'HantooExd',
    'PriceOutput',
    'Balance1',
    'Balance2',
    'BalanceResult',
    'OrderDetail',
    'AvailableAmount',
    'BalanceForTickers',
    'BalanceForTickerOutput1',
    'BalanceForTickerOutput2',
    'BalanceForTickerOutput3',
    'TickerItem',
    # DataSource
    'HantooDataSource',
    'HantooAccountInfo',
    # Repository
    'HantooExchangeRepositoryImpl',
    # Deprecated aliases
    'HantooClient',
    'HantooService',
]

"""
Alternative Data Feeds Module
Sentiment, on-chain metrics, funding rates, order flow
"""

from .alternative_data import (
    AlternativeDataFeed,
    SentimentData,
    OnChainData,
    FundingData,
    OrderFlowData,
    EdgeDetector,
    create_alternative_feed,
)

__all__ = [
    "AlternativeDataFeed",
    "SentimentData",
    "OnChainData",
    "FundingData",
    "OrderFlowData",
    "EdgeDetector",
    "create_alternative_feed",
]

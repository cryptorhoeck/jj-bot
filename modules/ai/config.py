"""
AI Configuration Module for JJ-Bot
Centralized configuration for all AI components
"""

import os
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from enum import Enum


class AIProvider(Enum):
    """Supported AI providers"""
    ANTHROPIC = "anthropic"
    OPENAI = "openai"  # Future support
    LOCAL = "local"     # Future support for local models


class AnalysisType(Enum):
    """Types of AI analysis"""
    SENTIMENT = "sentiment"
    TRADE_DECISION = "trade_decision"
    SIGNAL_ENHANCEMENT = "signal_enhancement"
    RISK_ASSESSMENT = "risk_assessment"
    MARKET_SUMMARY = "market_summary"
    DOCUMENT_ANALYSIS = "document_analysis"


@dataclass
class AIConfig:
    """
    Centralized AI configuration for JJ-Bot

    Environment variables:
    - ANTHROPIC_API_KEY: API key for Claude
    - AI_MODEL: Model to use (default: claude-sonnet-4-20250514)
    - AI_MAX_TOKENS: Max response tokens (default: 1024)
    - AI_TEMPERATURE: Response temperature (default: 0.3)
    - AI_CACHE_TTL: Cache time-to-live in seconds (default: 300)
    - AI_ENABLED: Enable/disable AI features (default: true)
    """

    # Provider settings
    provider: AIProvider = AIProvider.ANTHROPIC
    api_key: Optional[str] = None

    # Model settings
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 1024
    temperature: float = 0.3

    # Performance settings
    timeout: int = 30  # API timeout in seconds
    max_retries: int = 3
    retry_delay: float = 1.0

    # Caching settings
    cache_enabled: bool = True
    cache_ttl: int = 300  # Cache TTL in seconds (5 minutes)
    max_cache_size: int = 100  # Maximum cached responses

    # Feature flags
    enabled: bool = True
    sentiment_analysis_enabled: bool = True
    trade_decision_enabled: bool = True
    signal_enhancement_enabled: bool = True
    risk_assessment_enabled: bool = True

    # Analysis parameters
    min_confidence_threshold: float = 0.6
    sentiment_weight: float = 0.2  # Weight of AI sentiment in final signal

    # Rate limiting
    requests_per_minute: int = 20

    # Prompts configuration
    system_prompts: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        """Load from environment variables if not set"""
        if self.api_key is None:
            self.api_key = os.environ.get("ANTHROPIC_API_KEY")

        # Override from environment
        if os.environ.get("AI_MODEL"):
            self.model = os.environ.get("AI_MODEL")
        if os.environ.get("AI_MAX_TOKENS"):
            self.max_tokens = int(os.environ.get("AI_MAX_TOKENS"))
        if os.environ.get("AI_TEMPERATURE"):
            self.temperature = float(os.environ.get("AI_TEMPERATURE"))
        if os.environ.get("AI_CACHE_TTL"):
            self.cache_ttl = int(os.environ.get("AI_CACHE_TTL"))
        if os.environ.get("AI_ENABLED"):
            self.enabled = os.environ.get("AI_ENABLED", "true").lower() == "true"

        # Set default system prompts
        if not self.system_prompts:
            self.system_prompts = DEFAULT_SYSTEM_PROMPTS.copy()

    @property
    def is_configured(self) -> bool:
        """Check if AI is properly configured"""
        return bool(self.api_key) and self.enabled

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary (excluding sensitive data)"""
        return {
            "provider": self.provider.value,
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "timeout": self.timeout,
            "cache_enabled": self.cache_enabled,
            "cache_ttl": self.cache_ttl,
            "enabled": self.enabled,
            "is_configured": self.is_configured,
            "sentiment_analysis_enabled": self.sentiment_analysis_enabled,
            "trade_decision_enabled": self.trade_decision_enabled,
            "signal_enhancement_enabled": self.signal_enhancement_enabled,
            "risk_assessment_enabled": self.risk_assessment_enabled,
            "min_confidence_threshold": self.min_confidence_threshold,
            "sentiment_weight": self.sentiment_weight,
            "requests_per_minute": self.requests_per_minute,
        }


# Default system prompts for different analysis types
DEFAULT_SYSTEM_PROMPTS = {
    AnalysisType.SENTIMENT.value: """You are an expert cryptocurrency market analyst.
Analyze the provided market data and determine the overall market sentiment.
Consider price action, volume, technical indicators, and any provided context.
Respond with a JSON object containing:
- sentiment: "bullish", "bearish", or "neutral"
- confidence: float between 0 and 1
- reasoning: brief explanation (1-2 sentences)
- key_factors: list of main factors influencing the sentiment""",

    AnalysisType.TRADE_DECISION.value: """You are an expert trading analyst for JJ-Bot, an automated cryptocurrency trading system.
Analyze the provided signal and market context to make a trade recommendation.
Consider:
- Technical indicators (RSI, MACD, Bollinger Bands, moving averages)
- Price action and trend
- Risk/reward ratio
- Market conditions

Respond with a JSON object containing:
- action: "BUY", "SELL", or "HOLD"
- confidence: float between 0 and 1
- reasoning: detailed explanation of your decision
- risk_level: "low", "medium", or "high"
- suggested_position_size: percentage of portfolio (0.01 to 0.10)
- stop_loss_pct: suggested stop loss percentage
- take_profit_pct: suggested take profit percentage""",

    AnalysisType.SIGNAL_ENHANCEMENT.value: """You are an expert trading signal analyst.
Evaluate the provided trading signal from technical analysis and enhance it with additional context.
Your goal is to improve signal quality by:
1. Confirming or questioning the signal based on broader context
2. Adjusting confidence based on market conditions
3. Identifying potential risks not captured by technical analysis

Respond with a JSON object containing:
- enhanced_action: "BUY", "SELL", or "HOLD"
- original_action: the original signal action
- enhanced_confidence: adjusted confidence (0-1)
- original_confidence: the original signal strength
- adjustment_reason: why you adjusted (or confirmed) the signal
- additional_considerations: list of factors to watch
- recommended: boolean indicating if trade is recommended""",

    AnalysisType.RISK_ASSESSMENT.value: """You are a risk management expert for cryptocurrency trading.
Assess the risk of the proposed trade based on current market conditions.
Consider:
- Market volatility
- Position sizing
- Portfolio exposure
- Current drawdown
- Market regime (trending/ranging/volatile)

Respond with a JSON object containing:
- risk_score: float 0-10 (0=lowest risk, 10=highest risk)
- risk_level: "low", "medium", "high", or "extreme"
- max_recommended_position: percentage of portfolio
- concerns: list of specific risk concerns
- mitigations: suggested risk mitigation strategies
- proceed: boolean indicating if trade should proceed""",

    AnalysisType.MARKET_SUMMARY.value: """You are a cryptocurrency market analyst.
Provide a concise market summary based on the provided data.
Include:
- Overall market direction
- Key movers and their context
- Notable patterns or setups
- Short-term outlook (next 1-4 hours)

Respond with a JSON object containing:
- summary: 2-3 sentence market overview
- direction: "bullish", "bearish", or "sideways"
- key_levels: dict with support and resistance levels
- opportunities: list of potential trading opportunities
- warnings: list of things to watch out for""",

    AnalysisType.DOCUMENT_ANALYSIS.value: """You are a financial research analyst.
Analyze the provided document content and extract relevant trading insights.
Focus on:
- Key takeaways relevant to cryptocurrency trading
- Actionable insights
- Risk factors mentioned
- Market outlook or predictions

Respond with a JSON object containing:
- summary: brief document summary
- key_insights: list of main insights
- trading_implications: how this affects trading decisions
- sentiment_impact: "positive", "negative", or "neutral"
- confidence: how confident are you in these insights (0-1)""",
}


# Global config instance
_ai_config: Optional[AIConfig] = None


def get_ai_config() -> AIConfig:
    """Get the global AI configuration instance"""
    global _ai_config
    if _ai_config is None:
        _ai_config = AIConfig()
    return _ai_config


def update_ai_config(**kwargs) -> AIConfig:
    """Update the global AI configuration"""
    global _ai_config
    config = get_ai_config()
    for key, value in kwargs.items():
        if hasattr(config, key):
            setattr(config, key, value)
    return config


def reset_ai_config() -> AIConfig:
    """Reset AI configuration to defaults"""
    global _ai_config
    _ai_config = AIConfig()
    return _ai_config

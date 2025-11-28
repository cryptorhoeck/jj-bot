"""
LLM Client - Claude API Integration
====================================

Provides AI-powered market analysis, reasoning, and decision support
for the JJ-Bot trading system.

Usage:
    from modules.ai.llm_client import LLMClient

    client = LLMClient()
    analysis = await client.analyze_market_conditions(market_data)
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
import json

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

from .config import AIConfig, LLMConfig

logger = logging.getLogger(__name__)


@dataclass
class MarketAnalysis:
    """Structured market analysis result from LLM."""
    timestamp: datetime
    sentiment: str  # bullish, bearish, neutral
    confidence: float  # 0-1
    reasoning: str
    recommended_action: str  # buy, sell, hold
    risk_assessment: str  # low, medium, high
    key_factors: List[str]
    raw_response: Optional[str] = None


@dataclass
class TradeReasoning:
    """LLM reasoning for a specific trade decision."""
    should_trade: bool
    direction: str  # long, short, none
    confidence: float
    entry_rationale: str
    exit_strategy: str
    risk_factors: List[str]
    position_size_suggestion: float  # 0-1 as fraction of available capital


class LLMClient:
    """
    Claude API client for AI-powered trading analysis.

    Provides:
    - Market sentiment analysis
    - Trade decision reasoning
    - News/document analysis
    - Strategy explanation and optimization suggestions
    """

    def __init__(self, config: Optional[AIConfig] = None):
        self.config = config or AIConfig.from_env()
        self.llm_config = self.config.llm

        if not HAS_ANTHROPIC:
            logger.warning("anthropic package not installed. Run: pip install anthropic")
            self.client = None
        elif not self.llm_config.api_key:
            logger.warning("ANTHROPIC_API_KEY not set. LLM features disabled.")
            self.client = None
        else:
            self.client = anthropic.Anthropic(api_key=self.llm_config.api_key)

        # Simple in-memory cache
        self._cache: Dict[str, tuple] = {}  # key -> (result, timestamp)

    @property
    def is_available(self) -> bool:
        """Check if LLM client is properly configured and available."""
        return self.client is not None

    def _get_cache_key(self, method: str, data: Dict) -> str:
        """Generate cache key from method and data."""
        return f"{method}:{json.dumps(data, sort_keys=True)}"

    def _get_cached(self, key: str) -> Optional[Any]:
        """Get cached result if still valid."""
        if key in self._cache:
            result, timestamp = self._cache[key]
            age = (datetime.now() - timestamp).total_seconds()
            if age < self.llm_config.cache_ttl_seconds:
                return result
            else:
                del self._cache[key]
        return None

    def _set_cached(self, key: str, result: Any):
        """Cache a result."""
        if self.llm_config.cache_responses:
            self._cache[key] = (result, datetime.now())

    async def analyze_market_conditions(
        self,
        market_data: Dict[str, Any],
        symbols: Optional[List[str]] = None,
        include_technical: bool = True
    ) -> MarketAnalysis:
        """
        Analyze current market conditions using Claude.

        Args:
            market_data: Dict containing price data, volumes, indicators
            symbols: Specific symbols to focus on (default: all)
            include_technical: Include technical indicator analysis

        Returns:
            MarketAnalysis with sentiment, reasoning, and recommendations
        """
        if not self.is_available:
            return self._fallback_analysis()

        # Check cache
        cache_key = self._get_cache_key("analyze_market", market_data)
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        # Build prompt
        prompt = self._build_market_analysis_prompt(market_data, symbols, include_technical)

        try:
            response = await asyncio.to_thread(
                self.client.messages.create,
                model=self.llm_config.model,
                max_tokens=self.llm_config.max_tokens,
                temperature=self.llm_config.temperature,
                messages=[{"role": "user", "content": prompt}]
            )

            result = self._parse_market_analysis(response.content[0].text)
            self._set_cached(cache_key, result)
            return result

        except Exception as e:
            logger.error(f"LLM market analysis failed: {e}")
            return self._fallback_analysis()

    async def get_trade_reasoning(
        self,
        symbol: str,
        current_price: float,
        indicators: Dict[str, float],
        position: Optional[Dict] = None,
        recent_trades: Optional[List[Dict]] = None
    ) -> TradeReasoning:
        """
        Get AI reasoning for whether to take a trade.

        Args:
            symbol: Trading symbol (e.g., "BTC")
            current_price: Current market price
            indicators: Dict of technical indicators (RSI, MACD, etc.)
            position: Current position if any
            recent_trades: Recent trade history for context

        Returns:
            TradeReasoning with decision and rationale
        """
        if not self.is_available:
            return self._fallback_trade_reasoning()

        prompt = self._build_trade_reasoning_prompt(
            symbol, current_price, indicators, position, recent_trades
        )

        try:
            response = await asyncio.to_thread(
                self.client.messages.create,
                model=self.llm_config.model,
                max_tokens=self.llm_config.max_tokens,
                temperature=self.llm_config.temperature,
                messages=[{"role": "user", "content": prompt}]
            )

            return self._parse_trade_reasoning(response.content[0].text)

        except Exception as e:
            logger.error(f"LLM trade reasoning failed: {e}")
            return self._fallback_trade_reasoning()

    async def analyze_document(
        self,
        content: str,
        document_type: str = "research",
        extract_signals: bool = True
    ) -> Dict[str, Any]:
        """
        Analyze a document (research paper, news, etc.) for trading insights.

        Args:
            content: Document text content
            document_type: Type of document (research, news, report)
            extract_signals: Whether to extract actionable trading signals

        Returns:
            Dict with summary, key points, and optional trading signals
        """
        if not self.is_available:
            return {"error": "LLM not available", "summary": "", "signals": []}

        prompt = f"""Analyze this {document_type} document for cryptocurrency trading insights.

Document:
{content[:8000]}  # Truncate for token limits

Provide:
1. Brief summary (2-3 sentences)
2. Key points relevant to crypto trading
3. {"Actionable trading signals if any" if extract_signals else ""}
4. Confidence in the analysis (low/medium/high)

Format as JSON with keys: summary, key_points, signals, confidence"""

        try:
            response = await asyncio.to_thread(
                self.client.messages.create,
                model=self.llm_config.model,
                max_tokens=self.llm_config.max_tokens,
                temperature=self.llm_config.temperature,
                messages=[{"role": "user", "content": prompt}]
            )

            return self._parse_json_response(response.content[0].text)

        except Exception as e:
            logger.error(f"Document analysis failed: {e}")
            return {"error": str(e), "summary": "", "signals": []}

    def _build_market_analysis_prompt(
        self,
        market_data: Dict,
        symbols: Optional[List[str]],
        include_technical: bool
    ) -> str:
        """Build the prompt for market analysis."""
        symbols_str = ", ".join(symbols) if symbols else "all available"

        prompt = f"""You are an expert cryptocurrency market analyst. Analyze the following market data and provide a comprehensive assessment.

Market Data:
{json.dumps(market_data, indent=2, default=str)}

Focus on: {symbols_str}
{"Include technical indicator analysis." if include_technical else ""}

Provide your analysis as JSON with these exact keys:
- sentiment: "bullish", "bearish", or "neutral"
- confidence: float 0-1
- reasoning: string explaining your analysis
- recommended_action: "buy", "sell", or "hold"
- risk_assessment: "low", "medium", or "high"
- key_factors: list of strings with key factors influencing your analysis

Be concise but thorough. Base analysis on the data provided."""

        return prompt

    def _build_trade_reasoning_prompt(
        self,
        symbol: str,
        price: float,
        indicators: Dict,
        position: Optional[Dict],
        recent_trades: Optional[List[Dict]]
    ) -> str:
        """Build the prompt for trade reasoning."""
        position_str = json.dumps(position) if position else "None"
        trades_str = json.dumps(recent_trades[-5:]) if recent_trades else "None"

        return f"""You are a cryptocurrency trading advisor. Evaluate whether to take a trade.

Symbol: {symbol}
Current Price: ${price:,.2f}
Technical Indicators: {json.dumps(indicators)}
Current Position: {position_str}
Recent Trades: {trades_str}

Provide your recommendation as JSON with these exact keys:
- should_trade: boolean
- direction: "long", "short", or "none"
- confidence: float 0-1
- entry_rationale: string
- exit_strategy: string describing when to exit
- risk_factors: list of risk considerations
- position_size_suggestion: float 0-1 (fraction of available capital)

Be conservative and prioritize capital preservation."""

    def _parse_market_analysis(self, response: str) -> MarketAnalysis:
        """Parse LLM response into MarketAnalysis."""
        try:
            data = self._parse_json_response(response)
            return MarketAnalysis(
                timestamp=datetime.now(),
                sentiment=data.get("sentiment", "neutral"),
                confidence=float(data.get("confidence", 0.5)),
                reasoning=data.get("reasoning", ""),
                recommended_action=data.get("recommended_action", "hold"),
                risk_assessment=data.get("risk_assessment", "medium"),
                key_factors=data.get("key_factors", []),
                raw_response=response
            )
        except Exception as e:
            logger.error(f"Failed to parse market analysis: {e}")
            return self._fallback_analysis()

    def _parse_trade_reasoning(self, response: str) -> TradeReasoning:
        """Parse LLM response into TradeReasoning."""
        try:
            data = self._parse_json_response(response)
            return TradeReasoning(
                should_trade=data.get("should_trade", False),
                direction=data.get("direction", "none"),
                confidence=float(data.get("confidence", 0.0)),
                entry_rationale=data.get("entry_rationale", ""),
                exit_strategy=data.get("exit_strategy", ""),
                risk_factors=data.get("risk_factors", []),
                position_size_suggestion=float(data.get("position_size_suggestion", 0.0))
            )
        except Exception as e:
            logger.error(f"Failed to parse trade reasoning: {e}")
            return self._fallback_trade_reasoning()

    def _parse_json_response(self, response: str) -> Dict:
        """Extract JSON from LLM response."""
        # Try to find JSON in the response
        import re

        # Look for JSON block
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        # Try parsing the whole response
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {"raw": response}

    def _fallback_analysis(self) -> MarketAnalysis:
        """Return neutral analysis when LLM is unavailable."""
        return MarketAnalysis(
            timestamp=datetime.now(),
            sentiment="neutral",
            confidence=0.0,
            reasoning="LLM analysis unavailable - using fallback",
            recommended_action="hold",
            risk_assessment="high",
            key_factors=["LLM unavailable"]
        )

    def _fallback_trade_reasoning(self) -> TradeReasoning:
        """Return conservative reasoning when LLM is unavailable."""
        return TradeReasoning(
            should_trade=False,
            direction="none",
            confidence=0.0,
            entry_rationale="LLM unavailable - no trade recommended",
            exit_strategy="N/A",
            risk_factors=["LLM system unavailable"],
            position_size_suggestion=0.0
        )

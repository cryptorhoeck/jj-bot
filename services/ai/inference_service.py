"""
AI Inference Service
====================

Background service that provides real-time AI analysis
and integrates with the trading engine.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from modules.ai.llm_client import LLMClient, MarketAnalysis, TradeReasoning
from modules.ai.config import AIConfig

logger = logging.getLogger(__name__)


@dataclass
class AIServiceStatus:
    """Status of the AI inference service."""
    running: bool = False
    started_at: Optional[datetime] = None
    analyses_performed: int = 0
    last_analysis_at: Optional[datetime] = None
    errors: int = 0
    llm_available: bool = False


@dataclass
class CachedAnalysis:
    """Cached market analysis with expiry."""
    analysis: MarketAnalysis
    created_at: datetime
    expires_at: datetime


class AIInferenceService:
    """
    Service that provides AI-powered analysis for trading decisions.

    Integrates with:
    - Market data feed for real-time prices
    - Strategy engine for signal enhancement
    - Trading bot for decision support

    Usage:
        service = AIInferenceService()
        await service.start()

        # Get analysis
        analysis = await service.get_market_analysis(market_data)

        # Get trade reasoning
        reasoning = await service.get_trade_recommendation(symbol, price, indicators)

        await service.stop()
    """

    def __init__(self, config: Optional[AIConfig] = None):
        self.config = config or AIConfig.from_env()
        self.llm_client = LLMClient(self.config)
        self.status = AIServiceStatus(llm_available=self.llm_client.is_available)

        # Analysis cache
        self._analysis_cache: Dict[str, CachedAnalysis] = {}
        self._cache_ttl = timedelta(minutes=5)

        # Background task
        self._running = False
        self._task: Optional[asyncio.Task] = None

    @property
    def is_running(self) -> bool:
        return self._running

    async def start(self):
        """Start the AI inference service."""
        if self._running:
            logger.warning("AI service already running")
            return

        logger.info("Starting AI Inference Service...")

        # Validate configuration
        errors = self.config.validate()
        if errors:
            for error in errors:
                logger.warning(f"Config warning: {error}")

        self._running = True
        self.status.running = True
        self.status.started_at = datetime.now()
        self.status.llm_available = self.llm_client.is_available

        logger.info(f"AI Service started. LLM available: {self.status.llm_available}")

    async def stop(self):
        """Stop the AI inference service."""
        if not self._running:
            return

        logger.info("Stopping AI Inference Service...")
        self._running = False
        self.status.running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        logger.info("AI Service stopped")

    async def get_market_analysis(
        self,
        market_data: Dict[str, Any],
        force_refresh: bool = False
    ) -> MarketAnalysis:
        """
        Get AI analysis of current market conditions.

        Args:
            market_data: Current market data
            force_refresh: Bypass cache and get fresh analysis

        Returns:
            MarketAnalysis with sentiment and recommendations
        """
        if not self.config.enable_llm_analysis:
            return self._disabled_analysis()

        # Check cache
        cache_key = self._make_cache_key(market_data)
        if not force_refresh and cache_key in self._analysis_cache:
            cached = self._analysis_cache[cache_key]
            if datetime.now() < cached.expires_at:
                return cached.analysis

        # Get fresh analysis
        try:
            analysis = await self.llm_client.analyze_market_conditions(market_data)
            self.status.analyses_performed += 1
            self.status.last_analysis_at = datetime.now()

            # Cache result
            self._analysis_cache[cache_key] = CachedAnalysis(
                analysis=analysis,
                created_at=datetime.now(),
                expires_at=datetime.now() + self._cache_ttl
            )

            return analysis

        except Exception as e:
            logger.error(f"Market analysis failed: {e}")
            self.status.errors += 1
            return self._error_analysis(str(e))

    async def get_trade_recommendation(
        self,
        symbol: str,
        current_price: float,
        indicators: Dict[str, float],
        position: Optional[Dict] = None
    ) -> TradeReasoning:
        """
        Get AI recommendation for a potential trade.

        Args:
            symbol: Trading symbol
            current_price: Current price
            indicators: Technical indicators
            position: Current position if any

        Returns:
            TradeReasoning with recommendation and rationale
        """
        if not self.config.enable_llm_analysis:
            return self._disabled_reasoning()

        try:
            reasoning = await self.llm_client.get_trade_reasoning(
                symbol=symbol,
                current_price=current_price,
                indicators=indicators,
                position=position
            )
            return reasoning

        except Exception as e:
            logger.error(f"Trade reasoning failed: {e}")
            self.status.errors += 1
            return self._error_reasoning(str(e))

    async def enhance_signal(
        self,
        signal: Dict[str, Any],
        market_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Enhance a trading signal with AI analysis.

        Takes a signal from the strategy engine and adds:
        - AI confidence score
        - Risk assessment
        - Position sizing suggestion

        Args:
            signal: Original trading signal
            market_context: Current market data

        Returns:
            Enhanced signal with AI additions
        """
        if not self.config.enable_llm_analysis or not self.llm_client.is_available:
            return signal  # Return original signal unchanged

        try:
            # Get AI reasoning for this signal
            reasoning = await self.get_trade_recommendation(
                symbol=signal.get("symbol", ""),
                current_price=signal.get("price", 0),
                indicators=signal.get("indicators", {})
            )

            # Enhance signal
            enhanced = signal.copy()
            enhanced["ai_enhanced"] = True
            enhanced["ai_confidence"] = reasoning.confidence
            enhanced["ai_should_trade"] = reasoning.should_trade
            enhanced["ai_reasoning"] = reasoning.entry_rationale
            enhanced["ai_risk_factors"] = reasoning.risk_factors
            enhanced["ai_position_size"] = reasoning.position_size_suggestion

            return enhanced

        except Exception as e:
            logger.error(f"Signal enhancement failed: {e}")
            signal["ai_enhanced"] = False
            signal["ai_error"] = str(e)
            return signal

    def get_status(self) -> Dict[str, Any]:
        """Get current service status."""
        return {
            "running": self.status.running,
            "started_at": self.status.started_at.isoformat() if self.status.started_at else None,
            "llm_available": self.status.llm_available,
            "analyses_performed": self.status.analyses_performed,
            "last_analysis_at": self.status.last_analysis_at.isoformat() if self.status.last_analysis_at else None,
            "errors": self.status.errors,
            "cache_size": len(self._analysis_cache),
            "config": {
                "llm_model": self.config.llm.model,
                "llm_enabled": self.config.enable_llm_analysis,
                "document_learning_enabled": self.config.enable_document_learning,
            }
        }

    def _make_cache_key(self, data: Dict) -> str:
        """Create cache key from data."""
        import json
        import hashlib
        serialized = json.dumps(data, sort_keys=True, default=str)
        return hashlib.md5(serialized.encode()).hexdigest()

    def _disabled_analysis(self) -> MarketAnalysis:
        """Return when LLM analysis is disabled."""
        return MarketAnalysis(
            timestamp=datetime.now(),
            sentiment="neutral",
            confidence=0.0,
            reasoning="LLM analysis disabled in configuration",
            recommended_action="hold",
            risk_assessment="unknown",
            key_factors=["AI disabled"]
        )

    def _disabled_reasoning(self) -> TradeReasoning:
        """Return when LLM analysis is disabled."""
        return TradeReasoning(
            should_trade=False,
            direction="none",
            confidence=0.0,
            entry_rationale="LLM analysis disabled",
            exit_strategy="N/A",
            risk_factors=["AI disabled"],
            position_size_suggestion=0.0
        )

    def _error_analysis(self, error: str) -> MarketAnalysis:
        """Return when analysis fails."""
        return MarketAnalysis(
            timestamp=datetime.now(),
            sentiment="neutral",
            confidence=0.0,
            reasoning=f"Analysis failed: {error}",
            recommended_action="hold",
            risk_assessment="high",
            key_factors=["Error occurred"]
        )

    def _error_reasoning(self, error: str) -> TradeReasoning:
        """Return when reasoning fails."""
        return TradeReasoning(
            should_trade=False,
            direction="none",
            confidence=0.0,
            entry_rationale=f"Reasoning failed: {error}",
            exit_strategy="N/A",
            risk_factors=["Error occurred"],
            position_size_suggestion=0.0
        )

"""
AI Inference Service for JJ-Bot
Provides real-time AI analysis integrated with the trading system
"""

import os
import sys
import time
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

# Add paths
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from services.base.service import BaseService
from modules.ai.config import AIConfig, get_ai_config, AnalysisType
from modules.ai.llm_client import LLMClient, LLMResponse, get_llm_client
from modules.event_bus import event_bus

# Configure logging
logger = logging.getLogger("jjbot.ai.inference")


@dataclass
class EnhancedSignal:
    """Trading signal enhanced with AI analysis"""
    original_signal: Dict[str, Any]
    ai_analysis: Optional[Dict[str, Any]] = None
    enhanced_action: str = "HOLD"
    enhanced_strength: float = 0.0
    ai_confidence: float = 0.0
    recommendation: str = "hold"
    reasoning: str = ""
    risk_level: str = "unknown"
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_signal": self.original_signal,
            "ai_analysis": self.ai_analysis,
            "enhanced_action": self.enhanced_action,
            "enhanced_strength": self.enhanced_strength,
            "ai_confidence": self.ai_confidence,
            "recommendation": self.recommendation,
            "reasoning": self.reasoning,
            "risk_level": self.risk_level,
            "timestamp": self.timestamp
        }


class AIInferenceService(BaseService):
    """
    AI Inference Service - Real-time AI analysis for trading

    Features:
    - Signal enhancement with AI analysis
    - Market sentiment analysis
    - Risk assessment
    - Trade decision support

    Listens to: TRADING_SIGNAL events
    Publishes: AI_ENHANCED_SIGNAL events
    """

    def __init__(self):
        super().__init__(name="ai_inference", auto_start=True)

        # AI components
        self.config: AIConfig = get_ai_config()
        self.llm_client: Optional[LLMClient] = None

        # Analysis state
        self.last_sentiment: Optional[Dict[str, Any]] = None
        self.enhanced_signals: List[EnhancedSignal] = []
        self.max_signal_history = 100

        # Configuration
        self.service_config = {
            "auto_enhance_signals": True,
            "min_signal_strength": 0.5,  # Only enhance signals above this threshold
            "sentiment_update_interval": 300,  # Update sentiment every 5 minutes
            "enhance_on_event": True,  # Enhance signals on TRADING_SIGNAL events
        }

        # Stats tracking
        self.stats = {
            "signals_processed": 0,
            "signals_enhanced": 0,
            "signals_confirmed": 0,
            "signals_adjusted": 0,
            "signals_rejected": 0,
            "ai_errors": 0,
            "avg_enhancement_time_ms": 0,
            "last_analysis": None
        }

    def _run(self):
        """Initialize and run the AI inference service"""
        print("[AI] AI Inference Service starting...")

        try:
            # Initialize LLM client
            self.llm_client = get_llm_client()

            if not self.llm_client.is_available:
                print("[WARNING] AI client not available (no API key). Running in fallback mode.")
            else:
                print(f"[OK] AI client initialized: {self.config.model}")

            # Subscribe to trading signals for enhancement
            if self.service_config["enhance_on_event"]:
                event_bus.subscribe("TRADING_SIGNAL", self._on_trading_signal)
                print("[INFO] Subscribed to TRADING_SIGNAL events")

            self.stats["last_analysis"] = datetime.now().isoformat()
            print("[OK] AI Inference Service started")

            # Main service loop
            last_sentiment_update = 0
            while self.status == "running":
                try:
                    # Periodic sentiment update
                    now = time.time()
                    if now - last_sentiment_update > self.service_config["sentiment_update_interval"]:
                        # Note: In production, this would fetch real market data
                        last_sentiment_update = now

                    time.sleep(1)

                except Exception as e:
                    logger.error(f"AI service loop error: {e}")
                    time.sleep(5)

        except Exception as e:
            print(f"[ERROR] AI Inference Service error: {e}")
            logger.error(f"AI Inference Service failed: {e}")
            self.status = "stopped"

    def _cleanup(self):
        """Cleanup when stopping"""
        # Unsubscribe from events
        try:
            event_bus.unsubscribe("TRADING_SIGNAL", self._on_trading_signal)
            print("[STOP] AI Inference Service stopped")
        except Exception as e:
            print(f"[WARNING] Error during cleanup: {e}")

    def _on_trading_signal(self, event: Dict[str, Any]):
        """Handle incoming trading signals"""
        try:
            signal = event.get("data", {})

            # Only process signals above threshold
            strength = signal.get("strength", 0)
            if strength < self.service_config["min_signal_strength"]:
                return

            # Enhance the signal
            if self.service_config["auto_enhance_signals"]:
                enhanced = self.enhance_signal(signal)

                # Publish enhanced signal
                if enhanced:
                    event_bus.publish("AI_ENHANCED_SIGNAL", enhanced.to_dict())

        except Exception as e:
            logger.error(f"Error processing trading signal: {e}")
            self.stats["ai_errors"] += 1

    def enhance_signal(
        self,
        signal: Dict[str, Any],
        market_data: Optional[Dict[str, Any]] = None
    ) -> Optional[EnhancedSignal]:
        """
        Enhance a trading signal with AI analysis

        Args:
            signal: Original trading signal from strategy engine
            market_data: Optional additional market data

        Returns:
            EnhancedSignal with AI analysis, or None if enhancement failed
        """
        start_time = time.time()
        self.stats["signals_processed"] += 1

        # If AI not available, return original signal with no enhancement
        if not self.llm_client or not self.llm_client.is_available:
            return self._fallback_enhancement(signal)

        try:
            # Get AI analysis
            response = self.llm_client.enhance_signal(signal, market_data)

            if not response.success:
                logger.warning(f"AI enhancement failed: {response.error}")
                self.stats["ai_errors"] += 1
                return self._fallback_enhancement(signal)

            # Parse AI response
            ai_content = response.content or {}

            # Create enhanced signal
            enhanced = EnhancedSignal(
                original_signal=signal,
                ai_analysis=ai_content,
                enhanced_action=ai_content.get("enhanced_action", signal.get("action", "HOLD")),
                enhanced_strength=ai_content.get("enhanced_confidence", signal.get("strength", 0)),
                ai_confidence=ai_content.get("enhanced_confidence", 0),
                recommendation="execute" if ai_content.get("recommended", False) else "hold",
                reasoning=ai_content.get("adjustment_reason", ""),
                risk_level=ai_content.get("risk_level", "unknown")
            )

            # Update stats
            self.stats["signals_enhanced"] += 1

            # Track if signal was confirmed, adjusted, or rejected
            original_action = signal.get("action", "HOLD")
            if enhanced.enhanced_action == original_action:
                if enhanced.recommendation == "execute":
                    self.stats["signals_confirmed"] += 1
                else:
                    self.stats["signals_rejected"] += 1
            else:
                self.stats["signals_adjusted"] += 1

            # Update timing stats
            elapsed_ms = (time.time() - start_time) * 1000
            self.stats["avg_enhancement_time_ms"] = (
                (self.stats["avg_enhancement_time_ms"] * (self.stats["signals_enhanced"] - 1) + elapsed_ms)
                / self.stats["signals_enhanced"]
            )

            # Store in history
            self.enhanced_signals.append(enhanced)
            if len(self.enhanced_signals) > self.max_signal_history:
                self.enhanced_signals.pop(0)

            self.stats["last_analysis"] = datetime.now().isoformat()

            # Log the enhancement
            symbol = signal.get("symbol", "?")
            logger.info(
                f"Enhanced signal for {symbol}: "
                f"{original_action} -> {enhanced.enhanced_action} "
                f"(confidence: {enhanced.ai_confidence:.2f}, "
                f"rec: {enhanced.recommendation})"
            )

            return enhanced

        except Exception as e:
            logger.error(f"Error enhancing signal: {e}")
            self.stats["ai_errors"] += 1
            return self._fallback_enhancement(signal)

    def _fallback_enhancement(self, signal: Dict[str, Any]) -> EnhancedSignal:
        """Create a fallback enhanced signal when AI is unavailable"""
        return EnhancedSignal(
            original_signal=signal,
            ai_analysis=None,
            enhanced_action=signal.get("action", "HOLD"),
            enhanced_strength=signal.get("strength", 0),
            ai_confidence=0,
            recommendation="hold",  # Default to hold without AI confirmation
            reasoning="AI analysis unavailable - using original signal without enhancement",
            risk_level="unknown"
        )

    def analyze_sentiment(
        self,
        market_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Analyze market sentiment

        Args:
            market_data: Market data for sentiment analysis

        Returns:
            Sentiment analysis result or None
        """
        if not self.llm_client or not self.llm_client.is_available:
            return None

        try:
            response = self.llm_client.analyze_sentiment(market_data)

            if response.success:
                self.last_sentiment = {
                    "result": response.content,
                    "timestamp": datetime.now().isoformat(),
                    "symbol": market_data.get("symbol"),
                    "cached": response.cached
                }
                return self.last_sentiment

            return None

        except Exception as e:
            logger.error(f"Error analyzing sentiment: {e}")
            return None

    def assess_trade_risk(
        self,
        trade: Dict[str, Any],
        portfolio: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Assess risk for a proposed trade

        Args:
            trade: Proposed trade details
            portfolio: Current portfolio state

        Returns:
            Risk assessment or None
        """
        if not self.llm_client or not self.llm_client.is_available:
            return None

        try:
            response = self.llm_client.assess_risk(trade, portfolio)

            if response.success:
                return {
                    "assessment": response.content,
                    "timestamp": datetime.now().isoformat(),
                    "cached": response.cached
                }

            return None

        except Exception as e:
            logger.error(f"Error assessing risk: {e}")
            return None

    def get_market_summary(
        self,
        market_data: Dict[str, Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Generate a market summary

        Args:
            market_data: Dictionary of symbol -> market data

        Returns:
            Market summary or None
        """
        if not self.llm_client or not self.llm_client.is_available:
            return None

        try:
            response = self.llm_client.generate_market_summary(market_data)

            if response.success:
                return {
                    "summary": response.content,
                    "timestamp": datetime.now().isoformat(),
                    "cached": response.cached
                }

            return None

        except Exception as e:
            logger.error(f"Error generating market summary: {e}")
            return None

    def analyze_document(
        self,
        document_content: str,
        document_type: str = "general"
    ) -> Optional[Dict[str, Any]]:
        """
        Analyze a document for trading insights

        Args:
            document_content: Document text content
            document_type: Type of document

        Returns:
            Document analysis or None
        """
        if not self.llm_client or not self.llm_client.is_available:
            return None

        try:
            response = self.llm_client.analyze_document(document_content, document_type)

            if response.success:
                return {
                    "analysis": response.content,
                    "timestamp": datetime.now().isoformat(),
                    "document_type": document_type
                }

            return None

        except Exception as e:
            logger.error(f"Error analyzing document: {e}")
            return None

    def get_enhanced_signals(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent enhanced signals"""
        return [s.to_dict() for s in self.enhanced_signals[-limit:]]

    def get_last_sentiment(self) -> Optional[Dict[str, Any]]:
        """Get the most recent sentiment analysis"""
        return self.last_sentiment

    def update_config(self, new_config: Dict[str, Any]) -> bool:
        """
        Update service configuration

        Args:
            new_config: New configuration values

        Returns:
            True if successful
        """
        try:
            self.service_config.update(new_config)
            print(f"[OK] AI Inference config updated: {new_config}")
            return True
        except Exception as e:
            print(f"[ERROR] Error updating config: {e}")
            return False

    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive service status"""
        llm_stats = self.llm_client.get_stats() if self.llm_client else {}

        return {
            "name": self.name,
            "status": self.status,
            "ai_available": self.llm_client.is_available if self.llm_client else False,
            "model": self.config.model,
            "config": self.service_config,
            "stats": self.stats,
            "llm_stats": llm_stats,
            "last_sentiment": self.last_sentiment,
            "enhanced_signals_count": len(self.enhanced_signals)
        }


# Global service instance
ai_inference_service = AIInferenceService()

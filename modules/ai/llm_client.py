"""
LLM Client Module for JJ-Bot
Provides Claude API integration for AI-powered analysis
"""

import os
import sys
import json
import time
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from collections import OrderedDict
import threading

# Add parent path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from modules.ai.config import AIConfig, get_ai_config, AnalysisType

# Configure logging
logger = logging.getLogger("jjbot.ai.llm_client")


@dataclass
class LLMResponse:
    """Structured response from LLM"""
    success: bool
    content: Optional[Dict[str, Any]] = None
    raw_text: Optional[str] = None
    error: Optional[str] = None
    model: Optional[str] = None
    tokens_used: int = 0
    latency_ms: float = 0
    cached: bool = False
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class ResponseCache:
    """
    LRU cache for LLM responses to reduce API calls and latency
    Thread-safe implementation
    """

    def __init__(self, max_size: int = 100, ttl_seconds: int = 300):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: OrderedDict = OrderedDict()
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    def _make_key(self, prompt: str, analysis_type: str) -> str:
        """Generate cache key from prompt and analysis type"""
        content = f"{analysis_type}:{prompt}"
        return hashlib.md5(content.encode()).hexdigest()

    def get(self, prompt: str, analysis_type: str) -> Optional[LLMResponse]:
        """Get cached response if valid"""
        key = self._make_key(prompt, analysis_type)

        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None

            entry = self._cache[key]

            # Check TTL
            if datetime.now() > entry["expires"]:
                del self._cache[key]
                self._misses += 1
                return None

            # Move to end (most recently used)
            self._cache.move_to_end(key)
            self._hits += 1

            # Return cached response marked as cached
            response = entry["response"]
            response.cached = True
            return response

    def set(self, prompt: str, analysis_type: str, response: LLMResponse):
        """Store response in cache"""
        key = self._make_key(prompt, analysis_type)

        with self._lock:
            # Remove oldest if at capacity
            if len(self._cache) >= self.max_size:
                self._cache.popitem(last=False)

            self._cache[key] = {
                "response": response,
                "expires": datetime.now() + timedelta(seconds=self.ttl_seconds)
            }

    def clear(self):
        """Clear all cached responses"""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            total = self._hits + self._misses
            hit_rate = (self._hits / total * 100) if total > 0 else 0
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate_pct": round(hit_rate, 2),
                "ttl_seconds": self.ttl_seconds
            }


class LLMClient:
    """
    Claude API client for JJ-Bot
    Handles all LLM interactions with caching, retries, and graceful fallbacks
    """

    def __init__(self, config: Optional[AIConfig] = None):
        self.config = config or get_ai_config()
        self._client = None
        self._cache = ResponseCache(
            max_size=self.config.max_cache_size,
            ttl_seconds=self.config.cache_ttl
        )
        self._request_times: List[float] = []
        self._lock = threading.Lock()

        # Statistics
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_tokens": 0,
            "avg_latency_ms": 0,
            "last_request": None
        }

        # Initialize client
        self._init_client()

    def _init_client(self):
        """Initialize the Anthropic client"""
        if not self.config.api_key:
            logger.warning("No ANTHROPIC_API_KEY found. AI features will be disabled.")
            return

        try:
            import anthropic
            self._client = anthropic.Anthropic(api_key=self.config.api_key)
            logger.info(f"Anthropic client initialized with model: {self.config.model}")
        except ImportError:
            logger.error("anthropic package not installed. Run: pip install anthropic")
            self._client = None
        except Exception as e:
            logger.error(f"Failed to initialize Anthropic client: {e}")
            self._client = None

    @property
    def is_available(self) -> bool:
        """Check if LLM client is available and configured"""
        return self._client is not None and self.config.enabled

    def _check_rate_limit(self) -> bool:
        """Check if we're within rate limits"""
        with self._lock:
            now = time.time()
            # Remove requests older than 1 minute
            self._request_times = [t for t in self._request_times if now - t < 60]

            if len(self._request_times) >= self.config.requests_per_minute:
                return False

            self._request_times.append(now)
            return True

    def _parse_json_response(self, text: str) -> Optional[Dict[str, Any]]:
        """Parse JSON from LLM response, handling markdown code blocks"""
        try:
            # Try direct JSON parse first
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try to extract JSON from markdown code blocks
        import re

        # Match ```json ... ``` or ``` ... ```
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # Try to find JSON object in text
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        return None

    def analyze(
        self,
        prompt: str,
        analysis_type: AnalysisType,
        context: Optional[Dict[str, Any]] = None,
        use_cache: bool = True
    ) -> LLMResponse:
        """
        Perform AI analysis on the given prompt

        Args:
            prompt: The analysis prompt/question
            analysis_type: Type of analysis to perform
            context: Additional context data to include
            use_cache: Whether to use cached responses

        Returns:
            LLMResponse with analysis results
        """
        start_time = time.time()
        self.stats["total_requests"] += 1
        self.stats["last_request"] = datetime.now().isoformat()

        # Check if AI is available
        if not self.is_available:
            return LLMResponse(
                success=False,
                error="AI client not available. Check API key configuration.",
                latency_ms=(time.time() - start_time) * 1000
            )

        # Check cache first
        if use_cache and self.config.cache_enabled:
            cached = self._cache.get(prompt, analysis_type.value)
            if cached:
                logger.debug(f"Cache hit for {analysis_type.value}")
                self.stats["successful_requests"] += 1
                return cached

        # Check rate limit
        if not self._check_rate_limit():
            return LLMResponse(
                success=False,
                error="Rate limit exceeded. Please wait before making more requests.",
                latency_ms=(time.time() - start_time) * 1000
            )

        # Build the full prompt
        system_prompt = self.config.system_prompts.get(
            analysis_type.value,
            "You are an expert trading analyst. Respond with valid JSON."
        )

        # Add context if provided
        full_prompt = prompt
        if context:
            context_str = json.dumps(context, indent=2, default=str)
            full_prompt = f"{prompt}\n\nAdditional Context:\n{context_str}"

        # Make API call with retries
        last_error = None
        for attempt in range(self.config.max_retries):
            try:
                response = self._client.messages.create(
                    model=self.config.model,
                    max_tokens=self.config.max_tokens,
                    temperature=self.config.temperature,
                    system=system_prompt,
                    messages=[
                        {"role": "user", "content": full_prompt}
                    ]
                )

                # Extract response text
                raw_text = response.content[0].text
                tokens_used = response.usage.input_tokens + response.usage.output_tokens

                # Parse JSON response
                content = self._parse_json_response(raw_text)

                latency_ms = (time.time() - start_time) * 1000

                # Update stats
                self.stats["successful_requests"] += 1
                self.stats["total_tokens"] += tokens_used
                total_successful = self.stats["successful_requests"]
                self.stats["avg_latency_ms"] = (
                    (self.stats["avg_latency_ms"] * (total_successful - 1) + latency_ms)
                    / total_successful
                )

                result = LLMResponse(
                    success=True,
                    content=content,
                    raw_text=raw_text,
                    model=self.config.model,
                    tokens_used=tokens_used,
                    latency_ms=latency_ms,
                    cached=False
                )

                # Cache the response
                if use_cache and self.config.cache_enabled and content:
                    self._cache.set(prompt, analysis_type.value, result)

                return result

            except Exception as e:
                last_error = str(e)
                logger.warning(f"LLM request failed (attempt {attempt + 1}/{self.config.max_retries}): {e}")

                if attempt < self.config.max_retries - 1:
                    time.sleep(self.config.retry_delay * (attempt + 1))

        # All retries failed
        self.stats["failed_requests"] += 1
        return LLMResponse(
            success=False,
            error=f"Request failed after {self.config.max_retries} attempts: {last_error}",
            latency_ms=(time.time() - start_time) * 1000
        )

    def analyze_sentiment(self, market_data: Dict[str, Any]) -> LLMResponse:
        """
        Analyze market sentiment from price and indicator data

        Args:
            market_data: Dictionary containing price, volume, and indicator data

        Returns:
            LLMResponse with sentiment analysis
        """
        prompt = f"""Analyze the following market data and provide sentiment analysis:

Symbol: {market_data.get('symbol', 'Unknown')}
Current Price: ${market_data.get('price', 0):,.2f}
24h Change: {market_data.get('change_24h', 0):.2f}%
Volume 24h: ${market_data.get('volume_24h', 0):,.0f}

Technical Indicators:
- RSI: {market_data.get('rsi', 'N/A')}
- MACD: {market_data.get('macd', 'N/A')}
- SMA Fast: {market_data.get('sma_fast', 'N/A')}
- SMA Slow: {market_data.get('sma_slow', 'N/A')}
"""
        return self.analyze(prompt, AnalysisType.SENTIMENT, market_data)

    def analyze_trade_signal(
        self,
        signal: Dict[str, Any],
        market_context: Optional[Dict[str, Any]] = None
    ) -> LLMResponse:
        """
        Analyze a trading signal and provide trade decision

        Args:
            signal: Trading signal from strategy engine
            market_context: Additional market context

        Returns:
            LLMResponse with trade decision
        """
        prompt = f"""Evaluate this trading signal and provide a trade recommendation:

Signal Details:
- Symbol: {signal.get('symbol', 'Unknown')}
- Action: {signal.get('action', 'Unknown')}
- Price: ${signal.get('price', 0):,.2f}
- Signal Strength: {signal.get('strength', 0):.2f}
- Reasons: {', '.join(signal.get('reason', []))}

Technical Indicators:
{json.dumps(signal.get('indicators', {}), indent=2, default=str)}
"""
        return self.analyze(prompt, AnalysisType.TRADE_DECISION, market_context)

    def enhance_signal(
        self,
        signal: Dict[str, Any],
        market_data: Optional[Dict[str, Any]] = None
    ) -> LLMResponse:
        """
        Enhance a trading signal with AI analysis

        Args:
            signal: Original trading signal
            market_data: Current market data

        Returns:
            LLMResponse with enhanced signal
        """
        prompt = f"""Evaluate and potentially enhance this trading signal:

Original Signal:
- Symbol: {signal.get('symbol', 'Unknown')}
- Action: {signal.get('action', 'Unknown')}
- Strength: {signal.get('strength', 0):.2f}
- Price: ${signal.get('price', 0):,.2f}
- Technical Reasons: {', '.join(signal.get('reason', []))}

Your task is to:
1. Confirm or adjust the signal based on the technical analysis
2. Assess if the signal strength is appropriate
3. Identify any risks not captured in the technical analysis
4. Provide a recommendation on whether to proceed
"""
        context = {
            "original_signal": signal,
            "market_data": market_data
        }
        return self.analyze(prompt, AnalysisType.SIGNAL_ENHANCEMENT, context)

    def assess_risk(
        self,
        trade: Dict[str, Any],
        portfolio: Dict[str, Any]
    ) -> LLMResponse:
        """
        Assess risk for a proposed trade

        Args:
            trade: Proposed trade details
            portfolio: Current portfolio state

        Returns:
            LLMResponse with risk assessment
        """
        prompt = f"""Assess the risk of this proposed trade:

Proposed Trade:
- Symbol: {trade.get('symbol', 'Unknown')}
- Action: {trade.get('action', 'Unknown')}
- Position Size: {trade.get('position_size', 0):.2%} of portfolio
- Entry Price: ${trade.get('price', 0):,.2f}

Portfolio State:
- Total Equity: ${portfolio.get('equity', 0):,.2f}
- Open Positions: {portfolio.get('open_positions', 0)}
- Current Drawdown: {portfolio.get('drawdown', 0):.2%}
- Daily P&L: ${portfolio.get('daily_pnl', 0):,.2f}
"""
        context = {"trade": trade, "portfolio": portfolio}
        return self.analyze(prompt, AnalysisType.RISK_ASSESSMENT, context)

    def generate_market_summary(
        self,
        market_data: Dict[str, Dict[str, Any]]
    ) -> LLMResponse:
        """
        Generate a market summary from multiple assets

        Args:
            market_data: Dictionary of symbol -> market data

        Returns:
            LLMResponse with market summary
        """
        # Format market data for prompt
        summary_lines = []
        for symbol, data in market_data.items():
            price = data.get('price', 0)
            change = data.get('change_24h', 0)
            summary_lines.append(f"- {symbol}: ${price:,.2f} ({change:+.2f}%)")

        prompt = f"""Provide a market summary for the following assets:

{chr(10).join(summary_lines)}

Include overall market direction, notable patterns, and short-term outlook.
"""
        return self.analyze(prompt, AnalysisType.MARKET_SUMMARY, market_data)

    def analyze_document(self, document_content: str, document_type: str = "general") -> LLMResponse:
        """
        Analyze a document for trading insights

        Args:
            document_content: Text content of the document
            document_type: Type of document (research, news, report, etc.)

        Returns:
            LLMResponse with document analysis
        """
        # Truncate if too long
        max_length = 10000
        if len(document_content) > max_length:
            document_content = document_content[:max_length] + "\n\n[Content truncated...]"

        prompt = f"""Analyze this {document_type} document and extract trading-relevant insights:

---
{document_content}
---

Focus on actionable insights, market implications, and risk factors.
"""
        return self.analyze(
            prompt,
            AnalysisType.DOCUMENT_ANALYSIS,
            {"document_type": document_type},
            use_cache=False  # Don't cache document analysis
        )

    def clear_cache(self):
        """Clear the response cache"""
        self._cache.clear()
        logger.info("LLM response cache cleared")

    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics"""
        return {
            **self.stats,
            "cache": self._cache.get_stats(),
            "is_available": self.is_available,
            "model": self.config.model,
            "config": self.config.to_dict()
        }


# Global client instance
_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """Get the global LLM client instance"""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client


def reset_llm_client():
    """Reset the global LLM client"""
    global _llm_client
    _llm_client = None

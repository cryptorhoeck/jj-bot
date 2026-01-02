"""
AI Analysis API Endpoints for JJ-Bot

Provides access to:
- AI status and configuration
- Market sentiment analysis
- Signal enhancement
- Trade risk assessment
- Market summaries
- Document analysis
"""

from fastapi import APIRouter, HTTPException, Query, Body
from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

# Import AI modules
from modules.ai.config import get_ai_config, update_ai_config, AnalysisType
from modules.ai.llm_client import get_llm_client, LLMClient
from services.ai.inference_service import ai_inference_service, AIInferenceService

router = APIRouter(prefix="/api/ai", tags=["ai"])


# ===== Pydantic Models =====

class SentimentRequest(BaseModel):
    """Request model for sentiment analysis"""
    symbol: str
    price: float
    change_24h: float = 0.0
    volume_24h: float = 0.0
    rsi: Optional[float] = None
    macd: Optional[float] = None
    sma_fast: Optional[float] = None
    sma_slow: Optional[float] = None


class SignalEnhanceRequest(BaseModel):
    """Request model for signal enhancement"""
    symbol: str
    action: str  # BUY, SELL, HOLD
    price: float
    strength: float
    reason: List[str] = []
    indicators: Optional[Dict[str, Any]] = None


class RiskAssessmentRequest(BaseModel):
    """Request model for risk assessment"""
    symbol: str
    action: str
    position_size: float  # As percentage of portfolio (0.01 = 1%)
    price: float
    equity: float
    open_positions: int = 0
    drawdown: float = 0.0
    daily_pnl: float = 0.0


class DocumentAnalysisRequest(BaseModel):
    """Request model for document analysis"""
    content: str
    document_type: str = "general"  # general, research, news, report


class AIConfigUpdate(BaseModel):
    """Request model for AI config updates"""
    enabled: Optional[bool] = None
    sentiment_analysis_enabled: Optional[bool] = None
    trade_decision_enabled: Optional[bool] = None
    signal_enhancement_enabled: Optional[bool] = None
    min_confidence_threshold: Optional[float] = None
    sentiment_weight: Optional[float] = None
    cache_enabled: Optional[bool] = None


# ===== Status & Configuration Endpoints =====

@router.get("/status", summary="Get AI System Status")
async def get_ai_status() -> Dict[str, Any]:
    """
    Get comprehensive status of the AI system

    Returns:
        AI configuration, availability, and service stats
    """
    try:
        config = get_ai_config()
        llm_client = get_llm_client()

        # Get service status
        service_status = ai_inference_service.get_status()

        return {
            "success": True,
            "status": {
                "enabled": config.enabled,
                "available": llm_client.is_available,
                "configured": config.is_configured,
                "model": config.model,
                "provider": config.provider.value,
                "service_running": service_status.get("status") == "running"
            },
            "config": config.to_dict(),
            "service": service_status,
            "features": {
                "sentiment_analysis": config.sentiment_analysis_enabled,
                "trade_decisions": config.trade_decision_enabled,
                "signal_enhancement": config.signal_enhancement_enabled,
                "risk_assessment": config.risk_assessment_enabled
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health", summary="AI Health Check")
async def ai_health_check() -> Dict[str, Any]:
    """
    Quick health check for AI services

    Returns:
        Health status and basic metrics
    """
    try:
        config = get_ai_config()
        llm_client = get_llm_client()
        stats = llm_client.get_stats()

        return {
            "healthy": llm_client.is_available,
            "model": config.model,
            "requests": stats.get("total_requests", 0),
            "success_rate": (
                stats.get("successful_requests", 0) /
                max(stats.get("total_requests", 1), 1) * 100
            ),
            "avg_latency_ms": stats.get("avg_latency_ms", 0),
            "cache_hit_rate": stats.get("cache", {}).get("hit_rate_pct", 0),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "healthy": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@router.post("/config", summary="Update AI Configuration")
async def update_ai_configuration(config_update: AIConfigUpdate) -> Dict[str, Any]:
    """
    Update AI system configuration

    Args:
        config_update: Configuration values to update

    Returns:
        Updated configuration
    """
    try:
        # Filter out None values
        updates = {k: v for k, v in config_update.dict().items() if v is not None}

        if not updates:
            raise HTTPException(status_code=400, detail="No configuration values provided")

        config = update_ai_config(**updates)

        return {
            "success": True,
            "message": "AI configuration updated",
            "config": config.to_dict()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== AI Service Management =====

@router.post("/service/start", summary="Start AI Inference Service")
async def start_ai_service() -> Dict[str, Any]:
    """
    Start the AI inference service

    Returns:
        Service start status
    """
    try:
        if ai_inference_service.status == "running":
            return {
                "success": True,
                "message": "AI service already running",
                "status": ai_inference_service.get_status()
            }

        result = ai_inference_service.start()
        return {
            "success": result.get("success", False),
            "message": result.get("message", ""),
            "status": ai_inference_service.get_status()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/service/stop", summary="Stop AI Inference Service")
async def stop_ai_service() -> Dict[str, Any]:
    """
    Stop the AI inference service

    Returns:
        Service stop status
    """
    try:
        result = ai_inference_service.stop()
        return {
            "success": result.get("success", False),
            "message": result.get("message", ""),
            "status": ai_inference_service.get_status()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== Analysis Endpoints =====

@router.post("/analyze/sentiment", summary="Analyze Market Sentiment")
async def analyze_sentiment(request: SentimentRequest) -> Dict[str, Any]:
    """
    Analyze market sentiment for a symbol

    Args:
        request: Market data for sentiment analysis

    Returns:
        Sentiment analysis result
    """
    try:
        config = get_ai_config()
        if not config.sentiment_analysis_enabled:
            raise HTTPException(status_code=400, detail="Sentiment analysis is disabled")

        llm_client = get_llm_client()
        if not llm_client.is_available:
            raise HTTPException(
                status_code=503,
                detail="AI service unavailable. Check API key configuration."
            )

        market_data = request.dict()
        response = llm_client.analyze_sentiment(market_data)

        if not response.success:
            return {
                "success": False,
                "error": response.error,
                "latency_ms": response.latency_ms
            }

        return {
            "success": True,
            "sentiment": response.content,
            "cached": response.cached,
            "latency_ms": response.latency_ms,
            "timestamp": response.timestamp
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze/signal", summary="Enhance Trading Signal")
async def enhance_signal(request: SignalEnhanceRequest) -> Dict[str, Any]:
    """
    Enhance a trading signal with AI analysis

    Args:
        request: Trading signal to enhance

    Returns:
        Enhanced signal with AI recommendations
    """
    try:
        config = get_ai_config()
        if not config.signal_enhancement_enabled:
            raise HTTPException(status_code=400, detail="Signal enhancement is disabled")

        # Use the inference service for enhancement
        signal = request.dict()
        enhanced = ai_inference_service.enhance_signal(signal)

        if not enhanced:
            return {
                "success": False,
                "error": "Failed to enhance signal"
            }

        return {
            "success": True,
            "enhanced_signal": enhanced.to_dict(),
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze/risk", summary="Assess Trade Risk")
async def assess_risk(request: RiskAssessmentRequest) -> Dict[str, Any]:
    """
    Assess risk for a proposed trade

    Args:
        request: Trade and portfolio details

    Returns:
        Risk assessment with recommendations
    """
    try:
        config = get_ai_config()
        if not config.risk_assessment_enabled:
            raise HTTPException(status_code=400, detail="Risk assessment is disabled")

        trade = {
            "symbol": request.symbol,
            "action": request.action,
            "position_size": request.position_size,
            "price": request.price
        }

        portfolio = {
            "equity": request.equity,
            "open_positions": request.open_positions,
            "drawdown": request.drawdown,
            "daily_pnl": request.daily_pnl
        }

        result = ai_inference_service.assess_trade_risk(trade, portfolio)

        if not result:
            return {
                "success": False,
                "error": "Risk assessment unavailable"
            }

        return {
            "success": True,
            "risk_assessment": result,
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze/document", summary="Analyze Document for Trading Insights")
async def analyze_document(request: DocumentAnalysisRequest) -> Dict[str, Any]:
    """
    Analyze a document for trading insights

    Args:
        request: Document content and type

    Returns:
        Document analysis with trading implications
    """
    try:
        if len(request.content) < 50:
            raise HTTPException(
                status_code=400,
                detail="Document content too short (minimum 50 characters)"
            )

        result = ai_inference_service.analyze_document(
            request.content,
            request.document_type
        )

        if not result:
            return {
                "success": False,
                "error": "Document analysis unavailable"
            }

        return {
            "success": True,
            "analysis": result,
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/market/summary", summary="Get AI Market Summary")
async def get_market_summary(
    symbols: str = Query(
        "BTC,ETH,SOL",
        description="Comma-separated list of symbols"
    )
) -> Dict[str, Any]:
    """
    Generate AI market summary for multiple symbols

    Args:
        symbols: Comma-separated symbol list

    Returns:
        Market summary with analysis
    """
    try:
        symbol_list = [s.strip().upper() for s in symbols.split(",")]

        # Build market data from current prices
        # In production, this would fetch real market data
        market_data = {}
        for symbol in symbol_list[:10]:  # Limit to 10 symbols
            market_data[symbol] = {
                "symbol": symbol,
                "price": 0,  # Would be fetched from market service
                "change_24h": 0
            }

        result = ai_inference_service.get_market_summary(market_data)

        if not result:
            return {
                "success": False,
                "error": "Market summary unavailable"
            }

        return {
            "success": True,
            "market_summary": result,
            "symbols": symbol_list,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== History & Stats Endpoints =====

@router.get("/signals/enhanced", summary="Get Enhanced Signal History")
async def get_enhanced_signals(
    limit: int = Query(10, ge=1, le=100, description="Number of signals to return")
) -> Dict[str, Any]:
    """
    Get recent AI-enhanced signals

    Args:
        limit: Maximum number of signals to return

    Returns:
        List of enhanced signals
    """
    try:
        signals = ai_inference_service.get_enhanced_signals(limit)
        return {
            "success": True,
            "signals": signals,
            "count": len(signals),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sentiment/latest", summary="Get Latest Sentiment Analysis")
async def get_latest_sentiment() -> Dict[str, Any]:
    """
    Get the most recent sentiment analysis

    Returns:
        Latest sentiment analysis or null
    """
    try:
        sentiment = ai_inference_service.get_last_sentiment()
        return {
            "success": True,
            "sentiment": sentiment,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", summary="Get AI Statistics")
async def get_ai_stats() -> Dict[str, Any]:
    """
    Get comprehensive AI system statistics

    Returns:
        Statistics for AI service and LLM client
    """
    try:
        llm_client = get_llm_client()
        llm_stats = llm_client.get_stats()
        service_status = ai_inference_service.get_status()

        return {
            "success": True,
            "llm_stats": llm_stats,
            "service_stats": service_status.get("stats", {}),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cache/clear", summary="Clear AI Response Cache")
async def clear_ai_cache() -> Dict[str, Any]:
    """
    Clear the LLM response cache

    Returns:
        Success status
    """
    try:
        llm_client = get_llm_client()
        llm_client.clear_cache()
        return {
            "success": True,
            "message": "AI cache cleared",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== Debug/Test Endpoints =====

@router.post("/test", summary="Test AI Connection")
async def test_ai_connection() -> Dict[str, Any]:
    """
    Test AI connection with a simple prompt

    Returns:
        Test result
    """
    try:
        llm_client = get_llm_client()

        if not llm_client.is_available:
            return {
                "success": False,
                "error": "AI client not available. Check ANTHROPIC_API_KEY.",
                "timestamp": datetime.now().isoformat()
            }

        # Simple test analysis
        response = llm_client.analyze(
            "Respond with a JSON object containing: {\"status\": \"ok\", \"message\": \"AI connection successful\"}",
            AnalysisType.SENTIMENT,
            use_cache=False
        )

        return {
            "success": response.success,
            "response": response.content,
            "raw_text": response.raw_text[:500] if response.raw_text else None,
            "latency_ms": response.latency_ms,
            "model": response.model,
            "error": response.error,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

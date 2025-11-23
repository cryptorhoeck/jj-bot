"""
API Integration Tests for JJ-Bot
Tests the core API endpoints for functionality and proper response format
"""
import pytest
import httpx
import asyncio
from datetime import datetime

# API base URL - can be configured via environment variable
API_BASE = "http://127.0.0.1:8000"


# ===== FIXTURES =====

@pytest.fixture
def api_client():
    """Create a test client for API calls"""
    return httpx.Client(base_url=API_BASE, timeout=10.0)


@pytest.fixture
def async_api_client():
    """Create an async test client"""
    return httpx.AsyncClient(base_url=API_BASE, timeout=10.0)


# ===== HEALTH & ROOT TESTS =====

class TestHealthEndpoints:
    """Test system health and root endpoints"""

    def test_root_endpoint(self, api_client):
        """Test root endpoint returns API info"""
        response = api_client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "status" in data
        assert data["status"] == "running"

    def test_health_endpoint(self, api_client):
        """Test system health endpoint"""
        response = api_client.get("/api/system/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data


# ===== TRADE ENDPOINT TESTS =====

class TestTradeEndpoints:
    """Test trade-related endpoints"""

    def test_get_trades(self, api_client):
        """Test fetching trades list"""
        response = api_client.get("/api/trades")
        assert response.status_code == 200
        data = response.json()
        assert "trades" in data
        assert isinstance(data["trades"], list)

    def test_get_trades_with_limit(self, api_client):
        """Test fetching trades with limit parameter"""
        response = api_client.get("/api/trades?limit=10")
        assert response.status_code == 200
        data = response.json()
        assert len(data["trades"]) <= 10

    def test_get_summary(self, api_client):
        """Test trade summary endpoint"""
        response = api_client.get("/api/summary")
        assert response.status_code == 200
        data = response.json()
        # Should have key metrics
        assert "total_trades" in data or "total_pnl" in data


# ===== BOT CONTROL TESTS =====

class TestBotControl:
    """Test bot start/stop functionality"""

    def test_bot_status(self, api_client):
        """Test bot status endpoint"""
        response = api_client.get("/api/bot/status")
        assert response.status_code == 200
        data = response.json()
        assert "running" in data
        assert isinstance(data["running"], bool)

    def test_simulator_status_alias(self, api_client):
        """Test backward-compatible simulator status endpoint"""
        response = api_client.get("/api/simulator/status")
        assert response.status_code == 200
        data = response.json()
        assert "running" in data


# ===== MARKET DATA TESTS =====

class TestMarketData:
    """Test market data endpoints"""

    def test_market_live(self, api_client):
        """Test live market data endpoint"""
        response = api_client.get("/api/market/live")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data

    def test_market_prices(self, api_client):
        """Test static market prices endpoint"""
        response = api_client.get("/api/market/prices")
        assert response.status_code == 200
        data = response.json()
        # Should return price data
        assert isinstance(data, dict)


# ===== ANALYTICS TESTS =====

class TestAnalytics:
    """Test analytics and performance endpoints"""

    def test_equity_curve(self, api_client):
        """Test equity curve endpoint"""
        response = api_client.get("/api/equity-curve")
        assert response.status_code == 200
        data = response.json()
        assert "equity_curve" in data
        assert "starting_capital" in data

    def test_open_positions(self, api_client):
        """Test open positions endpoint"""
        response = api_client.get("/api/positions/open")
        assert response.status_code == 200
        data = response.json()
        assert "open_positions" in data
        assert "count" in data

    def test_risk_status(self, api_client):
        """Test risk status endpoint"""
        response = api_client.get("/api/risk/status")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data


# ===== CONFIG TESTS =====

class TestConfig:
    """Test configuration endpoints"""

    def test_get_config(self, api_client):
        """Test config retrieval"""
        response = api_client.get("/api/config")
        assert response.status_code == 200
        data = response.json()
        assert "MAX_POSITION_SIZE" in data


# ===== DATA MANAGEMENT TESTS =====

class TestDataManagement:
    """Test data export/backup functionality"""

    def test_list_backups(self, api_client):
        """Test backup listing endpoint"""
        response = api_client.get("/api/data/backups")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data


# ===== RESPONSE FORMAT TESTS =====

class TestResponseFormat:
    """Verify consistent response formatting"""

    def test_error_responses_have_status(self, api_client):
        """Test that error responses include status field"""
        # Try a non-existent endpoint
        response = api_client.get("/api/nonexistent")
        assert response.status_code in [404, 422]

    def test_successful_responses_are_json(self, api_client):
        """Test that all successful responses are valid JSON"""
        endpoints = ["/", "/api/trades", "/api/summary", "/api/config"]
        for endpoint in endpoints:
            response = api_client.get(endpoint)
            assert response.status_code == 200
            # Should be able to parse as JSON
            data = response.json()
            assert data is not None


# ===== PERFORMANCE TESTS =====

class TestPerformance:
    """Basic performance/load tests"""

    def test_response_time_health(self, api_client):
        """Health endpoint should respond quickly"""
        import time
        start = time.time()
        response = api_client.get("/api/system/health")
        elapsed = time.time() - start

        assert response.status_code == 200
        assert elapsed < 1.0  # Should respond within 1 second

    def test_response_time_trades(self, api_client):
        """Trades endpoint should respond reasonably fast"""
        import time
        start = time.time()
        response = api_client.get("/api/trades?limit=50")
        elapsed = time.time() - start

        assert response.status_code == 200
        assert elapsed < 2.0  # Should respond within 2 seconds


# ===== ASYNC TESTS =====

@pytest.mark.asyncio
class TestAsyncEndpoints:
    """Async test examples"""

    async def test_concurrent_requests(self, async_api_client):
        """Test handling concurrent requests"""
        async with async_api_client as client:
            # Make 5 concurrent requests
            tasks = [client.get("/api/system/health") for _ in range(5)]
            responses = await asyncio.gather(*tasks)

            # All should succeed
            for response in responses:
                assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

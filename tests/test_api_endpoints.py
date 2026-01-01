"""
API Endpoint Tests for JJ-Bot
Tests core API functionality including health, status, and trading endpoints
"""

import pytest
from fastapi.testclient import TestClient


class TestHealthEndpoints:
    """Test system health and status endpoints"""

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

    def test_version_endpoint(self, api_client):
        """Test version endpoint returns version info"""
        response = api_client.get("/api/system/version")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data


class TestBotStatusEndpoints:
    """Test bot status and control endpoints"""

    def test_bot_status(self, api_client):
        """Test bot status endpoint"""
        response = api_client.get("/api/bot/status")
        assert response.status_code == 200
        data = response.json()
        assert "running" in data

    def test_simulator_status_compatibility(self, api_client):
        """Test legacy simulator status endpoint still works"""
        response = api_client.get("/api/simulator/status")
        assert response.status_code == 200


class TestTradingEndpoints:
    """Test trading data endpoints"""

    def test_get_trades(self, api_client):
        """Test get trades endpoint"""
        response = api_client.get("/api/trades")
        assert response.status_code == 200
        data = response.json()
        assert "trades" in data
        assert isinstance(data["trades"], list)

    def test_get_trades_with_limit(self, api_client):
        """Test get trades with limit parameter"""
        response = api_client.get("/api/trades?limit=10")
        assert response.status_code == 200
        data = response.json()
        assert "trades" in data
        assert len(data["trades"]) <= 10

    def test_get_summary(self, api_client):
        """Test get summary endpoint"""
        response = api_client.get("/api/summary")
        assert response.status_code == 200
        data = response.json()
        # Summary should have key trading metrics
        assert "total_trades" in data or "trades" in data

    def test_get_open_positions(self, api_client):
        """Test open positions endpoint"""
        response = api_client.get("/api/positions/open")
        assert response.status_code == 200
        data = response.json()
        assert "open_positions" in data
        assert "count" in data


class TestMarketDataEndpoints:
    """Test market data endpoints"""

    def test_market_prices(self, api_client):
        """Test static market prices endpoint"""
        response = api_client.get("/api/market/prices")
        assert response.status_code == 200
        data = response.json()
        # Should return some price data
        assert isinstance(data, dict)

    def test_market_live(self, api_client):
        """Test live market data endpoint"""
        response = api_client.get("/api/market/live")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data or "data" in data


class TestConfigEndpoints:
    """Test configuration endpoints"""

    def test_get_config(self, api_client):
        """Test get config endpoint"""
        response = api_client.get("/api/config")
        assert response.status_code == 200
        data = response.json()
        # Should have some config keys
        assert isinstance(data, dict)


class TestDataManagementEndpoints:
    """Test data management endpoints"""

    def test_list_backups(self, api_client):
        """Test list backups endpoint"""
        response = api_client.get("/api/data/backups")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        if data["status"] == "success":
            assert "backups" in data
            assert "total" in data

    def test_export_data(self, api_client):
        """Test export data endpoint returns CSV"""
        response = api_client.get("/api/data/export")
        assert response.status_code == 200
        # Should be CSV content type
        assert "text/csv" in response.headers.get("content-type", "")


class TestAnalyticsEndpoints:
    """Test analytics endpoints"""

    def test_risk_status(self, api_client):
        """Test risk status endpoint"""
        response = api_client.get("/api/risk/status")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data

    def test_performance_stats(self, api_client):
        """Test performance stats endpoint"""
        response = api_client.get("/api/performance/stats")
        assert response.status_code == 200
        # Should return stats or error
        data = response.json()
        assert isinstance(data, dict)

    def test_recent_errors(self, api_client):
        """Test recent errors endpoint"""
        response = api_client.get("/api/errors/recent")
        assert response.status_code == 200
        data = response.json()
        assert "errors" in data or "error" in data


class TestWebSocketEndpoints:
    """Test WebSocket related endpoints"""

    def test_websocket_stats(self, api_client):
        """Test WebSocket stats endpoint"""
        response = api_client.get("/api/websocket/stats")
        assert response.status_code == 200
        data = response.json()
        # Should have connection stats
        assert isinstance(data, dict)


class TestRateLimitEndpoints:
    """Test rate limiting endpoints"""

    def test_ratelimit_stats(self, api_client):
        """Test rate limit stats endpoint"""
        response = api_client.get("/api/ratelimit/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_requests" in data or "config" in data


class TestErrorHandling:
    """Test error handling"""

    def test_404_not_found(self, api_client):
        """Test 404 for non-existent endpoints"""
        response = api_client.get("/api/nonexistent")
        assert response.status_code == 404

    def test_invalid_limit_parameter(self, api_client):
        """Test handling of invalid parameters"""
        response = api_client.get("/api/trades?limit=invalid")
        # Should either handle gracefully or return error
        assert response.status_code in [200, 400, 422]

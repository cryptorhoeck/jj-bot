"""
Pytest configuration and fixtures for JJ-Bot tests
"""

import os
import sys
import pytest
import asyncio
from typing import Generator
from unittest.mock import MagicMock, patch

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# Configure pytest-asyncio
pytest_plugins = ('pytest_asyncio',)


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_config():
    """Provide mock configuration for tests"""
    return {
        "mode": "paper",
        "initial_capital": 10000.0,
        "symbols": ["BTC/USD", "ETH/USD"],
        "max_position_size": 0.02,
        "stop_loss_pct": 0.02,
        "take_profit_pct": 0.04,
    }


@pytest.fixture
def mock_trade():
    """Provide mock trade data"""
    return {
        "id": 1,
        "symbol": "BTC/USD",
        "side": "buy",
        "price": 45000.0,
        "quantity": 0.1,
        "pnl": 150.0,
        "timestamp": "2026-01-01T12:00:00Z",
        "status": "closed"
    }


@pytest.fixture
def mock_position():
    """Provide mock position data"""
    return {
        "symbol": "BTC/USD",
        "side": "long",
        "entry_price": 45000.0,
        "quantity": 0.1,
        "unrealized_pnl": 100.0,
        "entry_time": "2026-01-01T12:00:00Z"
    }


@pytest.fixture
def api_client():
    """Create test client for API"""
    from fastapi.testclient import TestClient
    from glue.api.main import app

    client = TestClient(app)
    yield client


@pytest.fixture
def async_api_client():
    """Create async test client for API"""
    from httpx import AsyncClient, ASGITransport
    from glue.api.main import app

    async def get_client():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

    return get_client


@pytest.fixture
def mock_auth_manager():
    """Mock authentication manager"""
    with patch('modules.auth.auth_manager') as mock:
        mock.is_auth_enabled.return_value = False
        mock.config.users = {}
        yield mock


@pytest.fixture
def mock_rate_limiter():
    """Mock rate limiter"""
    with patch('modules.rate_limit_middleware.rate_limiter') as mock:
        mock.check_rate_limit.return_value = (True, {})
        yield mock


@pytest.fixture
def sample_ohlc_data():
    """Provide sample OHLC data for testing"""
    return [
        {"timestamp": 1704067200000, "open": 45000, "high": 45500, "low": 44800, "close": 45200, "volume": 100},
        {"timestamp": 1704070800000, "open": 45200, "high": 45800, "low": 45100, "close": 45600, "volume": 120},
        {"timestamp": 1704074400000, "open": 45600, "high": 46000, "low": 45400, "close": 45800, "volume": 150},
    ]


@pytest.fixture
def sample_user_credentials():
    """Provide sample user credentials for testing"""
    return {
        "username": "testuser",
        "password": "testpassword123"
    }


# Cleanup fixture
@pytest.fixture(autouse=True)
def cleanup():
    """Clean up after each test"""
    yield
    # Add cleanup logic here if needed

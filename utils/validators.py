"""
Pydantic validators for API request/response validation
Ensures data integrity and provides clear error messages
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, validator, root_validator
from enum import Enum


class SignalType(str, Enum):
    """Trading signal types"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class TradeModel(BaseModel):
    """Validation model for trade data"""
    timestamp: str = Field(..., description="ISO format timestamp")
    symbol: str = Field(..., min_length=1, max_length=20, description="Trading symbol")
    signal: SignalType = Field(..., description="Trading signal (BUY/SELL/HOLD)")
    last_price: float = Field(..., gt=0, description="Last trade price")
    vwap: float = Field(..., gt=0, description="Volume-weighted average price")
    pnl: float = Field(default=0.0, description="Profit and loss")

    @validator('timestamp')
    def validate_timestamp(cls, v):
        """Ensure timestamp is valid ISO format"""
        try:
            datetime.fromisoformat(v.replace('Z', '+00:00'))
        except ValueError:
            raise ValueError(f"Invalid timestamp format: {v}. Must be ISO 8601 format")
        return v

    @validator('symbol')
    def validate_symbol(cls, v):
        """Ensure symbol is uppercase"""
        return v.upper().strip()

    class Config:
        use_enum_values = True
        json_schema_extra = {
            "example": {
                "timestamp": "2025-01-14T12:00:00Z",
                "symbol": "BTC",
                "signal": "BUY",
                "last_price": 45000.0,
                "vwap": 45100.0,
                "pnl": 100.0
            }
        }


class BacktestConfigModel(BaseModel):
    """Validation model for backtest configuration"""
    symbol: str = Field(..., min_length=1, description="Symbol to backtest")
    start_date: str = Field(..., description="Start date (YYYY-MM-DD)")
    end_date: str = Field(..., description="End date (YYYY-MM-DD)")
    initial_capital: float = Field(default=10000.0, gt=0, description="Initial capital")
    commission: float = Field(default=0.002, ge=0, le=0.1, description="Commission rate (0.2% realistic)")
    slippage: float = Field(default=0.005, ge=0, le=0.1, description="Slippage rate (0.5% realistic)")
    strategy: str = Field(default="momentum", description="Strategy name")

    @validator('start_date', 'end_date')
    def validate_date_format(cls, v):
        """Validate date format"""
        try:
            datetime.strptime(v, '%Y-%m-%d')
        except ValueError:
            raise ValueError(f"Invalid date format: {v}. Must be YYYY-MM-DD")
        return v

    @root_validator
    def validate_date_order(cls, values):
        """Ensure end_date is after start_date"""
        start = values.get('start_date')
        end = values.get('end_date')

        if start and end:
            start_dt = datetime.strptime(start, '%Y-% m-%d')
            end_dt = datetime.strptime(end, '%Y-%m-%d')

            if end_dt <= start_dt:
                raise ValueError("end_date must be after start_date")

        return values

    class Config:
        json_schema_extra = {
            "example": {
                "symbol": "BTC",
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
                "initial_capital": 10000.0,
                "commission": 0.002,
                "slippage": 0.005,
                "strategy": "momentum"
            }
        }


class StrategyConfigModel(BaseModel):
    """Validation model for strategy configuration"""
    rsi_oversold: int = Field(default=30, ge=0, le=100, description="RSI oversold threshold")
    rsi_overbought: int = Field(default=70, ge=0, le=100, description="RSI overbought threshold")
    sma_fast: int = Field(default=10, gt=0, description="Fast SMA period")
    sma_slow: int = Field(default=20, gt=0, description="Slow SMA period")
    min_signal_strength: float = Field(default=0.7, ge=0.0, le=1.0, description="Minimum signal strength")

    @root_validator
    def validate_thresholds(cls, values):
        """Ensure RSI thresholds make sense"""
        oversold = values.get('rsi_oversold')
        overbought = values.get('rsi_overbought')

        if oversold and overbought and oversold >= overbought:
            raise ValueError("rsi_oversold must be less than rsi_overbought")

        # Ensure SMA periods make sense
        fast = values.get('sma_fast')
        slow = values.get('sma_slow')

        if fast and slow and fast >= slow:
            raise ValueError("sma_fast must be less than sma_slow")

        return values

    class Config:
        json_schema_extra = {
            "example": {
                "rsi_oversold": 30,
                "rsi_overbought": 70,
                "sma_fast": 10,
                "sma_slow": 20,
                "min_signal_strength": 0.7
            }
        }


class RiskConfigModel(BaseModel):
    """Validation model for risk management configuration"""
    max_position_size: float = Field(default=1000.0, gt=0, description="Maximum position size")
    max_daily_loss: float = Field(default=1000.0, gt=0, description="Maximum daily loss")
    max_trades_per_day: int = Field(default=20, gt=0, description="Maximum trades per day")
    cooldown_seconds: int = Field(default=60, ge=0, description="Cooldown between trades")
    max_positions: int = Field(default=5, gt=0, description="Maximum concurrent positions")
    risk_per_trade: float = Field(default=0.02, gt=0, le=1.0, description="Risk per trade")

    class Config:
        json_schema_extra = {
            "example": {
                "max_position_size": 1000.0,
                "max_daily_loss": 1000.0,
                "max_trades_per_day": 20,
                "cooldown_seconds": 60,
                "max_positions": 5,
                "risk_per_trade": 0.02
            }
        }


class MarketDataRequestModel(BaseModel):
    """Validation model for market data requests"""
    symbols: List[str] = Field(..., min_items=1, max_items=50, description="List of symbols")
    timeframe: str = Field(default="1h", description="Timeframe (1m, 5m, 15m, 30m, 1h, 4h, 1d)")
    limit: int = Field(default=100, ge=1, le=1000, description="Number of candles")

    @validator('symbols')
    def validate_symbols(cls, v):
        """Ensure symbols are uppercase and unique"""
        return list(set(s.upper().strip() for s in v))

    @validator('timeframe')
    def validate_timeframe(cls, v):
        """Ensure timeframe is valid"""
        valid_timeframes = ['1m', '5m', '15m', '30m', '1h', '4h', '1d', '1w', '1M']
        if v not in valid_timeframes:
            raise ValueError(f"Invalid timeframe. Must be one of: {', '.join(valid_timeframes)}")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "symbols": ["BTC", "ETH", "SOL"],
                "timeframe": "1h",
                "limit": 100
            }
        }


class AlertConfigModel(BaseModel):
    """Validation model for price alert configuration"""
    symbol: str = Field(..., min_length=1, description="Symbol to alert on")
    condition: str = Field(..., description="Alert condition (above/below/crosses)")
    price: float = Field(..., gt=0, description="Alert price")
    enabled: bool = Field(default=True, description="Whether alert is enabled")
    notification_channel: Optional[str] = Field(default="email", description="Notification channel")

    @validator('symbol')
    def validate_symbol(cls, v):
        """Ensure symbol is uppercase"""
        return v.upper().strip()

    @validator('condition')
    def validate_condition(cls, v):
        """Ensure condition is valid"""
        valid_conditions = ['above', 'below', 'crosses_above', 'crosses_below']
        if v.lower() not in valid_conditions:
            raise ValueError(f"Invalid condition. Must be one of: {', '.join(valid_conditions)}")
        return v.lower()

    class Config:
        json_schema_extra = {
            "example": {
                "symbol": "BTC",
                "condition": "above",
                "price": 50000.0,
                "enabled": True,
                "notification_channel": "email"
            }
        }


class AnalyticsRequestModel(BaseModel):
    """Validation model for analytics requests"""
    start_date: Optional[str] = Field(default=None, description="Start date (YYYY-MM-DD)")
    end_date: Optional[str] = Field(default=None, description="End date (YYYY-MM-DD)")
    symbols: Optional[List[str]] = Field(default=None, description="Filter by symbols")
    include_metrics: List[str] = Field(
        default=['sharpe', 'sortino', 'max_drawdown'],
        description="Metrics to include"
    )

    @validator('start_date', 'end_date')
    def validate_date_format(cls, v):
        """Validate date format"""
        if v is None:
            return v

        try:
            datetime.strptime(v, '%Y-%m-%d')
        except ValueError:
            raise ValueError(f"Invalid date format: {v}. Must be YYYY-MM-DD")
        return v

    @validator('symbols')
    def validate_symbols(cls, v):
        """Ensure symbols are uppercase"""
        if v is None:
            return v
        return [s.upper().strip() for s in v]

    class Config:
        json_schema_extra = {
            "example": {
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
                "symbols": ["BTC", "ETH"],
                "include_metrics": ["sharpe", "sortino", "max_drawdown", "win_rate"]
            }
        }


if __name__ == "__main__":
    # Test validators
    print("Testing Pydantic validators...\n")

    # Test valid trade
    trade = TradeModel(
        timestamp="2025-01-14T12:00:00Z",
        symbol="btc",
        signal="BUY",
        last_price=45000.0,
        vwap=45100.0,
        pnl=100.0
    )
    print(f"✅ Valid trade: {trade.symbol} - {trade.signal}")

    # Test invalid trade (should raise error)
    try:
        invalid_trade = TradeModel(
            timestamp="invalid",
            symbol="BTC",
            signal="BUY",
            last_price=-100,  # Negative price
            vwap=45000.0
        )
    except Exception as e:
        print(f"❌ Invalid trade caught: {e}")

    # Test backtest config
    backtest = BacktestConfigModel(
        symbol="BTC",
        start_date="2024-01-01",
        end_date="2024-12-31"
    )
    print(f"✅ Valid backtest config: {backtest.symbol} {backtest.start_date} to {backtest.end_date}")

    print("\n✅ Pydantic validators test complete!")

"""
Standardized API Response Utilities
Ensures consistent response format across all endpoints
"""
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from pydantic import BaseModel, Field, validator
from enum import Enum


# ===== RESPONSE MODELS =====

class ResponseStatus(str, Enum):
    """Standard response status values"""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    PENDING = "pending"


class APIResponse(BaseModel):
    """Standard API response format"""
    status: ResponseStatus = ResponseStatus.SUCCESS
    message: Optional[str] = None
    data: Optional[Any] = None
    error: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

    class Config:
        use_enum_values = True


class PaginatedResponse(APIResponse):
    """Response format for paginated data"""
    page: int = 1
    per_page: int = 50
    total: int = 0
    total_pages: int = 0


# ===== HELPER FUNCTIONS =====

def success_response(
    data: Any = None,
    message: str = None,
    **extra_fields
) -> Dict:
    """Create a standardized success response"""
    response = {
        "status": "success",
        "timestamp": datetime.now().isoformat(),
    }
    if data is not None:
        response["data"] = data
    if message:
        response["message"] = message
    response.update(extra_fields)
    return response


def error_response(
    message: str,
    error_code: str = None,
    details: Any = None,
    **extra_fields
) -> Dict:
    """Create a standardized error response"""
    response = {
        "status": "error",
        "message": message,
        "timestamp": datetime.now().isoformat(),
    }
    if error_code:
        response["error_code"] = error_code
    if details:
        response["details"] = details
    response.update(extra_fields)
    return response


def paginated_response(
    data: List,
    page: int = 1,
    per_page: int = 50,
    total: int = None,
    message: str = None
) -> Dict:
    """Create a standardized paginated response"""
    if total is None:
        total = len(data)

    total_pages = (total + per_page - 1) // per_page

    return {
        "status": "success",
        "data": data,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        },
        "message": message,
        "timestamp": datetime.now().isoformat()
    }


# ===== INPUT VALIDATION MODELS =====

class TradeRequest(BaseModel):
    """Validate trade execution requests"""
    symbol: str = Field(..., min_length=2, max_length=10, description="Trading symbol")
    side: str = Field(..., pattern="^(BUY|SELL)$", description="Trade side")
    quantity: float = Field(..., gt=0, description="Trade quantity")
    price: Optional[float] = Field(None, gt=0, description="Limit price")
    stop_loss: Optional[float] = Field(None, gt=0, description="Stop loss price")
    take_profit: Optional[float] = Field(None, gt=0, description="Take profit price")

    @validator('symbol')
    def uppercase_symbol(cls, v):
        return v.upper().strip()


class BotConfigRequest(BaseModel):
    """Validate bot configuration requests"""
    initial_capital: float = Field(10000, gt=0, le=10000000, description="Starting capital")
    max_open_positions: int = Field(5, ge=1, le=50, description="Maximum concurrent positions")
    position_size_pct: float = Field(0.1, gt=0, le=1, description="Position size as % of capital")
    stop_loss_pct: float = Field(0.02, gt=0, le=0.5, description="Stop loss percentage")
    take_profit_pct: float = Field(0.05, gt=0, le=1, description="Take profit percentage")
    use_stop_loss: bool = Field(True, description="Enable stop loss")
    use_take_profit: bool = Field(True, description="Enable take profit")


class SymbolToggleRequest(BaseModel):
    """Validate symbol enable/disable requests"""
    symbol: str = Field(..., min_length=2, max_length=10)
    enabled: bool

    @validator('symbol')
    def uppercase_symbol(cls, v):
        return v.upper().strip()


class BacktestRequest(BaseModel):
    """Validate backtest requests"""
    strategy: str = Field(..., min_length=1, max_length=50)
    symbols: List[str] = Field(..., min_items=1, max_items=20)
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    initial_capital: float = Field(10000, gt=0, le=10000000)


class PaginationParams(BaseModel):
    """Standard pagination parameters"""
    page: int = Field(1, ge=1, description="Page number")
    per_page: int = Field(50, ge=1, le=500, description="Items per page")
    sort_by: Optional[str] = None
    sort_order: str = Field("desc", pattern="^(asc|desc)$")


class DateRangeParams(BaseModel):
    """Date range filter parameters"""
    start_date: Optional[str] = Field(None, description="Start date (ISO format)")
    end_date: Optional[str] = Field(None, description="End date (ISO format)")

    @validator('start_date', 'end_date', pre=True)
    def validate_date_format(cls, v):
        if v:
            try:
                datetime.fromisoformat(v.replace('Z', '+00:00'))
            except ValueError:
                raise ValueError('Invalid date format. Use ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)')
        return v


# ===== ERROR CODES =====

class ErrorCodes:
    """Standard error codes for API responses"""
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    RATE_LIMITED = "RATE_LIMITED"
    SERVER_ERROR = "SERVER_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    BAD_REQUEST = "BAD_REQUEST"
    CONFLICT = "CONFLICT"
    TIMEOUT = "TIMEOUT"

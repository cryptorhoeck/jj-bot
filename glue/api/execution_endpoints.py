"""
Execution Simulation API Endpoints

Provides endpoints for testing order execution with realistic market conditions
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from pydantic import BaseModel
import sys
import os

# Add paths
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from modules.execution import ExecutionSimulator, OrderType, OrderSide, simulate_market_order

router = APIRouter(prefix="/api/execution", tags=["execution"])


# === Request/Response Models ===

class SimulateOrderRequest(BaseModel):
    """Request to simulate order execution"""
    symbol: str
    order_type: str  # market, limit, stop
    side: str  # buy, sell
    quantity: float
    price: Optional[float] = None
    current_price: float
    volatility: Optional[float] = 0.5
    market_congestion: float = 0.5
    slippage_pct: float = 0.05


class OrderbookRequest(BaseModel):
    """Request to generate orderbook"""
    mid_price: float
    spread_pct: float = 0.05
    depth_factor: float = 1.0


# === Endpoints ===

@router.post("/simulate-order")
async def simulate_order(request: SimulateOrderRequest):
    """
    Simulate realistic order execution

    Simulates order execution with:
    - Slippage based on order size and volatility
    - Execution delays based on market conditions
    - Partial fills for large orders
    - Realistic price impact

    Request body:
    {
        "symbol": "BTC",
        "order_type": "market",
        "side": "buy",
        "quantity": 1.5,
        "current_price": 50000,
        "volatility": 0.8,
        "market_congestion": 0.6,
        "slippage_pct": 0.05
    }

    Returns:
        Simulated execution result

    Example:
    - POST /api/execution/simulate-order
    """
    try:
        # Validate inputs
        try:
            order_type = OrderType(request.order_type.lower())
            side = OrderSide(request.side.lower())
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # Create simulator
        simulator = ExecutionSimulator(
            slippage_model="percentage",
            base_slippage_pct=request.slippage_pct
        )

        # Execute order
        result = await simulator.execute_order(
            symbol=request.symbol,
            order_type=order_type,
            side=side,
            quantity=request.quantity,
            price=request.price,
            current_price=request.current_price,
            volatility=request.volatility,
            market_congestion=request.market_congestion
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-orderbook")
async def generate_orderbook(request: OrderbookRequest):
    """
    Generate simulated order book

    Creates a realistic order book with bid/ask levels.

    Request body:
    {
        "mid_price": 50000,
        "spread_pct": 0.05,
        "depth_factor": 1.0
    }

    Returns:
        Simulated order book

    Example:
    - POST /api/execution/generate-orderbook
    """
    try:
        simulator = ExecutionSimulator()

        orderbook = simulator.generate_orderbook(
            mid_price=request.mid_price,
            spread_pct=request.spread_pct,
            depth_factor=request.depth_factor
        )

        return {
            'success': True,
            'orderbook': orderbook
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/simulate-impact")
async def simulate_impact(
    mid_price: float,
    quantity: float,
    side: str,
    spread_pct: float = 0.05
):
    """
    Simulate order book impact

    Analyzes how an order would impact the order book.

    Query parameters:
    - mid_price: Current mid price
    - quantity: Order quantity
    - side: 'buy' or 'sell'
    - spread_pct: Bid-ask spread percentage

    Returns:
        Impact analysis

    Example:
    - POST /api/execution/simulate-impact?mid_price=50000&quantity=10&side=buy
    """
    try:
        # Validate side
        try:
            order_side = OrderSide(side.lower())
        except ValueError:
            raise HTTPException(status_code=400, detail="Side must be 'buy' or 'sell'")

        simulator = ExecutionSimulator()

        # Generate orderbook
        orderbook = simulator.generate_orderbook(mid_price, spread_pct)

        # Simulate impact
        impact = simulator.simulate_orderbook_impact(orderbook, order_side, quantity)

        return {
            'success': True,
            'impact': impact,
            'orderbook_snapshot': {
                'mid_price': orderbook['mid_price'],
                'spread': orderbook['spread'],
                'spread_pct': orderbook['spread_pct']
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quick-simulate")
async def quick_simulate(
    price: float = Query(..., description="Current price"),
    quantity: float = Query(..., description="Order quantity"),
    side: str = Query("buy", description="Order side (buy/sell)"),
    slippage_pct: float = Query(0.05, description="Slippage percentage")
):
    """
    Quick market order simulation

    Simplified endpoint for quick order simulations.

    Query parameters:
    - price: Current market price
    - quantity: Order quantity
    - side: 'buy' or 'sell'
    - slippage_pct: Expected slippage percentage

    Returns:
        Execution result

    Examples:
    - /api/execution/quick-simulate?price=50000&quantity=1.5&side=buy
    - /api/execution/quick-simulate?price=3000&quantity=5&side=sell&slippage_pct=0.1
    """
    try:
        result = simulate_market_order(
            price=price,
            quantity=quantity,
            side=side,
            slippage_pct=slippage_pct
        )

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models")
async def get_slippage_models():
    """
    Get available slippage models

    Returns descriptions of slippage calculation models.

    Example:
    - GET /api/execution/models
    """
    return {
        'success': True,
        'models': [
            {
                'name': 'percentage',
                'description': 'Fixed percentage slippage, adjusts for volatility',
                'parameters': ['base_slippage_pct', 'volatility_multiplier']
            },
            {
                'name': 'fixed',
                'description': 'Fixed dollar amount slippage',
                'parameters': ['base_slippage_pct']
            },
            {
                'name': 'volume_based',
                'description': 'Slippage increases with order size (market impact)',
                'parameters': ['base_slippage_pct', 'volatility_multiplier']
            }
        ]
    }


@router.get("/config")
async def get_execution_config():
    """
    Get execution simulator configuration

    Returns default configuration parameters.

    Example:
    - GET /api/execution/config
    """
    simulator = ExecutionSimulator()

    return {
        'success': True,
        'config': {
            'slippage_model': simulator.slippage_model,
            'base_slippage_pct': simulator.base_slippage_pct,
            'orderbook_depth': simulator.orderbook_depth,
            'min_delay_ms': simulator.min_delay_ms,
            'max_delay_ms': simulator.max_delay_ms,
            'volatility_multiplier': simulator.volatility_multiplier
        }
    }


@router.get("/status")
async def get_execution_status():
    """
    Get execution simulation module status

    Returns module capabilities and information.

    Example:
    - GET /api/execution/status
    """
    return {
        'success': True,
        'status': 'operational',
        'capabilities': {
            'order_simulation': True,
            'slippage_modeling': True,
            'orderbook_generation': True,
            'execution_delays': True,
            'partial_fills': True,
            'market_impact': True
        },
        'supported_order_types': [ot.value for ot in OrderType],
        'supported_slippage_models': ['percentage', 'fixed', 'volume_based'],
        'endpoints': [
            'POST /api/execution/simulate-order',
            'POST /api/execution/generate-orderbook',
            'POST /api/execution/simulate-impact',
            'GET /api/execution/quick-simulate',
            'GET /api/execution/models',
            'GET /api/execution/config',
            'GET /api/execution/status'
        ]
    }

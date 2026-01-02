"""
Order Execution Simulator

Realistic order execution with slippage, orderbook depth, and delays
"""

import random
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from enum import Enum


class OrderType(str, Enum):
    """Order types"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderSide(str, Enum):
    """Order sides"""
    BUY = "buy"
    SELL = "sell"


class ExecutionSimulator:
    """Simulate realistic order execution"""

    def __init__(
        self,
        slippage_model: str = "percentage",
        base_slippage_pct: float = 0.5,  # 0.5% realistic base slippage
        orderbook_depth: int = 10,
        min_delay_ms: int = 50,
        max_delay_ms: int = 200,
        volatility_multiplier: float = 1.0
    ):
        """
        Initialize execution simulator

        Args:
            slippage_model: 'percentage', 'fixed', or 'volume_based'
            base_slippage_pct: Base slippage percentage (0.05 = 0.05%)
            orderbook_depth: Simulated order book depth levels
            min_delay_ms: Minimum execution delay in milliseconds
            max_delay_ms: Maximum execution delay in milliseconds
            volatility_multiplier: Multiplier for slippage during high volatility
        """
        self.slippage_model = slippage_model
        self.base_slippage_pct = base_slippage_pct
        self.orderbook_depth = orderbook_depth
        self.min_delay_ms = min_delay_ms
        self.max_delay_ms = max_delay_ms
        self.volatility_multiplier = volatility_multiplier

        self.orderbook_cache: Dict[str, Dict] = {}

    def calculate_slippage(
        self,
        price: float,
        quantity: float,
        side: OrderSide,
        volatility: Optional[float] = None
    ) -> float:
        """
        Calculate slippage based on model

        Args:
            price: Order price
            quantity: Order quantity
            side: Buy or sell
            volatility: Current market volatility (optional)

        Returns:
            Slippage amount (can be negative)
        """
        if self.slippage_model == "percentage":
            # Simple percentage slippage
            slippage_pct = self.base_slippage_pct

            # Adjust for volatility
            if volatility:
                slippage_pct *= (1 + volatility * self.volatility_multiplier)

            # Random variation (±50%)
            slippage_pct *= random.uniform(0.5, 1.5)

            # Calculate slippage amount
            slippage = price * (slippage_pct / 100)

            # Negative slippage for buys (pay more), positive for sells (receive less)
            return -slippage if side == OrderSide.BUY else slippage

        elif self.slippage_model == "fixed":
            # Fixed dollar amount slippage
            base_slippage = self.base_slippage_pct  # Treat as fixed amount
            slippage = base_slippage * random.uniform(0.5, 1.5)
            return -slippage if side == OrderSide.BUY else slippage

        elif self.slippage_model == "volume_based":
            # Slippage increases with order size
            # Simulate impact based on quantity
            impact_factor = min(quantity / 1000, 1.0)  # Cap at 100% impact
            slippage_pct = self.base_slippage_pct * (1 + impact_factor * 2)

            if volatility:
                slippage_pct *= (1 + volatility * self.volatility_multiplier)

            slippage_pct *= random.uniform(0.5, 1.5)
            slippage = price * (slippage_pct / 100)
            return -slippage if side == OrderSide.BUY else slippage

        return 0

    def generate_orderbook(
        self,
        mid_price: float,
        spread_pct: float = 0.05,
        depth_factor: float = 1.0
    ) -> Dict[str, Any]:
        """
        Generate simulated order book

        Args:
            mid_price: Current mid price
            spread_pct: Bid-ask spread percentage
            depth_factor: Liquidity depth factor

        Returns:
            Order book with bids and asks
        """
        spread = mid_price * (spread_pct / 100)
        best_bid = mid_price - spread / 2
        best_ask = mid_price + spread / 2

        bids = []
        asks = []

        # Generate bid levels
        for i in range(self.orderbook_depth):
            level_price = best_bid - (i * spread * 0.5)
            level_size = random.uniform(0.1, 2.0) * depth_factor * (1 + i * 0.2)
            bids.append({
                'price': level_price,
                'size': level_size
            })

        # Generate ask levels
        for i in range(self.orderbook_depth):
            level_price = best_ask + (i * spread * 0.5)
            level_size = random.uniform(0.1, 2.0) * depth_factor * (1 + i * 0.2)
            asks.append({
                'price': level_price,
                'size': level_size
            })

        return {
            'bids': bids,
            'asks': asks,
            'spread': spread,
            'spread_pct': spread_pct,
            'mid_price': mid_price
        }

    def calculate_execution_delay(
        self,
        order_type: OrderType,
        market_congestion: float = 0.5
    ) -> float:
        """
        Calculate realistic execution delay

        Args:
            order_type: Type of order
            market_congestion: Market congestion factor (0-1)

        Returns:
            Delay in milliseconds
        """
        # Base delay
        base_delay = random.uniform(self.min_delay_ms, self.max_delay_ms)

        # Order type affects delay
        if order_type == OrderType.MARKET:
            type_multiplier = 1.0
        elif order_type == OrderType.LIMIT:
            type_multiplier = 1.5
        else:
            type_multiplier = 1.2

        # Market congestion affects delay
        congestion_multiplier = 1 + market_congestion

        return base_delay * type_multiplier * congestion_multiplier

    async def execute_order(
        self,
        symbol: str,
        order_type: OrderType,
        side: OrderSide,
        quantity: float,
        price: Optional[float] = None,
        current_price: Optional[float] = None,
        volatility: Optional[float] = None,
        market_congestion: float = 0.5
    ) -> Dict[str, Any]:
        """
        Simulate order execution with realistic conditions

        Args:
            symbol: Trading symbol
            order_type: Order type
            side: Buy or sell
            quantity: Order quantity
            price: Limit price (for limit orders)
            current_price: Current market price
            volatility: Market volatility factor
            market_congestion: Market congestion (0-1)

        Returns:
            Execution result dictionary
        """
        # Calculate execution delay
        delay_ms = self.calculate_execution_delay(order_type, market_congestion)
        await asyncio.sleep(delay_ms / 1000)  # Convert to seconds

        # Use current price if not provided
        if current_price is None:
            current_price = price if price else 0

        # For market orders, calculate slippage
        if order_type == OrderType.MARKET:
            slippage = self.calculate_slippage(
                current_price,
                quantity,
                side,
                volatility
            )
            execution_price = current_price + slippage
        else:
            # Limit orders execute at limit price (if filled)
            execution_price = price
            slippage = 0

        # Calculate total cost
        total_cost = execution_price * quantity

        # Simulate partial fills for large orders
        fill_percentage = 1.0
        if quantity > 100:  # Large order threshold
            fill_percentage = random.uniform(0.7, 1.0)

        filled_quantity = quantity * fill_percentage

        return {
            'success': True,
            'symbol': symbol,
            'order_type': order_type.value,
            'side': side.value,
            'requested_quantity': quantity,
            'filled_quantity': filled_quantity,
            'fill_percentage': fill_percentage * 100,
            'requested_price': price,
            'execution_price': execution_price,
            'slippage': slippage,
            'slippage_pct': (slippage / current_price * 100) if current_price > 0 else 0,
            'total_cost': total_cost,
            'delay_ms': delay_ms,
            'executed_at': datetime.now().isoformat()
        }

    def simulate_orderbook_impact(
        self,
        orderbook: Dict[str, Any],
        side: OrderSide,
        quantity: float
    ) -> Dict[str, Any]:
        """
        Simulate the impact of an order on the order book

        Args:
            orderbook: Current order book
            side: Buy or sell
            quantity: Order quantity

        Returns:
            Impact analysis
        """
        levels = orderbook['asks'] if side == OrderSide.BUY else orderbook['bids']

        remaining_quantity = quantity
        total_cost = 0
        levels_consumed = 0
        average_price = 0

        for level in levels:
            if remaining_quantity <= 0:
                break

            level_size = level['size']
            level_price = level['price']

            consumed = min(remaining_quantity, level_size)
            total_cost += consumed * level_price
            remaining_quantity -= consumed
            levels_consumed += 1

        if quantity > 0:
            average_price = total_cost / quantity

        return {
            'average_price': average_price,
            'levels_consumed': levels_consumed,
            'fully_filled': remaining_quantity == 0,
            'unfilled_quantity': remaining_quantity,
            'price_impact_pct': ((average_price - orderbook['mid_price']) / orderbook['mid_price'] * 100) if orderbook['mid_price'] > 0 else 0
        }


# Convenience functions

def simulate_market_order(
    price: float,
    quantity: float,
    side: str = "buy",
    slippage_pct: float = 0.05
) -> Dict[str, Any]:
    """
    Quick market order simulation

    Args:
        price: Current price
        quantity: Order size
        side: 'buy' or 'sell'
        slippage_pct: Slippage percentage

    Returns:
        Simulated execution result
    """
    simulator = ExecutionSimulator(base_slippage_pct=slippage_pct)

    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    result = loop.run_until_complete(
        simulator.execute_order(
            symbol="SIM",
            order_type=OrderType.MARKET,
            side=OrderSide(side.lower()),
            quantity=quantity,
            current_price=price
        )
    )

    return result


# Global simulator instance
default_simulator = ExecutionSimulator()

"""
Market Simulator with Realistic Trading Mechanics

Handles:
- Position management (entry/exit)
- Order execution with slippage
- Commission calculation
- Real P&L tracking
- Risk management (stop-loss, take-profit)

This provides a realistic trading environment for testing strategies.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List
from enum import Enum


class OrderSide(Enum):
    """Order side"""
    BUY = "BUY"
    SELL = "SELL"


class PositionSide(Enum):
    """Position direction"""
    LONG = "LONG"
    SHORT = "SHORT"


@dataclass
class Position:
    """Open trading position"""
    symbol: str
    side: PositionSide
    entry_price: float
    quantity: float
    entry_time: datetime
    strategy: str

    # P&L tracking
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0

    # Risk management
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None

    # Entry costs
    entry_commission: float = 0.0
    entry_slippage: float = 0.0

    # Position value
    @property
    def position_value(self) -> float:
        """Total position value"""
        return self.entry_price * self.quantity

    def calculate_pnl(self, current_price: float) -> float:
        """
        Calculate unrealized P&L.

        Args:
            current_price: Current market price

        Returns:
            Unrealized P&L in dollars
        """
        if self.side == PositionSide.LONG:
            # Long: profit when price goes up
            pnl = (current_price - self.entry_price) * self.quantity
        else:
            # Short: profit when price goes down
            pnl = (self.entry_price - current_price) * self.quantity

        # Subtract entry costs
        pnl -= (self.entry_commission + self.entry_slippage)

        self.unrealized_pnl = pnl
        return pnl

    def check_stop_loss(self, current_price: float) -> bool:
        """Check if stop-loss is hit"""
        if self.stop_loss is None:
            return False

        if self.side == PositionSide.LONG:
            return current_price <= self.stop_loss
        else:
            return current_price >= self.stop_loss

    def check_take_profit(self, current_price: float) -> bool:
        """Check if take-profit is hit"""
        if self.take_profit is None:
            return False

        if self.side == PositionSide.LONG:
            return current_price >= self.take_profit
        else:
            return current_price <= self.take_profit


@dataclass
class Trade:
    """Completed trade record"""
    timestamp: datetime
    symbol: str
    signal: str  # BUY or SELL
    strategy: str

    # Execution details
    entry_price: float
    exit_price: float
    quantity: float

    # Costs
    commission: float
    slippage: float

    # Results
    pnl: float
    pnl_percentage: float

    # Market data
    entry_bid: Optional[float] = None
    entry_ask: Optional[float] = None
    exit_bid: Optional[float] = None
    exit_ask: Optional[float] = None

    # Position details
    position_side: str = "LONG"
    hold_duration_seconds: float = 0.0


class MarketSimulator:
    """
    Realistic market simulator with proper trading mechanics.

    Features:
    - Commission (default 0.1% per trade)
    - Slippage (default 0.05%)
    - Bid-ask spread execution
    - Position tracking
    - Stop-loss / take-profit
    - Real P&L calculation

    Usage:
        simulator = MarketSimulator(initial_capital=10000)

        # Open position
        position = simulator.open_position(
            symbol="BTC",
            side=PositionSide.LONG,
            price=45000,
            bid=44995,
            ask=45005,
            strategy="rsi_strategy"
        )

        # Update P&L
        simulator.update_positions(current_price=45500)

        # Close position
        trade = simulator.close_position(
            symbol="BTC",
            price=45500,
            bid=45495,
            ask=45505
        )
    """

    def __init__(
        self,
        initial_capital: float = 10000.0,
        commission_rate: float = 0.001,     # 0.1%
        slippage_rate: float = 0.0005,      # 0.05%
        position_size_pct: float = 0.10,    # 10% of capital per trade
        use_stop_loss: bool = True,
        stop_loss_pct: float = 0.02,        # 2% stop-loss
        use_take_profit: bool = True,
        take_profit_pct: float = 0.05,      # 5% take-profit
    ):
        """
        Initialize market simulator.

        Args:
            initial_capital: Starting capital
            commission_rate: Commission as decimal (0.001 = 0.1%)
            slippage_rate: Slippage as decimal (0.0005 = 0.05%)
            position_size_pct: Position size as % of capital (0.10 = 10%)
            use_stop_loss: Enable stop-loss
            stop_loss_pct: Stop-loss distance as decimal (0.02 = 2%)
            use_take_profit: Enable take-profit
            take_profit_pct: Take-profit distance as decimal (0.05 = 5%)
        """
        # Capital tracking
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.available_capital = initial_capital

        # Trading parameters
        self.commission_rate = commission_rate
        self.slippage_rate = slippage_rate
        self.position_size_pct = position_size_pct

        # Risk management
        self.use_stop_loss = use_stop_loss
        self.stop_loss_pct = stop_loss_pct
        self.use_take_profit = use_take_profit
        self.take_profit_pct = take_profit_pct

        # Position tracking
        self.open_positions: Dict[str, Position] = {}
        self.closed_trades: List[Trade] = []

        # Statistics
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_commission_paid = 0.0
        self.total_slippage_paid = 0.0

    def _calculate_position_size(self, price: float) -> float:
        """
        Calculate position size (number of units to trade).

        Args:
            price: Current price

        Returns:
            Quantity to trade
        """
        position_value = self.available_capital * self.position_size_pct
        quantity = position_value / price
        return quantity

    def _calculate_commission(self, value: float) -> float:
        """Calculate commission for a trade"""
        return value * self.commission_rate

    def _calculate_slippage(self, value: float) -> float:
        """Calculate slippage cost"""
        return value * self.slippage_rate

    def _get_execution_price(
        self,
        side: OrderSide,
        mid_price: float,
        bid: Optional[float] = None,
        ask: Optional[float] = None
    ) -> float:
        """
        Get realistic execution price including spread and slippage.

        Args:
            side: BUY or SELL
            mid_price: Mid-market price
            bid: Bid price (if available)
            ask: Ask price (if available)

        Returns:
            Actual execution price
        """
        # Use bid/ask if provided, otherwise estimate spread
        if side == OrderSide.BUY:
            base_price = ask if ask else mid_price * 1.0005
        else:
            base_price = bid if bid else mid_price * 0.9995

        # Add slippage (always unfavorable)
        if side == OrderSide.BUY:
            execution_price = base_price * (1 + self.slippage_rate)
        else:
            execution_price = base_price * (1 - self.slippage_rate)

        return execution_price

    def can_open_position(self, symbol: str, price: float) -> bool:
        """
        Check if we can open a new position.

        Args:
            symbol: Trading symbol
            price: Current price

        Returns:
            True if position can be opened
        """
        # Check if position already open
        if symbol in self.open_positions:
            return False

        # Check if enough capital
        position_value = price * self._calculate_position_size(price)
        return self.available_capital >= position_value

    def open_position(
        self,
        symbol: str,
        side: PositionSide,
        price: float,
        strategy: str,
        bid: Optional[float] = None,
        ask: Optional[float] = None,
        timestamp: Optional[datetime] = None
    ) -> Optional[Position]:
        """
        Open a new position.

        Args:
            symbol: Trading symbol
            side: LONG or SHORT
            price: Current market price
            strategy: Strategy name
            bid: Current bid price
            ask: Current ask price
            timestamp: Trade timestamp

        Returns:
            Position object if successful, None if failed
        """
        if not self.can_open_position(symbol, price):
            return None

        # Calculate position size
        quantity = self._calculate_position_size(price)

        # Get execution price (use ask for long, bid for short)
        order_side = OrderSide.BUY if side == PositionSide.LONG else OrderSide.SELL
        execution_price = self._get_execution_price(order_side, price, bid, ask)

        # Calculate costs
        position_value = execution_price * quantity
        commission = self._calculate_commission(position_value)
        slippage = abs(execution_price - price) * quantity

        # Update capital
        self.available_capital -= (position_value + commission)
        self.total_commission_paid += commission
        self.total_slippage_paid += slippage

        # Calculate stop-loss and take-profit
        stop_loss = None
        take_profit = None

        if self.use_stop_loss:
            if side == PositionSide.LONG:
                stop_loss = execution_price * (1 - self.stop_loss_pct)
            else:
                stop_loss = execution_price * (1 + self.stop_loss_pct)

        if self.use_take_profit:
            if side == PositionSide.LONG:
                take_profit = execution_price * (1 + self.take_profit_pct)
            else:
                take_profit = execution_price * (1 - self.take_profit_pct)

        # Create position
        position = Position(
            symbol=symbol,
            side=side,
            entry_price=execution_price,
            quantity=quantity,
            entry_time=timestamp or datetime.now(),
            strategy=strategy,
            stop_loss=stop_loss,
            take_profit=take_profit,
            entry_commission=commission,
            entry_slippage=slippage
        )

        self.open_positions[symbol] = position
        return position

    def close_position(
        self,
        symbol: str,
        price: float,
        bid: Optional[float] = None,
        ask: Optional[float] = None,
        timestamp: Optional[datetime] = None,
        reason: str = "signal"
    ) -> Optional[Trade]:
        """
        Close an open position.

        Args:
            symbol: Trading symbol
            price: Current market price
            bid: Current bid price
            ask: Current ask price
            timestamp: Trade timestamp
            reason: Closure reason (signal/stop_loss/take_profit)

        Returns:
            Trade object if successful, None if no position open
        """
        if symbol not in self.open_positions:
            return None

        position = self.open_positions[symbol]

        # Get execution price (opposite side of entry)
        if position.side == PositionSide.LONG:
            order_side = OrderSide.SELL
        else:
            order_side = OrderSide.BUY

        execution_price = self._get_execution_price(order_side, price, bid, ask)

        # Calculate exit costs
        position_value = execution_price * position.quantity
        exit_commission = self._calculate_commission(position_value)
        exit_slippage = abs(execution_price - price) * position.quantity

        self.total_commission_paid += exit_commission
        self.total_slippage_paid += exit_slippage

        # Calculate P&L
        if position.side == PositionSide.LONG:
            gross_pnl = (execution_price - position.entry_price) * position.quantity
        else:
            gross_pnl = (position.entry_price - execution_price) * position.quantity

        # Subtract all costs
        net_pnl = gross_pnl - (
            position.entry_commission +
            position.entry_slippage +
            exit_commission +
            exit_slippage
        )

        # P&L percentage
        pnl_pct = (net_pnl / position.position_value) * 100

        # Update capital
        self.available_capital += position_value
        self.current_capital += net_pnl

        # Update statistics
        self.total_trades += 1
        if net_pnl > 0:
            self.winning_trades += 1
        else:
            self.losing_trades += 1

        # Calculate hold duration
        exit_time = timestamp or datetime.now()
        hold_duration = (exit_time - position.entry_time).total_seconds()

        # Create trade record
        trade = Trade(
            timestamp=exit_time,
            symbol=symbol,
            signal="SELL" if position.side == PositionSide.LONG else "BUY",
            strategy=position.strategy,
            entry_price=position.entry_price,
            exit_price=execution_price,
            quantity=position.quantity,
            commission=position.entry_commission + exit_commission,
            slippage=position.entry_slippage + exit_slippage,
            pnl=net_pnl,
            pnl_percentage=pnl_pct,
            entry_bid=bid,
            entry_ask=ask,
            exit_bid=bid,
            exit_ask=ask,
            position_side=position.side.value,
            hold_duration_seconds=hold_duration
        )

        # Remove position and add to trade history
        del self.open_positions[symbol]
        self.closed_trades.append(trade)

        return trade

    def update_positions(
        self,
        prices: Dict[str, float],
        bids: Optional[Dict[str, float]] = None,
        asks: Optional[Dict[str, float]] = None,
        timestamp: Optional[datetime] = None
    ) -> List[Trade]:
        """
        Update all open positions and check for stop-loss/take-profit.

        Args:
            prices: Dict of {symbol: current_price}
            bids: Dict of {symbol: bid_price}
            asks: Dict of {symbol: ask_price}
            timestamp: Current timestamp

        Returns:
            List of trades closed due to stop-loss/take-profit
        """
        closed_trades = []
        symbols_to_close = []

        for symbol, position in self.open_positions.items():
            if symbol not in prices:
                continue

            current_price = prices[symbol]
            bid = bids.get(symbol) if bids else None
            ask = asks.get(symbol) if asks else None

            # Update unrealized P&L
            position.calculate_pnl(current_price)

            # Check stop-loss
            if position.check_stop_loss(current_price):
                symbols_to_close.append((symbol, "stop_loss"))

            # Check take-profit
            elif position.check_take_profit(current_price):
                symbols_to_close.append((symbol, "take_profit"))

        # Close positions that hit stop-loss/take-profit
        for symbol, reason in symbols_to_close:
            trade = self.close_position(
                symbol=symbol,
                price=prices[symbol],
                bid=bids.get(symbol) if bids else None,
                ask=asks.get(symbol) if asks else None,
                timestamp=timestamp,
                reason=reason
            )
            if trade:
                closed_trades.append(trade)

        return closed_trades

    def get_statistics(self) -> Dict:
        """Get trading statistics"""
        win_rate = (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0

        total_pnl = self.current_capital - self.initial_capital
        total_return_pct = (total_pnl / self.initial_capital) * 100

        return {
            "initial_capital": self.initial_capital,
            "current_capital": round(self.current_capital, 2),
            "available_capital": round(self.available_capital, 2),
            "total_pnl": round(total_pnl, 2),
            "total_return_pct": round(total_return_pct, 2),
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": round(win_rate, 2),
            "open_positions": len(self.open_positions),
            "total_commission_paid": round(self.total_commission_paid, 2),
            "total_slippage_paid": round(self.total_slippage_paid, 2),
        }

    def reset(self):
        """Reset simulator to initial state"""
        self.current_capital = self.initial_capital
        self.available_capital = self.initial_capital
        self.open_positions.clear()
        self.closed_trades.clear()
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_commission_paid = 0.0
        self.total_slippage_paid = 0.0

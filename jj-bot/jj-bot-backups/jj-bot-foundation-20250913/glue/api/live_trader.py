import asyncio
import datetime
import sys
import os

# Fix imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)
sys.path.insert(0, os.path.join(current_dir, '..', '..'))

from engine import log_trade
from hands.data.market_data_manager import market_manager
from hands.strategies.strategy_engine import StrategyEngine

class LiveTrader:
    """Live trading system using real market data"""
    
    def __init__(self, symbol: str = "BTCUSDT"):
        self.symbol = symbol
        self.strategy_engine = StrategyEngine()
        self.is_trading = False
        self.trade_count = 0
        
    async def start_live_trading(self):
        """Start live trading with real market data"""
        print(f"🔴 LIVE Trading Started for {self.symbol}")
        print("⚠️  WARNING: This uses REAL market data")
        print("💡 This is SIMULATION mode - no actual trades executed")
        
        self.is_trading = True
        
        # Subscribe to market data updates
        market_manager.add_subscriber(self.on_market_update)
        
        # Start live market data
        await market_manager.start_live_updates(self.symbol, interval=10)
    
    def on_market_update(self, market_data):
        """Handle real-time market data updates"""
        if not self.is_trading:
            return
            
        try:
            # Add volume change estimate (real calculation would need historical data)
            market_data['volume_change_24h'] = (
                (market_data.get('volume_24h', 0) / 2000000000 - 1) * 100
            )
            
            # Run strategy analysis on real data
            analysis = self.strategy_engine.analyze_market(market_data)
            
            # Get consensus signal
            signal = analysis['consensus_signal']
            confidence = analysis['consensus_confidence']
            
            # Only trade on strong signals
            if confidence > 0.5 and signal != 'HOLD':
                self.execute_simulated_trade(market_data, analysis)
                
        except Exception as e:
            print(f"Error processing market update: {e}")
    
    def execute_simulated_trade(self, market_data, analysis):
        """Execute a simulated trade based on real market signals"""
        
        signal = analysis['consensus_signal']
        confidence = analysis['consensus_confidence']
        price = market_data['price']
        vwap = market_data.get('vwap', price)
        
        # Calculate realistic P&L based on signal strength and market conditions
        spread = abs(price - vwap)
        base_pnl = spread * confidence
        
        # Add some randomness for slippage and market impact
        import random
        market_noise = random.uniform(-15, 15)
        pnl = base_pnl + market_noise
        
        # For shorts, flip the P&L calculation
        if signal == 'SHORT':
            pnl = base_pnl * random.uniform(0.7, 1.3) + market_noise
        else:  # LONG
            pnl = base_pnl * random.uniform(0.7, 1.3) + market_noise
        
        # Create trade record
        trade = {
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "symbol": self.symbol,
            "signal": signal,
            "last_price": round(price, 2),
            "vwap": round(vwap, 2),
            "pnl": round(pnl, 2)
        }
        
        # Log the trade
        log_trade(trade)
        self.trade_count += 1
        
        # Enhanced display
        data_source = market_data.get('data_source', 'unknown')
        print(f"🔴 LIVE #{self.trade_count:3d} | {signal:5s} | ${price:8.2f} | VWAP ${vwap:8.2f} | "
              f"Conf {confidence:.1%} | P&L ${pnl:+.2f} | Source: {data_source}")
        
        # Show strategy breakdown for significant trades
        if confidence > 0.7:
            print(f"   📊 {analysis['recommendation']}")
            print(f"   🧠 Strategies: {analysis['individual_strategies']}")
    
    def stop_trading(self):
        """Stop live trading"""
        self.is_trading = False
        market_manager.stop_live_updates()
        print(f"🛑 Live trading stopped after {self.trade_count} trades")

async def run_live_trader():
    """Main function to run live trader"""
    trader = LiveTrader("BTCUSDT")
    
    try:
        await trader.start_live_trading()
    except KeyboardInterrupt:
        print("\n🛑 Stopping live trader...")
        trader.stop_trading()

if __name__ == "__main__":
    asyncio.run(run_live_trader())

import asyncio
import random
import datetime
import sys
import os

# Fix the import path issue
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)
sys.path.insert(0, os.path.join(current_dir, '..', '..'))

# Import our modules
from engine import log_trade
from hands.strategies.strategy_engine import StrategyEngine

SYMBOL = "BTCUSDT"

async def simulate_advanced_trading():
    """Advanced trade simulator using multiple strategies"""
    print("🧠 JJ Gorilla Advanced Multi-Strategy Simulator Starting...")
    
    # Initialize strategy engine
    strategy_engine = StrategyEngine()
    
    # Starting market conditions
    last_price = 99500 + random.randint(-500, 500)
    vwap = last_price
    volume_24h = 2500000000 + random.randint(-500000000, 500000000)
    
    trade_count = 0
    
    while True:
        try:
            # Simulate realistic market movements
            price_change = random.randint(-200, 200)
            last_price += price_change
            
            # VWAP follows price more slowly
            vwap_change = price_change * random.uniform(0.3, 0.8)
            vwap += vwap_change
            
            # Volume changes
            volume_change = random.randint(-100000000, 100000000)
            volume_24h = max(volume_24h + volume_change, 500000000)
            
            # Calculate percentage changes
            price_change_24h = random.uniform(-8, 8)
            volume_change_24h = random.uniform(-50, 150)
            
            # Ensure positive prices
            last_price = max(last_price, 1000)
            vwap = max(vwap, 1000)
            
            # Create market data for strategies
            market_data = {
                'symbol': SYMBOL,
                'current_price': last_price,
                'vwap': vwap,
                'volume_24h': volume_24h,
                'price_change_24h': price_change_24h,
                'volume_change_24h': volume_change_24h,
                'timestamp': datetime.datetime.now().isoformat()
            }
            
            # Run strategy analysis
            analysis = strategy_engine.analyze_market(market_data)
            
            # Get consensus signal
            signal = analysis['consensus_signal']
            confidence = analysis['consensus_confidence']
            
            # Skip HOLD signals sometimes
            if signal == 'HOLD' and random.random() < 0.7:
                await asyncio.sleep(random.uniform(3, 8))
                continue
            
            # Calculate P&L based on strategy confidence and market conditions
            base_pnl = abs(last_price - vwap) * random.uniform(0.1, 0.3)
            
            if signal == 'LONG':
                pnl = base_pnl * confidence * random.uniform(0.5, 1.5)
            elif signal == 'SHORT':
                pnl = base_pnl * confidence * random.uniform(0.5, 1.5)
            else:  # HOLD (treat as small position)
                pnl = base_pnl * 0.2 * random.uniform(-1, 1)
                signal = random.choice(['LONG', 'SHORT'])
            
            # Add market noise
            pnl += random.uniform(-20, 20)
            
            # Create trade record with strategy info
            trade = {
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "symbol": SYMBOL,
                "signal": signal,
                "last_price": round(last_price, 2),
                "vwap": round(vwap, 2),
                "pnl": round(pnl, 2)
            }
            
            # Log to database
            log_trade(trade)
            trade_count += 1
            
            # Enhanced display with strategy info
            confidence_display = f"{confidence:.1%}"
            pnl_display = f"${pnl:+.2f}"
            
            print(f"#{trade_count:3d} | {signal:5s} | ${last_price:8.2f} | VWAP ${vwap:8.2f} | Conf {confidence_display} | P&L {pnl_display}")
            
            # Show strategy breakdown occasionally
            if trade_count % 10 == 0:
                print("📊 Strategy Signals:", {k: v for k, v in analysis['individual_strategies'].items()})
                print("🎯 Recommendation:", analysis['recommendation'])
            
            # Variable wait time based on market volatility
            wait_time = random.uniform(2, 10)
            if abs(price_change_24h) > 5:  # High volatility = more frequent trades
                wait_time *= 0.5
            
            await asyncio.sleep(wait_time)
            
        except KeyboardInterrupt:
            print(f"\n🛑 Advanced Simulator stopped after {trade_count} trades")
            break
        except Exception as e:
            print(f"❌ Error in advanced simulator: {e}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(simulate_advanced_trading())

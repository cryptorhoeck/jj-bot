import asyncio
import random
import datetime
import sys
import os

# Fix the import path issue
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Now import directly from engine
from engine import log_trade

SYMBOL = "BTCUSDT"

async def simulate_trades():
    """Simulate trading with realistic price movements and PnL calculation"""
    print("🚀 JJ-Bot Trade Simulator Starting...")
    
    # Starting price around current BTC level
    last_price = 99500 + random.randint(-500, 500)
    vwap = last_price  # Start VWAP at current price
    
    trade_count = 0
    
    while True:
        try:
            # More realistic price movement (smaller steps)
            price_change = random.randint(-150, 150)
            last_price += price_change
            
            # VWAP moves more slowly than price
            vwap_change = price_change * random.uniform(0.3, 0.7)
            vwap += vwap_change
            
            # Ensure prices stay positive
            last_price = max(last_price, 1000)
            vwap = max(vwap, 1000)
            
            # Simple VWAP-based signal generation
            price_vwap_ratio = last_price / vwap
            
            if price_vwap_ratio > 1.002:  # Price 0.2% above VWAP
                signal = "LONG"
                # For LONG: profit when price goes up relative to VWAP
                pnl = (last_price - vwap) * random.uniform(0.05, 0.15)
            elif price_vwap_ratio < 0.998:  # Price 0.2% below VWAP 
                signal = "SHORT"
                # For SHORT: profit when price goes down relative to VWAP
                pnl = (vwap - last_price) * random.uniform(0.05, 0.15)
            else:
                # Sometimes generate neutral/no trade
                if random.random() < 0.3:
                    await asyncio.sleep(3)
                    continue
                signal = random.choice(["LONG", "SHORT"])
                # Smaller PnL for less obvious setups
                if signal == "LONG":
                    pnl = (last_price - vwap) * random.uniform(-0.1, 0.1)
                else:
                    pnl = (vwap - last_price) * random.uniform(-0.1, 0.1)
            
            # Add some noise to PnL to simulate market impact, slippage etc.
            pnl += random.uniform(-15, 15)
            
            # Create trade record
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
            
            # Print trade info
            pnl_display = f"${pnl:+.2f}" if pnl != 0 else "$0.00"
            print(f"#{trade_count:3d} | {signal:5s} | ${last_price:8.2f} | VWAP ${vwap:8.2f} | P&L {pnl_display}")
            
            # Wait between trades (2-8 seconds)
            await asyncio.sleep(random.uniform(2, 8))
            
        except KeyboardInterrupt:
            print(f"\n🛑 Simulator stopped after {trade_count} trades")
            break
        except Exception as e:
            print(f"❌ Error in simulator: {e}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(simulate_trades())

import asyncio
import random
from datetime import datetime
from typing import List, Dict, Any

class TradingSimulator:
    def __init__(self):
        self.running = False
        self.trades = []
        self.positions = {}
        self.balance = 100000
        self.symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT"]
        
    async def start(self):
        """Start generating simulated trades"""
        self.running = True
        asyncio.create_task(self.trade_loop())
        return {"status": "started", "message": "Trading simulator started!"}
    
    async def stop(self):
        """Stop the simulator"""
        self.running = False
        return {"status": "stopped", "message": "Trading simulator stopped"}
    
    async def trade_loop(self):
        """Generate trades every few seconds"""
        while self.running:
            await asyncio.sleep(random.uniform(2, 8))  # Trade every 2-8 seconds
            
            symbol = random.choice(self.symbols)
            side = random.choice(["BUY", "SELL"])
            price = self.get_price(symbol)
            quantity = round(random.uniform(0.01, 1), 4)
            
            # Calculate PnL for sells
            pnl = 0
            if side == "SELL" and symbol in self.positions:
                avg_price = self.positions[symbol]["avg_price"]
                pnl = (price - avg_price) * quantity
            
            trade = {
                "id": f"trade_{len(self.trades) + 1}",
                "timestamp": datetime.now().isoformat(),
                "symbol": symbol,
                "side": side,
                "price": price,
                "quantity": quantity,
                "value": price * quantity,
                "pnl": round(pnl, 2),
                "status": "FILLED"
            }
            
            self.trades.append(trade)
            
            # Update positions
            if side == "BUY":
                if symbol not in self.positions:
                    self.positions[symbol] = {"quantity": 0, "avg_price": 0}
                pos = self.positions[symbol]
                total_value = (pos["quantity"] * pos["avg_price"]) + (quantity * price)
                pos["quantity"] += quantity
                pos["avg_price"] = total_value / pos["quantity"] if pos["quantity"] > 0 else 0
            else:  # SELL
                if symbol in self.positions:
                    self.positions[symbol]["quantity"] -= quantity
                    if self.positions[symbol]["quantity"] <= 0:
                        del self.positions[symbol]
            
            # Keep only last 100 trades
            if len(self.trades) > 100:
                self.trades = self.trades[-100:]
    
    def get_price(self, symbol):
        """Get simulated price for symbol"""
        base_prices = {
            "BTCUSDT": 45000,
            "ETHUSDT": 2500,
            "BNBUSDT": 350,
            "SOLUSDT": 100,
            "ADAUSDT": 0.5
        }
        base = base_prices.get(symbol, 100)
        return round(base * random.uniform(0.95, 1.05), 2)
    
    def get_recent_trades(self, limit=50):
        """Get recent trades"""
        return self.trades[-limit:] if self.trades else []
    
    def get_status(self):
        """Get simulator status"""
        total_pnl = sum(t.get("pnl", 0) for t in self.trades)
        return {
            "running": self.running,
            "balance": self.balance + total_pnl,
            "total_trades": len(self.trades),
            "open_positions": len(self.positions),
            "total_pnl": round(total_pnl, 2),
            "positions": self.positions
        }

# Global simulator instance
simulator = TradingSimulator()

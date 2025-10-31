import time
"""
Simulator Service - Wraps the existing simulator
"""

import sys
import os
import json
import subprocess
import requests
from datetime import datetime

# Add paths
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'glue'))

from services.base.service import BaseService

class SimulatorService(BaseService):
    """Service wrapper for trade simulator"""
    
    def __init__(self):
        super().__init__(name="simulator", auto_start=False)
        self.api_base = "http://127.0.0.1:8000"
        
    def _run(self):
        """Start the simulator via API"""
        try:
            # Call the existing simulator start endpoint
            response = requests.post(f"{self.api_base}/api/simulator/start")
            if response.status_code == 200:
                self.stats["start_response"] = response.json()
                
                # Keep checking status
                while self.status == "running":
                    time.sleep(5)
                    try:
                        status_resp = requests.get(f"{self.api_base}/api/simulator/status")
                        if status_resp.status_code == 200:
                            self.stats.update(status_resp.json())
                    except:
                        pass
            else:
                self.status = "error"
                
        except Exception as e:
            self.status = "error"
            self.stats["error"] = str(e)
    
    def _cleanup(self):
        """Stop the simulator"""
        try:
            requests.post(f"{self.api_base}/api/simulator/stop")
        except:
            pass

    def generate_trades(self, num_trades: int = 50):
        """Generate test trades directly"""
        try:
            import sqlite3
            import random
            from datetime import datetime, timedelta

            # Connect to database
            db_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'trades.db')
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Symbols to trade
            symbols = ['BTC', 'ETH', 'SOL', 'BNB', 'ADA', 'DOT', 'LINK', 'MATIC', 'UNI', 'AVAX']

            # Base prices
            base_prices = {
                'BTC': 45000, 'ETH': 2500, 'SOL': 100, 'BNB': 350, 'ADA': 0.50,
                'DOT': 7, 'LINK': 15, 'MATIC': 0.80, 'UNI': 6, 'AVAX': 35
            }

            # Generate trades
            trades_inserted = 0
            current_time = datetime.now()

            for i in range(num_trades):
                # Random symbol
                symbol = random.choice(symbols)
                base_price = base_prices[symbol]

                # Random price variation (±5%)
                price = base_price * (1 + random.uniform(-0.05, 0.05))

                # Random side
                side = random.choice(['buy', 'sell'])

                # Random size
                size = random.uniform(0.01, 0.5)

                # Random P&L (-50 to +100)
                pnl = random.uniform(-50, 100)

                # Timestamp (spread over last 24 hours)
                timestamp = current_time - timedelta(hours=random.randint(0, 24), minutes=random.randint(0, 59))

                # Insert trade
                cursor.execute("""
                    INSERT INTO trades (timestamp, symbol, side, price, size, pnl)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (timestamp.isoformat(), symbol, side, price, size, pnl))

                trades_inserted += 1

            conn.commit()
            conn.close()

            self.stats["last_generation"] = {
                "trades": trades_inserted,
                "timestamp": datetime.now().isoformat()
            }

            return {"success": True, "trades_generated": trades_inserted}

        except Exception as e:
            self.stats["error"] = str(e)
            raise Exception(f"Failed to generate trades: {str(e)}")

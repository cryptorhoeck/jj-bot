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
            # Import the simulator and generate trades
            from glue import simulator

            result = simulator.generate_trades(num_trades)

            self.stats["last_generation"] = {
                "trades": num_trades,
                "timestamp": datetime.now().isoformat(),
                "result": result
            }

            return result

        except Exception as e:
            self.stats["error"] = str(e)
            raise Exception(f"Failed to generate trades: {str(e)}")

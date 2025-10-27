"""
Enhanced Strategy with Multiple Timeframes and Better Signals
"""

import sys
import os
from datetime import datetime
from typing import Dict, List, Optional
import numpy as np

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from modules.strategy.strategy_engine import StrategyEngine

class EnhancedStrategy(StrategyEngine):
    """Enhanced strategy with better signal generation"""
    
    def __init__(self):
        super().__init__()
        
        # Enhanced parameters
        self.min_volume = 1000000  # Minimum 24h volume for trading
        self.min_data_points = 30  # Need more history
        self.signal_cooldown = {}  # Prevent signal spam
        self.cooldown_period = 300  # 5 minutes between signals
        
    def generate_signal(self, indicators: Dict) -> Optional[Dict]:
        """Enhanced signal generation with volume and volatility checks"""
        
        symbol = indicators["symbol"]
        price = indicators["current_price"]
        
        # Check cooldown
        if symbol in self.signal_cooldown:
            if (datetime.now() - self.signal_cooldown[symbol]).seconds < self.cooldown_period:
                return None
        
        # Get base signal
        signal = super().generate_signal(indicators)
        
        if signal and signal["action"] != "HOLD":
            # Add volume confirmation
            if symbol in self.price_history:
                recent = self.price_history[symbol][-1]
                volume = recent.get("volume", 0)
                
                if volume < self.min_volume:
                    signal["strength"] *= 0.5
                    signal["reason"].append("Low volume warning")
            
            # Add volatility check
            if indicators.get("bollinger"):
                bb = indicators["bollinger"]
                volatility = (bb["upper"] - bb["lower"]) / bb["middle"]
                
                if volatility < 0.01:  # Less than 1% band width
                    signal["strength"] *= 0.7
                    signal["reason"].append("Low volatility")
                elif volatility > 0.10:  # More than 10% band width
                    signal["strength"] *= 1.2
                    signal["reason"].append("High volatility opportunity")
            
            # Set cooldown
            self.signal_cooldown[symbol] = datetime.now()
            
            # Add confidence score
            signal["confidence"] = self.calculate_confidence(indicators)
            
        return signal
    
    def calculate_confidence(self, indicators: Dict) -> float:
        """Calculate overall confidence in the signal"""
        confidence = 0.5  # Base confidence
        
        # RSI alignment
        rsi = indicators.get("rsi")
        if rsi:
            if rsi < 30 or rsi > 70:
                confidence += 0.1
            if rsi < 20 or rsi > 80:
                confidence += 0.1
        
        # Moving average alignment
        if indicators.get("sma_fast") and indicators.get("sma_slow"):
            if indicators["sma_fast"] > indicators["sma_slow"]:
                confidence += 0.1
        
        # MACD confirmation
        if indicators.get("macd"):
            if indicators["macd"].get("histogram", 0) > 0:
                confidence += 0.1
        
        return min(confidence, 1.0)

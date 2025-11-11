"""
Strategy Engine Module for JJ-Bot
Analyzes market data and generates trading signals
"""

import sys
import os
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from modules.base import BaseModule
from modules.event_bus import event_bus

class StrategyEngine(BaseModule):
    """Trading strategy engine that analyzes prices and generates signals"""
    
    def __init__(self):
        super().__init__("StrategyEngine")
        
        # Price history for analysis
        self.price_history = {}
        self.max_history = 100
        
        # Indicators
        self.indicators = {}
        
        # Signals
        self.current_signals = {}
        self.signal_history = []
        
        # Strategy parameters
        self.rsi_oversold = 30
        self.rsi_overbought = 70
        self.sma_fast = 10
        self.sma_slow = 20
        
        # Subscribe to price updates
        event_bus.subscribe("PRICE_UPDATE", self.on_price_update)
        
    def start(self) -> bool:
        """Start the strategy engine"""
        try:
            self.status = "RUNNING"
            self.start_time = datetime.now().isoformat()
            self.logger.info("Strategy engine started")
            
            # Start analysis thread
            self.analysis_thread = threading.Thread(target=self._run_analysis)
            self.analysis_thread.daemon = True
            self.analysis_thread.start()
            
            return True
            
        except Exception as e:
            self.log_error(f"Failed to start: {e}")
            return False
    
    def stop(self) -> bool:
        """Stop the strategy engine"""
        try:
            self.status = "STOPPED"
            self.logger.info("Strategy engine stopped")
            return True
            
        except Exception as e:
            self.log_error(f"Failed to stop: {e}")
            return False
    
    def health_check(self) -> Dict[str, Any]:
        """Check module health"""
        return {
            "healthy": self.status == "RUNNING",
            "status": self.status,
            "symbols_tracked": len(self.price_history),
            "signals_generated": len(self.signal_history),
            "last_analysis": self.indicators.get("last_update")
        }
    
    def on_price_update(self, event: Dict):
        """Handle incoming price updates"""
        data = event["data"]
        symbol = data["symbol"]
        price = data["price"]
        timestamp = data["timestamp"]
        
        # Add to price history
        if symbol not in self.price_history:
            self.price_history[symbol] = []
        
        self.price_history[symbol].append({
            "price": price,
            "timestamp": timestamp,
            "volume": data.get("volume_24h", 0)
        })
        
        # Keep only recent history
        if len(self.price_history[symbol]) > self.max_history:
            self.price_history[symbol].pop(0)
        
        # Analyze if we have enough data
        if len(self.price_history[symbol]) >= self.sma_slow:
            self.analyze_symbol(symbol)
    
    def calculate_rsi(self, prices: List[float], period: int = 14) -> Optional[float]:
        """Calculate Relative Strength Index"""
        if len(prices) < period + 1:
            return None
        
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def calculate_sma(self, prices: List[float], period: int) -> Optional[float]:
        """Calculate Simple Moving Average"""
        if len(prices) < period:
            return None
        return np.mean(prices[-period:])
    
    def calculate_macd(self, prices: List[float]) -> Optional[Dict]:
        """Calculate MACD"""
        if len(prices) < 26:
            return None
        
        # Calculate EMAs
        ema_12 = self.calculate_ema(prices, 12)
        ema_26 = self.calculate_ema(prices, 26)
        
        if ema_12 is None or ema_26 is None:
            return None
        
        macd_line = ema_12 - ema_26
        
        return {
            "macd": macd_line,
            "signal": self.calculate_sma(prices[-9:], 9) if len(prices) >= 9 else None,
            "histogram": macd_line - (self.calculate_sma(prices[-9:], 9) or 0)
        }
    
    def calculate_ema(self, prices: List[float], period: int) -> Optional[float]:
        """Calculate Exponential Moving Average"""
        if len(prices) < period:
            return None
        
        multiplier = 2 / (period + 1)
        ema = prices[-period]  # Start with SMA
        
        for price in prices[-period+1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        
        return ema
    
    def calculate_bollinger_bands(self, prices: List[float], period: int = 20) -> Optional[Dict]:
        """Calculate Bollinger Bands"""
        if len(prices) < period:
            return None
        
        sma = self.calculate_sma(prices, period)
        std = np.std(prices[-period:])
        
        return {
            "middle": sma,
            "upper": sma + (2 * std),
            "lower": sma - (2 * std)
        }
    
    def analyze_symbol(self, symbol: str):
        """Analyze a symbol and generate signals"""
        history = self.price_history[symbol]
        prices = [h["price"] for h in history]
        
        # Calculate all indicators
        indicators = {
            "symbol": symbol,
            "current_price": prices[-1],
            "rsi": self.calculate_rsi(prices),
            "sma_fast": self.calculate_sma(prices, self.sma_fast),
            "sma_slow": self.calculate_sma(prices, self.sma_slow),
            "macd": self.calculate_macd(prices),
            "bollinger": self.calculate_bollinger_bands(prices),
            "timestamp": datetime.now().isoformat()
        }
        
        # Store indicators
        if symbol not in self.indicators:
            self.indicators[symbol] = {}
        self.indicators[symbol] = indicators
        self.indicators["last_update"] = datetime.now().isoformat()
        
        # Generate signals
        signal = self.generate_signal(indicators)
        if signal:
            self.current_signals[symbol] = signal
            self.signal_history.append(signal)
            
            # Publish signal event
            event_bus.publish("TRADING_SIGNAL", signal)
            
            # Log strong signals
            if signal["strength"] >= 0.7:
                print(f"🎯 SIGNAL: {signal['action']} {symbol} | Reason: {signal['reason']} | Strength: {signal['strength']:.1%}")
    
    def generate_signal(self, indicators: Dict) -> Optional[Dict]:
        """Generate trading signal based on indicators"""
        symbol = indicators["symbol"]
        price = indicators["current_price"]
        rsi = indicators["rsi"]
        sma_fast = indicators["sma_fast"]
        sma_slow = indicators["sma_slow"]
        bollinger = indicators["bollinger"]
        
        signal = {
            "symbol": symbol,
            "price": price,
            "timestamp": datetime.now().isoformat(),
            "action": None,
            "reason": [],
            "strength": 0,
            "indicators": indicators
        }
        
        buy_score = 0
        sell_score = 0
        
        # RSI signals
        if rsi:
            if rsi < self.rsi_oversold:
                buy_score += 0.3
                signal["reason"].append(f"RSI oversold ({rsi:.1f})")
            elif rsi > self.rsi_overbought:
                sell_score += 0.3
                signal["reason"].append(f"RSI overbought ({rsi:.1f})")
        
        # Moving average crossover
        if sma_fast and sma_slow:
            if sma_fast > sma_slow:
                buy_score += 0.3
                signal["reason"].append("Golden cross (fast SMA > slow SMA)")
            elif sma_fast < sma_slow:
                sell_score += 0.3
                signal["reason"].append("Death cross (fast SMA < slow SMA)")
        
        # Bollinger bands
        if bollinger:
            if price < bollinger["lower"]:
                buy_score += 0.2
                signal["reason"].append("Price below lower Bollinger band")
            elif price > bollinger["upper"]:
                sell_score += 0.2
                signal["reason"].append("Price above upper Bollinger band")
        
        # MACD
        if indicators["macd"] and indicators["macd"]["signal"]:
            macd = indicators["macd"]["macd"]
            signal_line = indicators["macd"]["signal"]
            if macd > signal_line:
                buy_score += 0.2
                signal["reason"].append("MACD bullish")
            else:
                sell_score += 0.2
                signal["reason"].append("MACD bearish")
        
        # Determine action
        if buy_score > sell_score and buy_score >= 0.5:
            signal["action"] = "BUY"
            signal["strength"] = buy_score
        elif sell_score > buy_score and sell_score >= 0.5:
            signal["action"] = "SELL"
            signal["strength"] = sell_score
        else:
            signal["action"] = "HOLD"
            signal["strength"] = max(buy_score, sell_score)
        
        # Only return actionable signals
        if signal["action"] != "HOLD":
            return signal
        
        return None
    
    def _run_analysis(self):
        """Background analysis thread"""
        while self.status == "RUNNING":
            try:
                # Periodic analysis of all symbols
                for symbol in list(self.price_history.keys()):
                    if len(self.price_history[symbol]) >= self.sma_slow:
                        self.analyze_symbol(symbol)
                
                time.sleep(5)  # Analyze every 5 seconds
                
            except Exception as e:
                self.log_error(f"Analysis error: {e}")
                time.sleep(1)
    
    def get_current_signals(self) -> Dict:
        """Get current signals for all symbols"""
        return self.current_signals.copy()
    
    def get_signal_history(self, limit: int = 10) -> List[Dict]:
        """Get recent signal history"""
        return self.signal_history[-limit:]

    def calculate_indicators(self, prices: List[float]) -> Dict[str, Any]:
        """
        Calculate all technical indicators for a price array.
        Used by realistic simulator.

        Args:
            prices: List of historical prices

        Returns:
            Dictionary of calculated indicators
        """
        if len(prices) < 2:
            return {}

        indicators = {
            "rsi": self.calculate_rsi(prices),
            "sma_short": self.calculate_sma(prices, self.sma_fast),
            "sma_long": self.calculate_sma(prices, self.sma_slow),
            "macd": None,
            "macd_signal": None,
            "bollinger_upper": None,
            "bollinger_middle": None,
            "bollinger_lower": None
        }

        # MACD
        macd_result = self.calculate_macd(prices)
        if macd_result:
            indicators["macd"] = macd_result.get("macd")
            indicators["macd_signal"] = macd_result.get("signal")

        # Bollinger Bands
        bb_result = self.calculate_bollinger_bands(prices)
        if bb_result:
            indicators["bollinger_upper"] = bb_result.get("upper")
            indicators["bollinger_middle"] = bb_result.get("middle")
            indicators["bollinger_lower"] = bb_result.get("lower")

        # Store for get_indicators()
        self.indicators["_latest"] = indicators

        return indicators

    def get_indicators(self) -> Dict[str, Any]:
        """
        Get the most recently calculated indicators.
        Used by realistic simulator.

        Returns:
            Dictionary of indicators
        """
        return self.indicators.get("_latest", {})

#!/usr/bin/env python3
"""
Enhanced Trading Engine for JJ Bot
Real trading logic with technical indicators
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import random

class TradingEngine:
    """Autonomous trading decision engine"""
    
    def __init__(self):
        self.price_history = {}
        self.positions = {}
        self.balance = 10000  # Starting balance
        self.risk_per_trade = 0.02  # Risk 2% per trade
        
    def update_price_history(self, symbol: str, price: float):
        """Store price history for analysis"""
        if symbol not in self.price_history:
            self.price_history[symbol] = []
        
        self.price_history[symbol].append({
            'timestamp': datetime.now(),
            'price': price
        })
        
        # Keep only last 100 prices
        if len(self.price_history[symbol]) > 100:
            self.price_history[symbol].pop(0)
    
    def calculate_sma(self, symbol: str, period: int) -> Optional[float]:
        """Simple Moving Average"""
        if symbol not in self.price_history:
            return None
            
        prices = [p['price'] for p in self.price_history[symbol]]
        if len(prices) < period:
            return None
            
        return np.mean(prices[-period:])
    
    def calculate_rsi(self, symbol: str, period: int = 14) -> Optional[float]:
        """Relative Strength Index"""
        if symbol not in self.price_history:
            return None
            
        prices = [p['price'] for p in self.price_history[symbol]]
        if len(prices) < period + 1:
            return None
        
        # Calculate price changes
        deltas = np.diff(prices[-period-1:])
        gains = deltas[deltas > 0]
        losses = -deltas[deltas < 0]
        
        avg_gain = np.mean(gains) if len(gains) > 0 else 0
        avg_loss = np.mean(losses) if len(losses) > 0 else 0
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def generate_signal(self, symbol: str, current_price: float) -> Dict:
        """Generate trading signal based on indicators"""
        
        # Update price history
        self.update_price_history(symbol, current_price)
        
        # Calculate indicators
        sma_20 = self.calculate_sma(symbol, 20)
        sma_50 = self.calculate_sma(symbol, 50)
        rsi = self.calculate_rsi(symbol)
        
        signal = {
            'symbol': symbol,
            'price': current_price,
            'action': 'HOLD',
            'confidence': 0,
            'reason': 'Insufficient data'
        }
        
        # Need enough data for analysis
        if sma_20 and sma_50 and rsi:
            # Bullish signals
            if current_price > sma_20 > sma_50 and rsi < 70:
                signal['action'] = 'BUY'
                signal['confidence'] = 0.7
                signal['reason'] = 'Bullish trend with room to grow'
                
            # Bearish signals
            elif current_price < sma_20 < sma_50 and rsi > 30:
                signal['action'] = 'SELL'
                signal['confidence'] = 0.7
                signal['reason'] = 'Bearish trend with room to fall'
                
            # Oversold - potential buy
            elif rsi < 30:
                signal['action'] = 'BUY'
                signal['confidence'] = 0.6
                signal['reason'] = 'Oversold condition'
                
            # Overbought - potential sell
            elif rsi > 70:
                signal['action'] = 'SELL'
                signal['confidence'] = 0.6
                signal['reason'] = 'Overbought condition'
        
        return signal
    
    def calculate_position_size(self, price: float, stop_loss: float) -> float:
        """Calculate position size based on risk management"""
        risk_amount = self.balance * self.risk_per_trade
        price_risk = abs(price - stop_loss)
        
        if price_risk > 0:
            position_size = risk_amount / price_risk
            return min(position_size, self.balance / price)  # Can't trade more than balance
        
        return 0
    
    def execute_trade(self, signal: Dict) -> Dict:
        """Execute trade based on signal"""
        
        # For now, simulate execution
        # In production, this would connect to exchange API
        
        trade = {
            'timestamp': datetime.now().isoformat(),
            'symbol': signal['symbol'],
            'signal': signal['action'],
            'last_price': signal['price'],
            'vwap': signal['price'] * 0.99,  # Simulated VWAP
            'pnl': 0,
            'confidence': signal['confidence'],
            'reason': signal['reason']
        }
        
        # Calculate simulated P&L based on confidence
        if signal['action'] in ['BUY', 'SELL']:
            # Higher confidence = better chance of profit
            profit_chance = signal['confidence']
            if random.random() < profit_chance:
                trade['pnl'] = random.uniform(10, 100) * signal['confidence']
            else:
                trade['pnl'] = random.uniform(-50, -10) * (1 - signal['confidence'])
        
        return trade

# Global engine instance
trading_engine = TradingEngine()

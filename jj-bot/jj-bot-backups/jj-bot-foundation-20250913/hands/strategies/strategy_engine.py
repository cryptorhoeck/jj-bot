import random
import numpy as np
from typing import Dict, List, Any
from datetime import datetime, timedelta
import json

class StrategyEngine:
    """
    JJ Gorilla's Multi-Strategy Trading Engine
    Combines multiple strategies for better performance
    """
    
    def __init__(self):
        self.strategies = {
            'vwap_divergence': VWAPDivergenceStrategy(),
            'momentum_breakout': MomentumBreakoutStrategy(), 
            'mean_reversion': MeanReversionStrategy(),
            'volume_spike': VolumeSpikeStrategy(),
            'smart_money': SmartMoneyStrategy()
        }
        
        self.strategy_weights = {
            'vwap_divergence': 0.3,
            'momentum_breakout': 0.25,
            'mean_reversion': 0.2,
            'volume_spike': 0.15,
            'smart_money': 0.1
        }
        
        self.performance_history = {}
        
    def analyze_market(self, market_data: Dict) -> Dict:
        """Run all strategies and combine signals"""
        
        signals = {}
        confidences = {}
        
        # Run each strategy
        for name, strategy in self.strategies.items():
            try:
                result = strategy.analyze(market_data)
                signals[name] = result['signal']
                confidences[name] = result['confidence']
            except Exception as e:
                print(f"Strategy {name} error: {e}")
                signals[name] = 'HOLD'
                confidences[name] = 0.0
        
        # Combine signals using weighted consensus
        consensus = self._calculate_consensus(signals, confidences)
        
        return {
            'consensus_signal': consensus['signal'],
            'consensus_confidence': consensus['confidence'],
            'individual_strategies': signals,
            'confidences': confidences,
            'strategy_weights': self.strategy_weights,
            'recommendation': self._get_recommendation(consensus)
        }
    
    def _calculate_consensus(self, signals: Dict, confidences: Dict) -> Dict:
        """Calculate weighted consensus from all strategies"""
        
        long_weight = 0.0
        short_weight = 0.0
        
        for strategy_name, signal in signals.items():
            weight = self.strategy_weights.get(strategy_name, 0.0)
            confidence = confidences.get(strategy_name, 0.0)
            
            if signal == 'LONG':
                long_weight += weight * confidence
            elif signal == 'SHORT':
                short_weight += weight * confidence
        
        # Determine consensus
        if long_weight > short_weight and long_weight > 0.4:
            return {'signal': 'LONG', 'confidence': long_weight}
        elif short_weight > long_weight and short_weight > 0.4:
            return {'signal': 'SHORT', 'confidence': short_weight}
        else:
            return {'signal': 'HOLD', 'confidence': max(long_weight, short_weight)}
    
    def _get_recommendation(self, consensus: Dict) -> str:
        """Get JJ Gorilla's trading recommendation"""
        signal = consensus['signal']
        confidence = consensus['confidence']
        
        if signal == 'LONG':
            if confidence > 0.7:
                return "🔥 STRONG BUY - High conviction LONG setup"
            elif confidence > 0.5:
                return "📈 BUY - Good LONG opportunity"
            else:
                return "📊 WEAK LONG - Consider smaller position"
        elif signal == 'SHORT':
            if confidence > 0.7:
                return "🔥 STRONG SELL - High conviction SHORT setup"
            elif confidence > 0.5:
                return "📉 SELL - Good SHORT opportunity"
            else:
                return "📊 WEAK SHORT - Consider smaller position"
        else:
            return "⏸️ HOLD - No clear signal, wait for better setup"

class VWAPDivergenceStrategy:
    """JJ's signature VWAP divergence strategy"""
    
    def analyze(self, data: Dict) -> Dict:
        price = data.get('current_price', 0)
        vwap = data.get('vwap', 0)
        volume = data.get('volume_24h', 0)
        
        if vwap == 0:
            return {'signal': 'HOLD', 'confidence': 0.0}
        
        # Calculate VWAP deviation
        deviation = (price - vwap) / vwap * 100
        
        # Volume factor (higher volume = higher confidence)
        volume_factor = min(volume / 1000000000, 2.0)  # Cap at 2x
        
        if deviation > 0.3:  # Price 0.3% above VWAP
            confidence = min(abs(deviation) / 2.0 * volume_factor, 1.0)
            return {'signal': 'SHORT', 'confidence': confidence}
        elif deviation < -0.3:  # Price 0.3% below VWAP
            confidence = min(abs(deviation) / 2.0 * volume_factor, 1.0)
            return {'signal': 'LONG', 'confidence': confidence}
        else:
            return {'signal': 'HOLD', 'confidence': 0.0}

class MomentumBreakoutStrategy:
    """Momentum-based breakout detection"""
    
    def analyze(self, data: Dict) -> Dict:
        price_change = data.get('price_change_24h', 0)
        volume_change = data.get('volume_change_24h', 0)
        
        # Strong momentum signals
        if price_change > 5 and volume_change > 50:
            return {'signal': 'LONG', 'confidence': 0.8}
        elif price_change < -5 and volume_change > 50:
            return {'signal': 'SHORT', 'confidence': 0.8}
        elif abs(price_change) > 3:
            confidence = abs(price_change) / 10.0
            signal = 'LONG' if price_change > 0 else 'SHORT'
            return {'signal': signal, 'confidence': confidence}
        else:
            return {'signal': 'HOLD', 'confidence': 0.0}

class MeanReversionStrategy:
    """Mean reversion for oversold/overbought conditions"""
    
    def analyze(self, data: Dict) -> Dict:
        price_change = data.get('price_change_24h', 0)
        
        # Look for extreme moves to fade
        if price_change > 8:  # Overbought
            confidence = min((price_change - 8) / 10.0, 0.9)
            return {'signal': 'SHORT', 'confidence': confidence}
        elif price_change < -8:  # Oversold
            confidence = min((abs(price_change) - 8) / 10.0, 0.9)
            return {'signal': 'LONG', 'confidence': confidence}
        else:
            return {'signal': 'HOLD', 'confidence': 0.0}

class VolumeSpikeStrategy:
    """Volume spike detection for institutional flow"""
    
    def analyze(self, data: Dict) -> Dict:
        volume_change = data.get('volume_change_24h', 0)
        price_change = data.get('price_change_24h', 0)
        
        # Volume spike with price confirmation
        if volume_change > 100:  # 100% volume increase
            if price_change > 1:
                confidence = min(volume_change / 200.0, 0.8)
                return {'signal': 'LONG', 'confidence': confidence}
            elif price_change < -1:
                confidence = min(volume_change / 200.0, 0.8)
                return {'signal': 'SHORT', 'confidence': confidence}
        
        return {'signal': 'HOLD', 'confidence': 0.0}

class SmartMoneyStrategy:
    """Detect smart money vs retail sentiment"""
    
    def analyze(self, data: Dict) -> Dict:
        # Simulated smart money indicators
        # In real implementation, this would use order flow, whale movements, etc.
        
        time_of_day = datetime.now().hour
        
        # Smart money typically trades during certain hours
        if 9 <= time_of_day <= 11 or 14 <= time_of_day <= 16:  # Market hours
            # Use volume and price action to detect institutional activity
            volume = data.get('volume_24h', 0)
            price_change = data.get('price_change_24h', 0)
            
            if volume > 2000000000 and abs(price_change) < 2:  # High volume, low volatility
                # Institutional accumulation/distribution
                signal = 'LONG' if price_change > 0 else 'SHORT'
                return {'signal': signal, 'confidence': 0.6}
        
        return {'signal': 'HOLD', 'confidence': 0.0}

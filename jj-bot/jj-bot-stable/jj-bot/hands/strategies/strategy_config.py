import json
from pathlib import Path

class StrategyConfig:
    """Manage strategy configurations and weights"""
    
    def __init__(self, config_file='strategy_config.json'):
        self.config_file = Path.home() / 'jj-bot' / 'data' / config_file
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        self.config = self.load_config()
    
    def load_config(self):
        """Load strategy configuration"""
        default_config = {
            'strategy_weights': {
                'vwap_divergence': 0.3,
                'momentum_breakout': 0.25,
                'mean_reversion': 0.2,
                'volume_spike': 0.15,
                'smart_money': 0.1
            },
            'strategy_params': {
                'vwap_divergence': {
                    'min_deviation': 0.3,
                    'volume_threshold': 1000000000
                },
                'momentum_breakout': {
                    'price_threshold': 5.0,
                    'volume_threshold': 50.0
                },
                'mean_reversion': {
                    'overbought_threshold': 8.0,
                    'oversold_threshold': -8.0
                }
            },
            'risk_management': {
                'max_position_per_strategy': 0.2,
                'stop_loss_percent': 2.0,
                'take_profit_percent': 4.0
            }
        }
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except:
                return default_config
        else:
            self.save_config(default_config)
            return default_config
    
    def save_config(self, config=None):
        """Save strategy configuration"""
        if config:
            self.config = config
        
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def update_weights(self, new_weights):
        """Update strategy weights"""
        self.config['strategy_weights'].update(new_weights)
        self.save_config()
    
    def get_weights(self):
        """Get current strategy weights"""
        return self.config['strategy_weights']

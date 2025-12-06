"""
Configuration management for JJ-Bot
Loads configuration from config.json and environment variables
Environment variables take precedence over config.json values
"""

import os
import json
from typing import Any, Dict, Optional
from pathlib import Path
from dotenv import load_dotenv

# Load .env file if it exists
load_dotenv()

# Base directory
BASE_DIR = Path(__file__).parent

# Load config.json
CONFIG_FILE = BASE_DIR / "config.json"
_config_data: Dict[str, Any] = {}

if CONFIG_FILE.exists():
    with open(CONFIG_FILE, 'r') as f:
        _config_data = json.load(f)


def get_env(key: str, default: Any = None, cast_type: type = str) -> Any:
    """
    Get environment variable with type casting

    Args:
        key: Environment variable name
        default: Default value if not found
        cast_type: Type to cast the value to (str, int, float, bool)

    Returns:
        Typed value from environment or default
    """
    value = os.getenv(key)

    if value is None:
        return default

    if cast_type == bool:
        return value.lower() in ('true', '1', 'yes', 'on')
    elif cast_type in (int, float):
        try:
            return cast_type(value)
        except (ValueError, TypeError):
            return default

    return value


def get_config(section: str, key: str, default: Any = None) -> Any:
    """
    Get configuration value from environment or config.json

    Environment variable naming: SECTION_KEY (e.g., MARKET_FEED_UPDATE_INTERVAL)

    Args:
        section: Configuration section (e.g., 'market_feed')
        key: Configuration key (e.g., 'update_interval')
        default: Default value if not found

    Returns:
        Configuration value
    """
    # Build environment variable name
    env_key = f"{section}_{key}".upper()

    # Check environment variable first
    env_value = os.getenv(env_key)
    if env_value is not None:
        # Try to parse as JSON for complex types
        try:
            return json.loads(env_value)
        except (json.JSONDecodeError, TypeError):
            return env_value

    # Fall back to config.json
    if section in _config_data and key in _config_data[section]:
        return _config_data[section][key]

    return default


# ======================
# APPLICATION SETTINGS
# ======================
APP_NAME = get_env('APP_NAME', 'JJ-Bot')

# Load version from VERSION file
def _load_version() -> str:
    """Load version from VERSION file"""
    version_file = BASE_DIR / "VERSION"
    if version_file.exists():
        return version_file.read_text().strip()
    return '3.0.0'  # Fallback

APP_VERSION = get_env('APP_VERSION', _load_version())
ENVIRONMENT = get_env('ENVIRONMENT', 'development')

# ======================
# API CONFIGURATION
# ======================
API_HOST = get_env('API_HOST', '127.0.0.1')
API_PORT = get_env('API_PORT', 8000, int)
API_WORKERS = get_env('API_WORKERS', 1, int)
API_RELOAD = get_env('API_RELOAD', True, bool)

# ======================
# FRONTEND CONFIGURATION
# ======================
FRONTEND_PORT = get_env('FRONTEND_PORT', 5173, int)
FRONTEND_HOST = get_env('FRONTEND_HOST', 'localhost')

# ======================
# DATABASE CONFIGURATION
# ======================
DATABASE_PATH = get_env('DATABASE_PATH', 'data/jj_trades.db')
DATABASE_BACKUP_DIR = get_env('DATABASE_BACKUP_DIR', 'backups')
DATABASE_AUTO_BACKUP = get_env('DATABASE_AUTO_BACKUP', True, bool)

# ======================
# LOGGING CONFIGURATION
# ======================
LOG_LEVEL = get_env('LOG_LEVEL', get_config('system', 'log_level', 'INFO'))
LOG_FORMAT = get_env('LOG_FORMAT', 'json')
LOG_FILE = get_env('LOG_FILE', 'logs/jj-bot.log')
LOG_MAX_SIZE = get_env('LOG_MAX_SIZE', 10485760, int)  # 10MB
LOG_BACKUP_COUNT = get_env('LOG_BACKUP_COUNT', 5, int)
LOG_TO_CONSOLE = get_env('LOG_TO_CONSOLE', True, bool)
LOG_TO_FILE = get_env('LOG_TO_FILE', True, bool)

# ======================
# MARKET DATA CONFIGURATION
# ======================
COINGECKO_API_URL = get_env(
    'COINGECKO_API_URL',
    get_config('market_feed', 'api_url', 'https://api.coingecko.com/api/v3')
)
COINGECKO_API_KEY = get_env('COINGECKO_API_KEY', '')
COINGECKO_RATE_LIMIT = get_env('COINGECKO_RATE_LIMIT', 50, int)  # Requests per minute
COINGECKO_TIMEOUT = get_env('COINGECKO_TIMEOUT', 10, int)
MARKET_DATA_REFRESH_INTERVAL = get_env(
    'MARKET_DATA_REFRESH_INTERVAL',
    get_config('market_feed', 'update_interval', 60),
    int
)

# Market coins list
MARKET_COINS = get_config('market_feed', 'coins', [
    "bitcoin", "ethereum", "binancecoin", "solana", "ripple",
    "cardano", "dogecoin", "avalanche-2", "tron", "chainlink",
    "polkadot", "polygon", "wrapped-bitcoin", "shiba-inu",
    "litecoin", "bitcoin-cash", "uniswap", "stellar", "cosmos",
    "ethereum-classic"
])

# ======================
# TRADING CONFIGURATION
# ======================
TRADING_MODE = get_env('TRADING_MODE', 'paper')  # paper, live
TRADING_ENABLED = get_env(
    'TRADING_ENABLED',
    get_config('trading_bot', 'enabled', True),
    bool
)
PAPER_TRADING = get_env(
    'PAPER_TRADING',
    get_config('trading_bot', 'paper_trading', True),
    bool
)

# Risk management
MAX_POSITION_SIZE = get_env('MAX_POSITION_SIZE', 1000, int)
MAX_DAILY_LOSS = get_env('MAX_DAILY_LOSS', 1000.0, float)
MAX_TRADES_PER_DAY = get_env('MAX_TRADES_PER_DAY', 20, int)
COOLDOWN_SECONDS = get_env('COOLDOWN_SECONDS', 60, int)
MAX_POSITIONS = get_env(
    'MAX_POSITIONS',
    get_config('trading_bot', 'max_positions', 5),
    int
)
RISK_PER_TRADE = get_env(
    'RISK_PER_TRADE',
    get_config('trading_bot', 'risk_per_trade', 0.02),
    float
)
COOLDOWN_MINUTES = get_env(
    'COOLDOWN_MINUTES',
    get_config('trading_bot', 'cooldown_minutes', 5),
    int
)

# Position sizing
DEFAULT_POSITION_SIZE = get_env('DEFAULT_POSITION_SIZE', 100, int)
POSITION_SIZE_METHOD = get_env('POSITION_SIZE_METHOD', 'fixed')  # fixed, percentage, kelly

# ======================
# STRATEGY CONFIGURATION
# ======================
# RSI
RSI_PERIOD = get_env('RSI_PERIOD', 14, int)
RSI_OVERBOUGHT = get_env(
    'RSI_OVERBOUGHT',
    get_config('strategy_engine', 'rsi_overbought', 70),
    int
)
RSI_OVERSOLD = get_env(
    'RSI_OVERSOLD',
    get_config('strategy_engine', 'rsi_oversold', 30),
    int
)

# SMA
SMA_SHORT_PERIOD = get_env('SMA_SHORT_PERIOD', 20, int)
SMA_LONG_PERIOD = get_env('SMA_LONG_PERIOD', 50, int)
SMA_FAST = get_env(
    'SMA_FAST',
    get_config('strategy_engine', 'sma_fast', 10),
    int
)
SMA_SLOW = get_env(
    'SMA_SLOW',
    get_config('strategy_engine', 'sma_slow', 20),
    int
)

# MACD
MACD_FAST_PERIOD = get_env('MACD_FAST_PERIOD', 12, int)
MACD_SLOW_PERIOD = get_env('MACD_SLOW_PERIOD', 26, int)
MACD_SIGNAL_PERIOD = get_env('MACD_SIGNAL_PERIOD', 9, int)

# Bollinger Bands
BOLLINGER_PERIOD = get_env('BOLLINGER_PERIOD', 20, int)
BOLLINGER_STD_DEV = get_env('BOLLINGER_STD_DEV', 2, int)

# Signal strength
MIN_SIGNAL_STRENGTH = get_env(
    'MIN_SIGNAL_STRENGTH',
    get_config('strategy_engine', 'min_signal_strength', 0.7),
    float
)

# ======================
# SERVICE CONFIGURATION
# ======================
AUTO_START_SERVICES = get_env(
    'AUTO_START_SERVICES',
    get_config('system', 'auto_start_services', True),
    bool
)
SERVICE_CHECK_INTERVAL = get_env('SERVICE_CHECK_INTERVAL', 5, int)
SERVICE_TIMEOUT = get_env('SERVICE_TIMEOUT', 30, int)

# ======================
# WEBSOCKET CONFIGURATION
# ======================
WEBSOCKET_PING_INTERVAL = get_env('WEBSOCKET_PING_INTERVAL', 30, int)
WEBSOCKET_PING_TIMEOUT = get_env('WEBSOCKET_PING_TIMEOUT', 10, int)
WEBSOCKET_MAX_CONNECTIONS = get_env('WEBSOCKET_MAX_CONNECTIONS', 100, int)

# ======================
# BACKTESTING CONFIGURATION
# ======================
BACKTEST_DEFAULT_CAPITAL = get_env(
    'BACKTEST_DEFAULT_CAPITAL',
    get_config('backtesting', 'initial_capital', 10000),
    float
)
BACKTEST_COMMISSION = get_env(
    'BACKTEST_COMMISSION',
    get_config('backtesting', 'commission', 0.001),
    float
)
BACKTEST_SLIPPAGE = get_env(
    'BACKTEST_SLIPPAGE',
    get_config('backtesting', 'slippage', 0.0005),
    float
)
BACKTEST_POSITION_SIZE = get_env(
    'BACKTEST_POSITION_SIZE',
    get_config('backtesting', 'position_size', 0.1),
    float
)

# ======================
# ANALYTICS CONFIGURATION
# ======================
ANALYTICS_INTERVAL = get_env(
    'ANALYSIS_INTERVAL',
    get_config('analytics', 'analysis_interval', 60),
    int
)
ANALYTICS_LOOKBACK_DAYS = get_env(
    'LOOKBACK_DAYS',
    get_config('analytics', 'lookback_days', 30),
    int
)

# ======================
# EXCHANGE API KEYS
# ======================
# Kraken
KRAKEN_API_KEY = get_env('KRAKEN_API_KEY', '')
KRAKEN_API_SECRET = get_env('KRAKEN_API_SECRET', '')
KRAKEN_API_URL = get_env('KRAKEN_API_URL', 'https://api.kraken.com')

# Coinbase
COINBASE_API_KEY = get_env('COINBASE_API_KEY', '')
COINBASE_API_SECRET = get_env('COINBASE_API_SECRET', '')
COINBASE_PASSPHRASE = get_env('COINBASE_PASSPHRASE', '')
COINBASE_API_URL = get_env('COINBASE_API_URL', 'https://api.coinbase.com')

# ======================
# NOTIFICATION SETTINGS
# ======================
ENABLE_EMAIL_NOTIFICATIONS = get_env('ENABLE_EMAIL_NOTIFICATIONS', False, bool)
SMTP_HOST = get_env('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT = get_env('SMTP_PORT', 587, int)
SMTP_USER = get_env('SMTP_USER', '')
SMTP_PASSWORD = get_env('SMTP_PASSWORD', '')
NOTIFICATION_EMAIL = get_env('NOTIFICATION_EMAIL', '')

ENABLE_DISCORD_NOTIFICATIONS = get_env('ENABLE_DISCORD_NOTIFICATIONS', False, bool)
DISCORD_WEBHOOK_URL = get_env('DISCORD_WEBHOOK_URL', '')

ENABLE_TELEGRAM_NOTIFICATIONS = get_env('ENABLE_TELEGRAM_NOTIFICATIONS', False, bool)
TELEGRAM_BOT_TOKEN = get_env('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = get_env('TELEGRAM_CHAT_ID', '')

# ======================
# CACHE CONFIGURATION
# ======================
ENABLE_CACHE = get_env('ENABLE_CACHE', False, bool)
CACHE_TYPE = get_env('CACHE_TYPE', 'memory')  # memory, redis
CACHE_TTL = get_env('CACHE_TTL', 300, int)

# Redis
REDIS_HOST = get_env('REDIS_HOST', 'localhost')
REDIS_PORT = get_env('REDIS_PORT', 6379, int)
REDIS_PASSWORD = get_env('REDIS_PASSWORD', '')
REDIS_DB = get_env('REDIS_DB', 0, int)

# ======================
# SECURITY SETTINGS
# ======================
ENABLE_API_AUTH = get_env('ENABLE_API_AUTH', False, bool)
JWT_SECRET_KEY = get_env('JWT_SECRET_KEY', '')
JWT_ALGORITHM = get_env('JWT_ALGORITHM', 'HS256')
JWT_EXPIRATION = get_env('JWT_EXPIRATION', 3600, int)

CORS_ORIGINS = get_env('CORS_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173')
CORS_ALLOW_CREDENTIALS = get_env('CORS_ALLOW_CREDENTIALS', True, bool)

ENABLE_RATE_LIMITING = get_env('ENABLE_RATE_LIMITING', False, bool)
RATE_LIMIT_PER_MINUTE = get_env('RATE_LIMIT_PER_MINUTE', 60, int)

# ======================
# MONITORING & ANALYTICS
# ======================
ENABLE_METRICS = get_env('ENABLE_METRICS', True, bool)
METRICS_INTERVAL = get_env('METRICS_INTERVAL', 60, int)

ENABLE_ERROR_TRACKING = get_env('ENABLE_ERROR_TRACKING', False, bool)
SENTRY_DSN = get_env('SENTRY_DSN', '')

# ======================
# FEATURE FLAGS
# ======================
ENABLE_REAL_TRADING = get_env('ENABLE_REAL_TRADING', False, bool)
ENABLE_BACKTESTING = get_env('ENABLE_BACKTESTING', True, bool)
ENABLE_PAPER_TRADING = get_env('ENABLE_PAPER_TRADING', True, bool)
ENABLE_ANALYTICS = get_env('ENABLE_ANALYTICS', True, bool)
ENABLE_WEBSOCKET = get_env('ENABLE_WEBSOCKET', True, bool)
ENABLE_CSV_EXPORT = get_env('ENABLE_CSV_EXPORT', True, bool)

# ======================
# DEVELOPMENT SETTINGS
# ======================
DEBUG = get_env('DEBUG', True, bool)
HOT_RELOAD = get_env('HOT_RELOAD', True, bool)
USE_MOCK_DATA = get_env('USE_MOCK_DATA', False, bool)
TEST_DATABASE_PATH = get_env('TEST_DATABASE_PATH', 'data/test_jj_trades.db')


def get_all_config() -> Dict[str, Any]:
    """
    Get all configuration as a dictionary

    Returns:
        Dictionary with all configuration values
    """
    return {
        'app': {
            'name': APP_NAME,
            'version': APP_VERSION,
            'environment': ENVIRONMENT,
        },
        'api': {
            'host': API_HOST,
            'port': API_PORT,
            'workers': API_WORKERS,
            'reload': API_RELOAD,
        },
        'database': {
            'path': DATABASE_PATH,
            'backup_dir': DATABASE_BACKUP_DIR,
            'auto_backup': DATABASE_AUTO_BACKUP,
        },
        'logging': {
            'level': LOG_LEVEL,
            'format': LOG_FORMAT,
            'file': LOG_FILE,
            'max_size': LOG_MAX_SIZE,
            'backup_count': LOG_BACKUP_COUNT,
            'to_console': LOG_TO_CONSOLE,
            'to_file': LOG_TO_FILE,
        },
        'market_data': {
            'api_url': COINGECKO_API_URL,
            'rate_limit': COINGECKO_RATE_LIMIT,
            'timeout': COINGECKO_TIMEOUT,
            'refresh_interval': MARKET_DATA_REFRESH_INTERVAL,
            'coins': MARKET_COINS,
        },
        'trading': {
            'mode': TRADING_MODE,
            'enabled': TRADING_ENABLED,
            'paper_trading': PAPER_TRADING,
            'max_positions': MAX_POSITIONS,
            'risk_per_trade': RISK_PER_TRADE,
        },
        'strategy': {
            'rsi': {
                'period': RSI_PERIOD,
                'overbought': RSI_OVERBOUGHT,
                'oversold': RSI_OVERSOLD,
            },
            'sma': {
                'short_period': SMA_SHORT_PERIOD,
                'long_period': SMA_LONG_PERIOD,
                'fast': SMA_FAST,
                'slow': SMA_SLOW,
            },
            'min_signal_strength': MIN_SIGNAL_STRENGTH,
        },
        'feature_flags': {
            'real_trading': ENABLE_REAL_TRADING,
            'backtesting': ENABLE_BACKTESTING,
            'paper_trading': ENABLE_PAPER_TRADING,
            'analytics': ENABLE_ANALYTICS,
            'websocket': ENABLE_WEBSOCKET,
            'csv_export': ENABLE_CSV_EXPORT,
        },
    }


def print_config() -> None:
    """Print current configuration (masking sensitive values)"""
    config = get_all_config()

    print("\n" + "=" * 50)
    print("JJ-Bot Configuration")
    print("=" * 50)

    def _print_dict(d: Dict, indent: int = 0):
        for key, value in d.items():
            if isinstance(value, dict):
                print("  " * indent + f"{key}:")
                _print_dict(value, indent + 1)
            else:
                # Mask sensitive values
                if any(sensitive in key.lower() for sensitive in ['key', 'secret', 'password', 'token']):
                    value = '***MASKED***' if value else '(not set)'
                print("  " * indent + f"{key}: {value}")

    _print_dict(config)
    print("=" * 50 + "\n")


if __name__ == "__main__":
    # When run directly, print configuration
    print_config()

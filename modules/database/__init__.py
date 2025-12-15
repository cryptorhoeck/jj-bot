"""
Database Module

Provides database connectivity and utilities for JJ-Bot.
The data_manager module is the SINGLE SOURCE OF TRUTH for all bot data.
"""

from .connection import (
    get_connection,
    get_db_connection,
    init_trades_db,
    init_price_history_db,
    init_learning_db,
    init_all_databases,
    TRADES_DB_PATH,
    PRICE_HISTORY_DB_PATH,
    LEARNING_DB_PATH
)

# Import data_manager module (single source of truth)
from . import data_manager

__all__ = [
    'get_connection',
    'get_db_connection',
    'init_trades_db',
    'init_price_history_db',
    'init_learning_db',
    'init_all_databases',
    'TRADES_DB_PATH',
    'PRICE_HISTORY_DB_PATH',
    'LEARNING_DB_PATH',
    'data_manager'
]

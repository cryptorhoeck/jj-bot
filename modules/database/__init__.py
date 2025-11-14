"""
Database Module

Provides database connectivity and utilities for JJ-Bot.
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

__all__ = [
    'get_connection',
    'get_db_connection',
    'init_trades_db',
    'init_price_history_db',
    'init_learning_db',
    'init_all_databases',
    'TRADES_DB_PATH',
    'PRICE_HISTORY_DB_PATH',
    'LEARNING_DB_PATH'
]

"""Consolidated data schema - Phase 1 refactor

Revision ID: 20251215_0001
Revises: 20250114_0001
Create Date: 2025-12-15

This migration consolidates all data into SQLite:
- Enhanced trades table with full trade lifecycle
- training_episodes for RL training metrics
- equity_snapshots for equity curve data
- bot_state for runtime state (replaces bot_state.json)
- model_versions for tracking trained models
"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

revision = '20251215_0001'
down_revision = '20250114_0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create consolidated schema"""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    # 1. Enhanced trades table - full trade lifecycle
    if 'trades' in existing_tables:
        # Add missing columns to existing trades table
        columns = [col['name'] for col in inspector.get_columns('trades')]

        new_columns = [
            ('side', 'TEXT'),  # 'long' or 'short'
            ('size', 'REAL'),
            ('entry_price', 'REAL'),
            ('exit_price', 'REAL'),
            ('entry_time', 'TEXT'),
            ('exit_time', 'TEXT'),
            ('pnl_pct', 'REAL'),
            ('signal_source', 'TEXT'),  # 'rl_agent', 'edge_strategy', etc.
            ('exit_reason', 'TEXT'),  # 'take_profit', 'stop_loss', 'signal', 'shutdown'
            ('model_version', 'TEXT'),  # Which model made this trade
            ('fees', 'REAL DEFAULT 0.0'),
            ('slippage', 'REAL DEFAULT 0.0'),
        ]

        for col_name, col_type in new_columns:
            if col_name not in columns:
                op.execute(f"ALTER TABLE trades ADD COLUMN {col_name} {col_type}")

    # 2. Training episodes table - one row per training episode
    if 'training_episodes' not in existing_tables:
        op.create_table(
            'training_episodes',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('episode', sa.Integer(), nullable=False),
            sa.Column('session_id', sa.Text()),  # Group episodes by training session
            sa.Column('timestamp', sa.Text(), nullable=False),
            sa.Column('symbol', sa.Text()),
            sa.Column('total_reward', sa.Real(), default=0.0),
            sa.Column('avg_reward', sa.Real(), default=0.0),
            sa.Column('total_pnl', sa.Real(), default=0.0),
            sa.Column('trades', sa.Integer(), default=0),
            sa.Column('wins', sa.Integer(), default=0),
            sa.Column('losses', sa.Integer(), default=0),
            sa.Column('win_rate', sa.Real(), default=0.0),
            sa.Column('profit_factor', sa.Real(), default=0.0),
            sa.Column('max_drawdown', sa.Real(), default=0.0),
            sa.Column('sharpe_ratio', sa.Real()),
            sa.Column('policy_loss', sa.Real()),
            sa.Column('value_loss', sa.Real()),
            sa.Column('entropy', sa.Real()),
            sa.Column('learning_rate', sa.Real()),
            sa.Column('steps', sa.Integer(), default=0),
            sa.Column('duration_seconds', sa.Real()),
        )
        op.create_index('idx_training_episodes_episode', 'training_episodes', ['episode'])
        op.create_index('idx_training_episodes_session', 'training_episodes', ['session_id'])
        op.create_index('idx_training_episodes_timestamp', 'training_episodes', ['timestamp'])

    # 3. Equity snapshots - for equity curves
    if 'equity_snapshots' not in existing_tables:
        op.create_table(
            'equity_snapshots',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('timestamp', sa.Text(), nullable=False),
            sa.Column('equity', sa.Real(), nullable=False),
            sa.Column('cash', sa.Real()),
            sa.Column('positions_value', sa.Real()),
            sa.Column('daily_pnl', sa.Real(), default=0.0),
            sa.Column('total_pnl', sa.Real(), default=0.0),
            sa.Column('drawdown', sa.Real(), default=0.0),
            sa.Column('drawdown_pct', sa.Real(), default=0.0),
            sa.Column('peak_equity', sa.Real()),
            sa.Column('open_positions', sa.Integer(), default=0),
            sa.Column('mode', sa.Text()),  # 'paper', 'live', 'training'
        )
        op.create_index('idx_equity_snapshots_timestamp', 'equity_snapshots', ['timestamp'])
        op.create_index('idx_equity_snapshots_mode', 'equity_snapshots', ['mode'])

    # 4. Bot state - single row, replaces bot_state.json
    if 'bot_state' not in existing_tables:
        op.create_table(
            'bot_state',
            sa.Column('id', sa.Integer(), primary_key=True, default=1),
            sa.Column('equity', sa.Real(), default=10000.0),
            sa.Column('peak_equity', sa.Real(), default=10000.0),
            sa.Column('daily_pnl', sa.Real(), default=0.0),
            sa.Column('daily_start_equity', sa.Real(), default=10000.0),
            sa.Column('total_pnl', sa.Real(), default=0.0),
            sa.Column('total_trades', sa.Integer(), default=0),
            sa.Column('winning_trades', sa.Integer(), default=0),
            sa.Column('losing_trades', sa.Integer(), default=0),
            sa.Column('trading_iq', sa.Integer(), default=0),
            sa.Column('expertise_level', sa.Text(), default='Untrained'),
            sa.Column('training_sessions', sa.Integer(), default=0),
            sa.Column('total_training_episodes', sa.Integer(), default=0),
            sa.Column('total_training_trades', sa.Integer(), default=0),
            sa.Column('last_training_date', sa.Text()),
            sa.Column('current_model_version', sa.Text()),
            sa.Column('avg_win_rate', sa.Real(), default=0.0),
            sa.Column('avg_profit_factor', sa.Real(), default=0.0),
            sa.Column('best_win_rate', sa.Real(), default=0.0),
            sa.Column('best_profit_factor', sa.Real(), default=0.0),
            sa.Column('mode', sa.Text(), default='paper'),
            sa.Column('last_updated', sa.Text()),
        )
        # Insert default row
        op.execute("""
            INSERT INTO bot_state (id, equity, peak_equity, daily_start_equity, expertise_level, mode, last_updated)
            VALUES (1, 10000.0, 10000.0, 10000.0, 'Untrained', 'paper', datetime('now'))
        """)

    # 5. Model versions - track trained models
    if 'model_versions' not in existing_tables:
        op.create_table(
            'model_versions',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('version', sa.Text(), nullable=False, unique=True),
            sa.Column('created_at', sa.Text(), nullable=False),
            sa.Column('file_path', sa.Text()),
            sa.Column('training_episodes', sa.Integer()),
            sa.Column('final_iq', sa.Integer()),
            sa.Column('final_win_rate', sa.Real()),
            sa.Column('final_profit_factor', sa.Real()),
            sa.Column('notes', sa.Text()),
            sa.Column('is_active', sa.Boolean(), default=False),
        )
        op.create_index('idx_model_versions_version', 'model_versions', ['version'])
        op.create_index('idx_model_versions_active', 'model_versions', ['is_active'])

    # 6. Open positions table - track current positions
    if 'open_positions' not in existing_tables:
        op.create_table(
            'open_positions',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('symbol', sa.Text(), nullable=False, unique=True),
            sa.Column('side', sa.Text(), nullable=False),  # 'long' or 'short'
            sa.Column('size', sa.Real(), nullable=False),
            sa.Column('entry_price', sa.Real(), nullable=False),
            sa.Column('entry_time', sa.Text(), nullable=False),
            sa.Column('current_price', sa.Real()),
            sa.Column('unrealized_pnl', sa.Real(), default=0.0),
            sa.Column('unrealized_pnl_pct', sa.Real(), default=0.0),
            sa.Column('stop_loss', sa.Real()),
            sa.Column('take_profit', sa.Real()),
            sa.Column('trailing_stop', sa.Real()),
            sa.Column('signal_source', sa.Text()),
            sa.Column('model_version', sa.Text()),
            sa.Column('last_updated', sa.Text()),
        )
        op.create_index('idx_open_positions_symbol', 'open_positions', ['symbol'])


def downgrade() -> None:
    """Remove consolidated schema tables"""
    op.drop_table('open_positions')
    op.drop_table('model_versions')
    op.drop_table('bot_state')
    op.drop_table('equity_snapshots')
    op.drop_table('training_episodes')

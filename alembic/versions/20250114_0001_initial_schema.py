"""Initial database schema

Revision ID: 20250114_0001
Revises:
Create Date: 2025-01-14 00:01:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20250114_0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create initial trades table"""
    # Check if table already exists
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if 'trades' not in inspector.get_table_names():
        op.create_table(
            'trades',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('timestamp', sa.Text(), nullable=False),
            sa.Column('symbol', sa.Text(), nullable=False),
            sa.Column('signal', sa.Text(), nullable=False),
            sa.Column('last_price', sa.Real(), nullable=False),
            sa.Column('vwap', sa.Real(), nullable=False),
            sa.Column('pnl', sa.Real(), nullable=False, server_default='0.0'),
        )

        # Create indexes for better query performance
        op.create_index('idx_trades_timestamp', 'trades', ['timestamp'])
        op.create_index('idx_trades_symbol', 'trades', ['symbol'])
        op.create_index('idx_trades_signal', 'trades', ['signal'])
    else:
        # Table exists, ensure pnl column exists
        columns = [col['name'] for col in inspector.get_columns('trades')]
        if 'pnl' not in columns:
            op.add_column('trades', sa.Column('pnl', sa.Real(), nullable=False, server_default='0.0'))


def downgrade() -> None:
    """Drop trades table"""
    op.drop_index('idx_trades_signal', 'trades')
    op.drop_index('idx_trades_symbol', 'trades')
    op.drop_index('idx_trades_timestamp', 'trades')
    op.drop_table('trades')

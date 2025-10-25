"""
Add conversation_history table for storing query context per project

Revision ID: conversation_history_001
Revises:
Create Date: 2025-10-25
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'conversation_history_001'
down_revision = None
depends_on = None


def upgrade():
    """Create conversation_history table"""
    op.create_table(
        'conversation_history',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('generated_sql', sa.Text(), nullable=True),
        sa.Column('response_summary', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for faster queries
    op.create_index(op.f('ix_conversation_history_id'), 'conversation_history', ['id'], unique=False)
    op.create_index(op.f('ix_conversation_history_project_id'), 'conversation_history', ['project_id'], unique=False)
    op.create_index(op.f('ix_conversation_history_created_at'), 'conversation_history', ['created_at'], unique=False)


def downgrade():
    """Drop conversation_history table"""
    op.drop_index(op.f('ix_conversation_history_created_at'), table_name='conversation_history')
    op.drop_index(op.f('ix_conversation_history_project_id'), table_name='conversation_history')
    op.drop_index(op.f('ix_conversation_history_id'), table_name='conversation_history')
    op.drop_table('conversation_history')

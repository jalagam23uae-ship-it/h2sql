"""
Create projects table for local project management

Revision ID: create_projects_001
Create Date: 2025-10-25
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = 'create_projects_001'
down_revision = '395835807854'  # response_logs table
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'projects',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('train_id', sa.String(255), nullable=True),
        sa.Column('connection', sa.Text(), nullable=False),
        sa.Column('db_metadata', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_projects_id'), 'projects', ['id'], unique=False)
    op.create_index(op.f('ix_projects_name'), 'projects', ['name'], unique=True)


def downgrade():
    op.drop_index(op.f('ix_projects_name'), table_name='projects')
    op.drop_index(op.f('ix_projects_id'), table_name='projects')
    op.drop_table('projects')

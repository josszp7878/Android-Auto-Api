"""add total score

Revision ID: xxx
Revises: xxx
Create Date: 2024-03-21 xx:xx:xx.xxx
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    # 添加总分字段
    op.add_column('devices', sa.Column('total_score', sa.Integer(), nullable=False, server_default='0'))

def downgrade():
    # 删除总分字段
    op.drop_column('devices', 'total_score') 
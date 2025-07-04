"""initial models

Revision ID: 7d701fe8cfa1
Revises: 
Create Date: 2025-06-17 10:10:12.436663

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7d701fe8cfa1'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('platform_configs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('config_name', sa.String(length=100), nullable=False),
    sa.Column('platform_name', sa.String(length=50), nullable=False),
    sa.Column('config_key', sa.String(length=100), nullable=False),
    sa.Column('config_value', sa.Text(), nullable=False),
    sa.Column('environment', sa.String(length=20), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'platform_name', 'config_key', 'environment', name='_user_platform_key_env_uc')
    )
    op.create_table('tag_mappings',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('platform_name', sa.String(length=50), nullable=False),
    sa.Column('mapping_name', sa.String(length=100), nullable=False),
    sa.Column('tag_name', sa.String(length=100), nullable=False),
    sa.Column('tag_id', sa.Integer(), nullable=False),
    sa.Column('environment', sa.String(length=20), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'platform_name', 'tag_name', 'environment', name='_user_platform_tag_env_uc')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('tag_mappings')
    op.drop_table('platform_configs')
    # ### end Alembic commands ###

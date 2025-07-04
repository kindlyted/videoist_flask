"""add wordpress_sites and wechat_accounts tables

Revision ID: 11b9c7652802
Revises: 3e5358febd63
Create Date: 2025-06-17 10:34:25.248514

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '11b9c7652802'
down_revision = '3e5358febd63'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('wechat_accounts',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('account_name', sa.String(length=100), nullable=False),
    sa.Column('account_id', sa.String(length=100), nullable=False),
    sa.Column('app_id', sa.String(length=100), nullable=False),
    sa.Column('app_secret', sa.String(length=255), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'account_id', name='_user_account_id_uc')
    )
    op.create_table('wordpress_sites',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('site_name', sa.String(length=100), nullable=False),
    sa.Column('site_url', sa.String(length=255), nullable=False),
    sa.Column('username', sa.String(length=100), nullable=False),
    sa.Column('api_key', sa.String(length=255), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'site_url', name='_user_site_url_uc')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('wordpress_sites')
    op.drop_table('wechat_accounts')
    # ### end Alembic commands ###

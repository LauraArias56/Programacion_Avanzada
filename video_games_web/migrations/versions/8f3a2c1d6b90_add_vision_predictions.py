"""add vision predictions

Revision ID: 8f3a2c1d6b90
Revises: 25c7b86a78a4
Create Date: 2026-11-18 20:05:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '8f3a2c1d6b90'
down_revision = '25c7b86a78a4'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'vision_predictions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('label', sa.String(length=40), nullable=False),
        sa.Column('label_es', sa.String(length=40), nullable=False),
        sa.Column('confidence', sa.Numeric(precision=6, scale=4), nullable=False),
        sa.Column('top_k', sa.JSON(), nullable=False),
        sa.Column('source', sa.String(length=20), nullable=False),
        sa.Column('model_version', sa.String(length=60), nullable=False),
        sa.Column('request_id', sa.String(length=64), nullable=True),
        sa.Column('latency_ms', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('vision_predictions', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_vision_predictions_created_at'), ['created_at'], unique=False
        )
        batch_op.create_index(
            batch_op.f('ix_vision_predictions_label'), ['label'], unique=False
        )
        batch_op.create_index(
            batch_op.f('ix_vision_predictions_label_es'), ['label_es'], unique=False
        )
        batch_op.create_index(
            batch_op.f('ix_vision_predictions_user_id'), ['user_id'], unique=False
        )


def downgrade():
    with op.batch_alter_table('vision_predictions', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_vision_predictions_user_id'))
        batch_op.drop_index(batch_op.f('ix_vision_predictions_label_es'))
        batch_op.drop_index(batch_op.f('ix_vision_predictions_label'))
        batch_op.drop_index(batch_op.f('ix_vision_predictions_created_at'))

    op.drop_table('vision_predictions')

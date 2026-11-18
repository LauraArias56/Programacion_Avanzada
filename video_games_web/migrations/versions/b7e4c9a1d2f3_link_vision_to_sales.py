"""link vision predictions with sales predictions

Revision ID: b7e4c9a1d2f3
Revises: 8f3a2c1d6b90
Create Date: 2026-11-18 22:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'b7e4c9a1d2f3'
down_revision = '8f3a2c1d6b90'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('vision_predictions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('theme', sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column('prediction_id', sa.Integer(), nullable=True))
        batch_op.create_index(
            batch_op.f('ix_vision_predictions_prediction_id'),
            ['prediction_id'],
            unique=False,
        )
        batch_op.create_unique_constraint(
            'uq_vision_predictions_prediction_id', ['prediction_id']
        )
        batch_op.create_foreign_key(
            'fk_vision_predictions_prediction_id',
            'predictions',
            ['prediction_id'],
            ['id'],
            ondelete='SET NULL',
        )


def downgrade():
    with op.batch_alter_table('vision_predictions', schema=None) as batch_op:
        batch_op.drop_constraint(
            'fk_vision_predictions_prediction_id', type_='foreignkey'
        )
        batch_op.drop_constraint(
            'uq_vision_predictions_prediction_id', type_='unique'
        )
        batch_op.drop_index(batch_op.f('ix_vision_predictions_prediction_id'))
        batch_op.drop_column('prediction_id')
        batch_op.drop_column('theme')

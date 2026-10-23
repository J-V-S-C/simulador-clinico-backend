"""Store one optional experience response per completed attempt."""
from alembic import op
import sqlalchemy as sa

revision = "c8a12f9e2d34"
down_revision = "b6dd5a8bb57b"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "experience_feedback",
        sa.Column("simulation_id", sa.String(36), sa.ForeignKey("simulations.id"), primary_key=True),
        sa.Column("liked", sa.Boolean(), nullable=False),
        sa.Column("clarity", sa.Integer(), nullable=False),
        sa.Column("difficulty", sa.Integer(), nullable=False),
        sa.Column("useful_feature", sa.String(1000), nullable=False),
        sa.Column("improvement", sa.String(1000), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade():
    op.drop_table("experience_feedback")

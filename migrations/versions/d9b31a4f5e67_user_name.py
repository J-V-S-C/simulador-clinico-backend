"""Add optional display name to existing accounts."""
from alembic import op
import sqlalchemy as sa

revision = "d9b31a4f5e67"
down_revision = "c8a12f9e2d34"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("name", sa.String(100), nullable=True))


def downgrade():
    op.drop_column("users", "name")

"""Store revocable admin sessions separately from student sessions."""
from alembic import op
import sqlalchemy as sa

revision = "e2c65f1b8a90"
down_revision = "d9b31a4f5e67"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("admin_tokens", sa.Column("hash", sa.String(64), primary_key=True),
                    sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False))


def downgrade():
    op.drop_table("admin_tokens")

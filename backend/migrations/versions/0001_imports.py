"""imports table (first schema)

Revision ID: 0001
Revises:
"""
import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    if "imports" in sa.inspect(op.get_bind()).get_table_names():
        return  # database created by the prototype's create_all: already in this shape
    op.create_table(
        "imports",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("customer_id", sa.String(64), nullable=False, index=True),
        sa.Column("plugin", sa.String(64), nullable=False),
        sa.Column("created_by", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("drawing_name", sa.String(255), nullable=False),
        sa.Column("bom_name", sa.String(255), nullable=False),
        sa.Column("part_number", sa.String(64), nullable=True),
        sa.Column("errors", sa.Integer, nullable=False),
        sa.Column("warnings", sa.Integer, nullable=False),
        sa.Column("model", sa.JSON, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("imports")

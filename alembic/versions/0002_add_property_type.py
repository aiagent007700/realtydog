"""Add parcels.property_type (canonical classification, for querying by type).

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-03
"""
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE parcels ADD COLUMN IF NOT EXISTS property_type TEXT")
    op.execute("CREATE INDEX IF NOT EXISTS idx_parcels_property_type ON parcels(property_type)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_parcels_property_type")
    op.execute("ALTER TABLE parcels DROP COLUMN IF EXISTS property_type")

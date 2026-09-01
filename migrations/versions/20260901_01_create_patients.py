"""Create patients table.

Revision ID: 20260901_01
Revises:
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260901_01"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "patients",
        sa.Column("patient_id", sa.Uuid(), nullable=False),
        sa.Column("first_name", sa.String(length=50), nullable=False),
        sa.Column("last_name", sa.String(length=50), nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=False),
        sa.Column(
            "sex",
            sa.Enum(
                "Male",
                "Female",
                "Other",
                "Decline to Answer",
                name="patient_sex",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("phone_number", sa.String(length=10), nullable=False),
        sa.Column("address_line_1", sa.String(length=255), nullable=False),
        sa.Column("address_line_2", sa.String(length=255), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=False),
        sa.Column("state", sa.String(length=2), nullable=False),
        sa.Column("zip_code", sa.String(length=10), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=True),
        sa.Column("insurance_provider", sa.String(length=150), nullable=True),
        sa.Column("insurance_member_id", sa.String(length=100), nullable=True),
        sa.Column(
            "preferred_language",
            sa.String(length=100),
            server_default="English",
            nullable=False,
        ),
        sa.Column("emergency_contact_name", sa.String(length=150), nullable=True),
        sa.Column("emergency_contact_phone", sa.String(length=10), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("patient_id"),
    )
    op.create_index("ix_patients_date_of_birth", "patients", ["date_of_birth"])
    op.create_index("ix_patients_last_name", "patients", ["last_name"])
    op.create_index("ix_patients_phone_number", "patients", ["phone_number"])


def downgrade() -> None:
    op.drop_index("ix_patients_phone_number", table_name="patients")
    op.drop_index("ix_patients_last_name", table_name="patients")
    op.drop_index("ix_patients_date_of_birth", table_name="patients")
    op.drop_table("patients")

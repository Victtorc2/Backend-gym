"""fase_6_clientes_diarios

Revision ID: 001_daily_clients
Revises:
Create Date: 2026-05-17

Crea las tablas del módulo Clientes Diarios (Fase 6):
  - clientes_diarios
  - pagos_diarios
  - ingresos_diarios
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001_daily_clients"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── clientes_diarios ───────────────────────────────────────────────────────
    op.create_table(
        "clientes_diarios",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("nombre", sa.String(length=200), nullable=False),
        sa.Column("documento", sa.String(length=20), nullable=True),
        sa.Column(
            "estado",
            sa.Enum("activo", "inactivo", name="daily_client_estado_enum"),
            nullable=False,
            server_default="activo",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("documento"),
    )
    op.create_index("ix_clientes_diarios_id", "clientes_diarios", ["id"], unique=False)
    op.create_index(
        "ix_clientes_diarios_documento", "clientes_diarios", ["documento"], unique=True
    )
    op.create_index(
        "ix_clientes_diarios_estado", "clientes_diarios", ["estado"], unique=False
    )

    # ── pagos_diarios ──────────────────────────────────────────────────────────
    op.create_table(
        "pagos_diarios",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("cliente_id", sa.Integer(), nullable=False),
        sa.Column("monto", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("fecha_pago", sa.Date(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["cliente_id"],
            ["clientes_diarios.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pagos_diarios_id", "pagos_diarios", ["id"], unique=False)
    op.create_index(
        "ix_pagos_diarios_cliente_id", "pagos_diarios", ["cliente_id"], unique=False
    )
    op.create_index(
        "ix_pagos_diarios_fecha_pago", "pagos_diarios", ["fecha_pago"], unique=False
    )

    # ── ingresos_diarios ───────────────────────────────────────────────────────
    op.create_table(
        "ingresos_diarios",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("cliente_id", sa.Integer(), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("hora", sa.Time(), nullable=False),
        sa.Column(
            "estado",
            sa.Enum("aprobado", "denegado", name="daily_ingreso_status_enum"),
            nullable=False,
        ),
        sa.Column("motivo", sa.String(length=300), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["cliente_id"],
            ["clientes_diarios.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ingresos_diarios_id", "ingresos_diarios", ["id"], unique=False)
    op.create_index(
        "ix_ingresos_diarios_cliente_id",
        "ingresos_diarios",
        ["cliente_id"],
        unique=False,
    )
    op.create_index(
        "ix_ingresos_diarios_fecha", "ingresos_diarios", ["fecha"], unique=False
    )
    op.create_index(
        "ix_ingresos_diarios_estado", "ingresos_diarios", ["estado"], unique=False
    )


def downgrade() -> None:
    op.drop_table("ingresos_diarios")
    op.drop_table("pagos_diarios")
    op.drop_table("clientes_diarios")
    op.execute("DROP TYPE IF EXISTS daily_ingreso_status_enum")
    op.execute("DROP TYPE IF EXISTS daily_client_estado_enum")

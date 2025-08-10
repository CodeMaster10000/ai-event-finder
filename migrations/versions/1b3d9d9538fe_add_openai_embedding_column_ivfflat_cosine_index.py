"""Add openai_embedding column + IVFFlat L2 index

Revision ID: 1b3d9d9538fe
Revises: b53c7fb4833a
Create Date: 2025-08-07 15:48:58.866155
"""
from alembic import op
import sqlalchemy as sa
import pgvector.sqlalchemy

# revision identifiers, used by Alembic.
revision = '1b3d9d9538fe'
down_revision = 'b53c7fb4833a'
branch_labels = None
depends_on = None


def upgrade():
    # Ensure pgvector is available
    op.execute('CREATE EXTENSION IF NOT EXISTS "vector";')

    # 1024-dim embedding column
    op.add_column(
        'events',
        sa.Column('openai_embedding', pgvector.sqlalchemy.Vector(1024), nullable=True)
    )

    # IVFFlat index for **Euclidean (L2)** distance only
    op.execute("""
        DO $$
        BEGIN
          IF NOT EXISTS (
            SELECT 1
            FROM   pg_class c
            JOIN   pg_namespace n ON n.oid = c.relnamespace
            WHERE  c.relname = 'idx_events_openai_embedding_l2'
              AND n.nspname = 'public'
          ) THEN
            CREATE INDEX idx_events_openai_embedding_l2
            ON events USING ivfflat (openai_embedding vector_l2_ops)
            WITH (lists = 100);
          END IF;
        END
        $$;
    """)


def downgrade():
    op.execute('DROP INDEX IF EXISTS idx_events_openai_embedding_l2;')
    op.drop_column('events', 'openai_embedding')

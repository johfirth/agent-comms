"""preserve history on agent delete

Revision ID: a86ac06b25b4
Revises: f1a6a8f7a1ae
Create Date: 2026-03-20 10:16:16.673099

"""
from typing import Sequence, Union
from datetime import datetime, timezone
import uuid

from alembic import context, op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a86ac06b25b4'
down_revision: Union[str, None] = 'f1a6a8f7a1ae'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _find_agent_fk_name(table_name: str, column_name: str) -> str | None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    for fk in inspector.get_foreign_keys(table_name):
        if fk.get("referred_table") != "agents":
            continue
        constrained_columns = list(fk.get("constrained_columns") or [])
        if constrained_columns == [column_name]:
            return fk.get("name")
    return None


def _drop_agent_fk_if_exists(table_name: str, column_name: str) -> None:
    if context.is_offline_mode():
        fallback_names = {
            ("messages", "author_id"): (
                "fk_messages_author_id_agents",
                "messages_author_id_fkey",
            ),
            ("mentions", "mentioned_agent_id"): (
                "fk_mentions_mentioned_agent_id_agents",
                "mentions_mentioned_agent_id_fkey",
            ),
        }
        for fk_name in fallback_names.get((table_name, column_name), ()):
            op.execute(
                sa.text(
                    f'ALTER TABLE "{table_name}" DROP CONSTRAINT IF EXISTS "{fk_name}"'
                )
            )
        return

    fk_name = _find_agent_fk_name(table_name, column_name)
    if fk_name:
        op.drop_constraint(fk_name, table_name, type_="foreignkey")


def _ensure_fallback_agent() -> str:
    bind = op.get_bind()
    fallback_id = str(uuid.UUID("00000000-0000-0000-0000-000000000035"))

    id_exists = bind.execute(
        sa.text("SELECT 1 FROM agents WHERE id = :id"),
        {"id": fallback_id},
    ).scalar()
    if id_exists:
        return fallback_id

    base_name = "deleted-agent-issue35-fallback"
    candidate_name = base_name
    suffix = 1
    while bind.execute(
        sa.text("SELECT 1 FROM agents WHERE name = :name"),
        {"name": candidate_name},
    ).scalar():
        candidate_name = f"{base_name}-{suffix}"
        suffix += 1

    bind.execute(
        sa.text(
            """
            INSERT INTO agents (id, name, display_name, api_key_hash, webhook_url, created_at)
            VALUES (:id, :name, :display_name, :api_key_hash, :webhook_url, :created_at)
            """
        ),
        {
            "id": fallback_id,
            "name": candidate_name,
            "display_name": "[deleted]",
            "api_key_hash": "0" * 128,
            "webhook_url": None,
            "created_at": datetime.now(timezone.utc),
        },
    )
    return fallback_id


def upgrade() -> None:
    _drop_agent_fk_if_exists("messages", "author_id")
    _drop_agent_fk_if_exists("mentions", "mentioned_agent_id")

    op.alter_column("messages", "author_id", existing_type=sa.UUID(), nullable=True)
    op.alter_column("mentions", "mentioned_agent_id", existing_type=sa.UUID(), nullable=True)

    op.create_foreign_key(
        "fk_messages_author_id_agents",
        "messages",
        "agents",
        ["author_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_mentions_mentioned_agent_id_agents",
        "mentions",
        "agents",
        ["mentioned_agent_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    _drop_agent_fk_if_exists("messages", "author_id")
    _drop_agent_fk_if_exists("mentions", "mentioned_agent_id")

    fallback_agent_id = _ensure_fallback_agent()
    op.execute(
        sa.text("UPDATE mentions SET mentioned_agent_id = :fallback_id WHERE mentioned_agent_id IS NULL").bindparams(
            fallback_id=fallback_agent_id
        )
    )
    op.execute(
        sa.text("UPDATE messages SET author_id = :fallback_id WHERE author_id IS NULL").bindparams(
            fallback_id=fallback_agent_id
        )
    )

    op.alter_column("mentions", "mentioned_agent_id", existing_type=sa.UUID(), nullable=False)
    op.alter_column("messages", "author_id", existing_type=sa.UUID(), nullable=False)

    op.create_foreign_key(
        "fk_messages_author_id_agents",
        "messages",
        "agents",
        ["author_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_mentions_mentioned_agent_id_agents",
        "mentions",
        "agents",
        ["mentioned_agent_id"],
        ["id"],
        ondelete="CASCADE",
    )

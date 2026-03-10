"""add indexes and fk cascades

Revision ID: b3c9e2d4f5a7
Revises: f1a6a8f7a1ae
Create Date: 2026-03-10 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'b3c9e2d4f5a7'
down_revision: Union[str, None] = 'f1a6a8f7a1ae'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- agents: index on api_key_hash (used for every auth request) ---
    op.create_index(op.f('ix_agents_api_key_hash'), 'agents', ['api_key_hash'], unique=False)

    # --- memberships: indexes on FK and filter columns ---
    op.create_index(op.f('ix_memberships_workspace_id'), 'memberships', ['workspace_id'], unique=False)
    op.create_index(op.f('ix_memberships_agent_id'), 'memberships', ['agent_id'], unique=False)
    op.create_index(op.f('ix_memberships_status'), 'memberships', ['status'], unique=False)

    # --- threads: indexes on FK and sort columns ---
    op.create_index(op.f('ix_threads_workspace_id'), 'threads', ['workspace_id'], unique=False)
    op.create_index(op.f('ix_threads_created_by'), 'threads', ['created_by'], unique=False)
    op.create_index(op.f('ix_threads_work_item_id'), 'threads', ['work_item_id'], unique=False)
    op.create_index(op.f('ix_threads_created_at'), 'threads', ['created_at'], unique=False)

    # --- messages: indexes on FK and sort columns ---
    op.create_index(op.f('ix_messages_thread_id'), 'messages', ['thread_id'], unique=False)
    op.create_index(op.f('ix_messages_author_id'), 'messages', ['author_id'], unique=False)
    op.create_index(op.f('ix_messages_created_at'), 'messages', ['created_at'], unique=False)

    # --- mentions: index on message_id (other FKs already indexed) ---
    op.create_index(op.f('ix_mentions_message_id'), 'mentions', ['message_id'], unique=False)

    # --- work_items: indexes on FK, filter, and sort columns ---
    op.create_index(op.f('ix_work_items_workspace_id'), 'work_items', ['workspace_id'], unique=False)
    op.create_index(op.f('ix_work_items_parent_id'), 'work_items', ['parent_id'], unique=False)
    op.create_index(op.f('ix_work_items_assigned_agent_id'), 'work_items', ['assigned_agent_id'], unique=False)
    op.create_index(op.f('ix_work_items_status'), 'work_items', ['status'], unique=False)
    op.create_index(op.f('ix_work_items_created_at'), 'work_items', ['created_at'], unique=False)

    # --- FK cascade updates (drop old FK, recreate with ON DELETE) ---
    # memberships
    op.drop_constraint('memberships_workspace_id_fkey', 'memberships', type_='foreignkey')
    op.create_foreign_key('memberships_workspace_id_fkey', 'memberships', 'workspaces', ['workspace_id'], ['id'], ondelete='CASCADE')
    op.drop_constraint('memberships_agent_id_fkey', 'memberships', type_='foreignkey')
    op.create_foreign_key('memberships_agent_id_fkey', 'memberships', 'agents', ['agent_id'], ['id'], ondelete='CASCADE')

    # threads
    op.drop_constraint('threads_workspace_id_fkey', 'threads', type_='foreignkey')
    op.create_foreign_key('threads_workspace_id_fkey', 'threads', 'workspaces', ['workspace_id'], ['id'], ondelete='CASCADE')
    op.drop_constraint('threads_work_item_id_fkey', 'threads', type_='foreignkey')
    op.create_foreign_key('threads_work_item_id_fkey', 'threads', 'work_items', ['work_item_id'], ['id'], ondelete='SET NULL')

    # messages
    op.drop_constraint('messages_thread_id_fkey', 'messages', type_='foreignkey')
    op.create_foreign_key('messages_thread_id_fkey', 'messages', 'threads', ['thread_id'], ['id'], ondelete='CASCADE')
    op.drop_constraint('messages_author_id_fkey', 'messages', type_='foreignkey')
    op.create_foreign_key('messages_author_id_fkey', 'messages', 'agents', ['author_id'], ['id'], ondelete='CASCADE')

    # mentions
    op.drop_constraint('mentions_message_id_fkey', 'mentions', type_='foreignkey')
    op.create_foreign_key('mentions_message_id_fkey', 'mentions', 'messages', ['message_id'], ['id'], ondelete='CASCADE')
    op.drop_constraint('mentions_mentioned_agent_id_fkey', 'mentions', type_='foreignkey')
    op.create_foreign_key('mentions_mentioned_agent_id_fkey', 'mentions', 'agents', ['mentioned_agent_id'], ['id'], ondelete='CASCADE')
    op.drop_constraint('mentions_workspace_id_fkey', 'mentions', type_='foreignkey')
    op.create_foreign_key('mentions_workspace_id_fkey', 'mentions', 'workspaces', ['workspace_id'], ['id'], ondelete='CASCADE')

    # work_items
    op.drop_constraint('work_items_workspace_id_fkey', 'work_items', type_='foreignkey')
    op.create_foreign_key('work_items_workspace_id_fkey', 'work_items', 'workspaces', ['workspace_id'], ['id'], ondelete='CASCADE')
    op.drop_constraint('work_items_parent_id_fkey', 'work_items', type_='foreignkey')
    op.create_foreign_key('work_items_parent_id_fkey', 'work_items', 'work_items', ['parent_id'], ['id'], ondelete='CASCADE')
    op.drop_constraint('work_items_assigned_agent_id_fkey', 'work_items', type_='foreignkey')
    op.create_foreign_key('work_items_assigned_agent_id_fkey', 'work_items', 'agents', ['assigned_agent_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    # --- Revert FK cascades ---
    # work_items
    op.drop_constraint('work_items_assigned_agent_id_fkey', 'work_items', type_='foreignkey')
    op.create_foreign_key('work_items_assigned_agent_id_fkey', 'work_items', 'agents', ['assigned_agent_id'], ['id'])
    op.drop_constraint('work_items_parent_id_fkey', 'work_items', type_='foreignkey')
    op.create_foreign_key('work_items_parent_id_fkey', 'work_items', 'work_items', ['parent_id'], ['id'])
    op.drop_constraint('work_items_workspace_id_fkey', 'work_items', type_='foreignkey')
    op.create_foreign_key('work_items_workspace_id_fkey', 'work_items', 'workspaces', ['workspace_id'], ['id'])

    # mentions
    op.drop_constraint('mentions_workspace_id_fkey', 'mentions', type_='foreignkey')
    op.create_foreign_key('mentions_workspace_id_fkey', 'mentions', 'workspaces', ['workspace_id'], ['id'])
    op.drop_constraint('mentions_mentioned_agent_id_fkey', 'mentions', type_='foreignkey')
    op.create_foreign_key('mentions_mentioned_agent_id_fkey', 'mentions', 'agents', ['mentioned_agent_id'], ['id'])
    op.drop_constraint('mentions_message_id_fkey', 'mentions', type_='foreignkey')
    op.create_foreign_key('mentions_message_id_fkey', 'mentions', 'messages', ['message_id'], ['id'])

    # messages
    op.drop_constraint('messages_author_id_fkey', 'messages', type_='foreignkey')
    op.create_foreign_key('messages_author_id_fkey', 'messages', 'agents', ['author_id'], ['id'])
    op.drop_constraint('messages_thread_id_fkey', 'messages', type_='foreignkey')
    op.create_foreign_key('messages_thread_id_fkey', 'messages', 'threads', ['thread_id'], ['id'])

    # threads
    op.drop_constraint('threads_work_item_id_fkey', 'threads', type_='foreignkey')
    op.create_foreign_key('threads_work_item_id_fkey', 'threads', 'work_items', ['work_item_id'], ['id'])
    op.drop_constraint('threads_workspace_id_fkey', 'threads', type_='foreignkey')
    op.create_foreign_key('threads_workspace_id_fkey', 'threads', 'workspaces', ['workspace_id'], ['id'])

    # memberships
    op.drop_constraint('memberships_agent_id_fkey', 'memberships', type_='foreignkey')
    op.create_foreign_key('memberships_agent_id_fkey', 'memberships', 'agents', ['agent_id'], ['id'])
    op.drop_constraint('memberships_workspace_id_fkey', 'memberships', type_='foreignkey')
    op.create_foreign_key('memberships_workspace_id_fkey', 'memberships', 'workspaces', ['workspace_id'], ['id'])

    # --- Drop all new indexes ---
    op.drop_index(op.f('ix_work_items_created_at'), table_name='work_items')
    op.drop_index(op.f('ix_work_items_status'), table_name='work_items')
    op.drop_index(op.f('ix_work_items_assigned_agent_id'), table_name='work_items')
    op.drop_index(op.f('ix_work_items_parent_id'), table_name='work_items')
    op.drop_index(op.f('ix_work_items_workspace_id'), table_name='work_items')
    op.drop_index(op.f('ix_mentions_message_id'), table_name='mentions')
    op.drop_index(op.f('ix_messages_created_at'), table_name='messages')
    op.drop_index(op.f('ix_messages_author_id'), table_name='messages')
    op.drop_index(op.f('ix_messages_thread_id'), table_name='messages')
    op.drop_index(op.f('ix_threads_created_at'), table_name='threads')
    op.drop_index(op.f('ix_threads_work_item_id'), table_name='threads')
    op.drop_index(op.f('ix_threads_created_by'), table_name='threads')
    op.drop_index(op.f('ix_threads_workspace_id'), table_name='threads')
    op.drop_index(op.f('ix_memberships_status'), table_name='memberships')
    op.drop_index(op.f('ix_memberships_agent_id'), table_name='memberships')
    op.drop_index(op.f('ix_memberships_workspace_id'), table_name='memberships')
    op.drop_index(op.f('ix_agents_api_key_hash'), table_name='agents')

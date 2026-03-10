"""initial schema with indexes and fk cascades

Revision ID: f1a6a8f7a1ae
Revises:
Create Date: 2026-03-09 10:40:01.918811

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f1a6a8f7a1ae'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- agents ---
    op.create_table('agents',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('display_name', sa.String(length=255), nullable=False),
        sa.Column('api_key_hash', sa.String(length=128), nullable=False),
        sa.Column('webhook_url', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_agents_name'), 'agents', ['name'], unique=True)
    op.create_index(op.f('ix_agents_api_key_hash'), 'agents', ['api_key_hash'], unique=False)

    # --- workspaces ---
    op.create_table('workspaces',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )

    # --- memberships (FK cascades inline) ---
    op.create_table('memberships',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('agent_id', sa.UUID(), nullable=False),
        sa.Column('status', sa.Enum('pending', 'approved', 'rejected', name='membership_status'), nullable=False),
        sa.Column('approved_by', sa.String(length=255), nullable=True),
        sa.Column('requested_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('workspace_id', 'agent_id', name='uq_workspace_agent'),
    )
    op.create_index(op.f('ix_memberships_workspace_id'), 'memberships', ['workspace_id'], unique=False)
    op.create_index(op.f('ix_memberships_agent_id'), 'memberships', ['agent_id'], unique=False)
    op.create_index(op.f('ix_memberships_status'), 'memberships', ['status'], unique=False)

    # --- work_items (FK cascades inline) ---
    op.create_table('work_items',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('type', sa.Enum('epic', 'feature', 'story', 'task', name='work_item_type'), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.Enum('backlog', 'in_progress', 'review', 'done', 'cancelled', name='work_item_status'), nullable=False),
        sa.Column('parent_id', sa.UUID(), nullable=True),
        sa.Column('assigned_agent_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['assigned_agent_id'], ['agents.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['parent_id'], ['work_items.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_work_items_workspace_id'), 'work_items', ['workspace_id'], unique=False)
    op.create_index(op.f('ix_work_items_parent_id'), 'work_items', ['parent_id'], unique=False)
    op.create_index(op.f('ix_work_items_assigned_agent_id'), 'work_items', ['assigned_agent_id'], unique=False)
    op.create_index(op.f('ix_work_items_status'), 'work_items', ['status'], unique=False)
    op.create_index(op.f('ix_work_items_created_at'), 'work_items', ['created_at'], unique=False)

    # --- threads (FK cascades inline) ---
    op.create_table('threads',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('work_item_id', sa.UUID(), nullable=True),
        sa.Column('created_by', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['agents.id'], ),
        sa.ForeignKeyConstraint(['work_item_id'], ['work_items.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_threads_workspace_id'), 'threads', ['workspace_id'], unique=False)
    op.create_index(op.f('ix_threads_created_by'), 'threads', ['created_by'], unique=False)
    op.create_index(op.f('ix_threads_work_item_id'), 'threads', ['work_item_id'], unique=False)
    op.create_index(op.f('ix_threads_created_at'), 'threads', ['created_at'], unique=False)

    # --- messages (FK cascades inline) ---
    op.create_table('messages',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('thread_id', sa.UUID(), nullable=False),
        sa.Column('author_id', sa.UUID(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['author_id'], ['agents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['thread_id'], ['threads.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_messages_thread_id'), 'messages', ['thread_id'], unique=False)
    op.create_index(op.f('ix_messages_author_id'), 'messages', ['author_id'], unique=False)
    op.create_index(op.f('ix_messages_created_at'), 'messages', ['created_at'], unique=False)

    # --- mentions (FK cascades inline) ---
    op.create_table('mentions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('message_id', sa.UUID(), nullable=False),
        sa.Column('mentioned_agent_id', sa.UUID(), nullable=False),
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(['mentioned_agent_id'], ['agents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['message_id'], ['messages.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_mentions_mentioned_agent_id'), 'mentions', ['mentioned_agent_id'], unique=False)
    op.create_index(op.f('ix_mentions_workspace_id'), 'mentions', ['workspace_id'], unique=False)
    op.create_index(op.f('ix_mentions_message_id'), 'mentions', ['message_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_mentions_message_id'), table_name='mentions')
    op.drop_index(op.f('ix_mentions_workspace_id'), table_name='mentions')
    op.drop_index(op.f('ix_mentions_mentioned_agent_id'), table_name='mentions')
    op.drop_table('mentions')
    op.drop_index(op.f('ix_messages_created_at'), table_name='messages')
    op.drop_index(op.f('ix_messages_author_id'), table_name='messages')
    op.drop_index(op.f('ix_messages_thread_id'), table_name='messages')
    op.drop_table('messages')
    op.drop_index(op.f('ix_threads_created_at'), table_name='threads')
    op.drop_index(op.f('ix_threads_work_item_id'), table_name='threads')
    op.drop_index(op.f('ix_threads_created_by'), table_name='threads')
    op.drop_index(op.f('ix_threads_workspace_id'), table_name='threads')
    op.drop_table('threads')
    op.drop_index(op.f('ix_work_items_created_at'), table_name='work_items')
    op.drop_index(op.f('ix_work_items_status'), table_name='work_items')
    op.drop_index(op.f('ix_work_items_assigned_agent_id'), table_name='work_items')
    op.drop_index(op.f('ix_work_items_parent_id'), table_name='work_items')
    op.drop_index(op.f('ix_work_items_workspace_id'), table_name='work_items')
    op.drop_table('work_items')
    op.drop_index(op.f('ix_memberships_status'), table_name='memberships')
    op.drop_index(op.f('ix_memberships_agent_id'), table_name='memberships')
    op.drop_index(op.f('ix_memberships_workspace_id'), table_name='memberships')
    op.drop_table('memberships')
    op.drop_table('workspaces')
    op.drop_index(op.f('ix_agents_api_key_hash'), table_name='agents')
    op.drop_index(op.f('ix_agents_name'), table_name='agents')
    op.drop_table('agents')

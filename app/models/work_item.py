import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class WorkItemType(str, enum.Enum):
    epic = "epic"
    feature = "feature"
    story = "story"
    task = "task"


class WorkItemStatus(str, enum.Enum):
    backlog = "backlog"
    in_progress = "in_progress"
    review = "review"
    done = "done"
    cancelled = "cancelled"


# Valid parent → child relationships
HIERARCHY_RULES: dict[WorkItemType, WorkItemType | None] = {
    WorkItemType.epic: None,
    WorkItemType.feature: WorkItemType.epic,
    WorkItemType.story: WorkItemType.feature,
    WorkItemType.task: WorkItemType.story,
}


class WorkItem(Base):
    __tablename__ = "work_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[WorkItemType] = mapped_column(Enum(WorkItemType, name="work_item_type"), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[WorkItemStatus] = mapped_column(
        Enum(WorkItemStatus, name="work_item_status"), default=WorkItemStatus.backlog, index=True
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("work_items.id", ondelete="CASCADE"), nullable=True, index=True
    )
    assigned_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)

    workspace = relationship("Workspace", back_populates="work_items")
    parent = relationship("WorkItem", remote_side="WorkItem.id", back_populates="children")
    children = relationship("WorkItem", back_populates="parent", cascade="all, delete-orphan")
    assigned_agent = relationship("Agent", foreign_keys=[assigned_agent_id])
    threads = relationship("Thread", back_populates="work_item")

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class AnalyticsReport(SQLModel, table=True):
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    space_id: UUID = Field(foreign_key="space.id", index=True)
    room_id: Optional[UUID] = Field(default=None, index=True)  # None means space-level report

    content: str  # Markdown report
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Metadata for what triggered it or type
    report_type: str = Field(default="general")  # general, participation, sentiment

    # Backward compat property
    @property
    def course_id(self) -> UUID:
        return self.space_id

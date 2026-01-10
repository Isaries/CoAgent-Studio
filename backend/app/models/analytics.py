from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class AnalyticsReport(SQLModel, table=True):
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    course_id: UUID = Field(foreign_key="course.id", index=True)
    room_id: Optional[UUID] = Field(default=None, index=True)  # None means course-level report

    content: str  # Markdown report
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Metadata for what triggered it or type
    report_type: str = Field(default="general")  # general, participation, sentiment

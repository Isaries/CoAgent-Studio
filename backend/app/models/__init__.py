from .agent_config import AgentConfig, AgentConfigCreate, AgentConfigRead, AgentType, AgentCategory
from .agent_key import AgentKey
from .agent_type_metadata import AgentTypeMetadata, AgentTypeMetadataRead, AgentTypeMetadataCreate
from .analytics import AnalyticsReport
from .announcement import Announcement, AnnouncementCreate, AnnouncementRead
from .course import Course, CourseCreate, CourseRead, CourseUpdate, UserCourseLink
from .message import Message, MessageCreate, MessageRead
from .room import Room, RoomCreate, RoomRead, RoomUpdate
from .user import User, UserCreate, UserRead, UserRole, UserUpdate
from .user_api_key import UserAPIKey, UserAPIKeyCreate, UserAPIKeyRead

# Import A2A models to ensure table creation
from app.core.a2a.store import A2AMessageRecord

__all__ = [
    "AgentConfig",
    "AgentConfigCreate",
    "AgentConfigRead",
    "AgentType",
    "AgentCategory",
    "AgentKey",
    "AgentTypeMetadata",
    "AgentTypeMetadataRead",
    "AgentTypeMetadataCreate",
    "AnalyticsReport",
    "Announcement",
    "AnnouncementCreate",
    "AnnouncementRead",
    "Course",
    "CourseCreate",
    "CourseRead",
    "CourseUpdate",
    "UserCourseLink",
    "Message",
    "MessageCreate",
    "MessageRead",
    "Room",
    "RoomCreate",
    "RoomRead",
    "RoomUpdate",
    "User",
    "UserCreate",
    "UserRead",
    "UserRole",
    "UserUpdate",
    "UserAPIKey",
    "UserAPIKeyCreate",
    "UserAPIKeyRead",
    "A2AMessageRecord",  # Ensure A2A table is created
]


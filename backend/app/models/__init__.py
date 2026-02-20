from .agent_config import AgentConfig, AgentConfigCreate, AgentConfigRead, AgentType, AgentCategory
from .agent_key import AgentKey
from .agent_type_metadata import AgentTypeMetadata, AgentTypeMetadataRead, AgentTypeMetadataCreate
from .analytics import AnalyticsReport
from .announcement import Announcement, AnnouncementCreate, AnnouncementRead
from .artifact import Artifact, ArtifactCreate, ArtifactRead, ArtifactUpdate, ArtifactType, AgentCapability
from .course import Course, CourseCreate, CourseRead, CourseUpdate, UserCourseLink
from .message import Message, MessageCreate, MessageRead
from .organization import Organization, OrganizationCreate, OrganizationRead, OrganizationUpdate, UserOrganizationLink
from .project import Project, ProjectCreate, ProjectRead, ProjectUpdate, UserProjectLink
from .room import Room, RoomCreate, RoomRead, RoomUpdate, UserRoomLink, RoomAgentLink
from .thread import AgentThread, AgentThreadCreate, AgentThreadRead, ThreadMessage, ThreadMessageCreate, ThreadMessageRead
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
    "Artifact",
    "ArtifactCreate",
    "ArtifactRead",
    "ArtifactUpdate",
    "ArtifactType",
    "AgentCapability",
    "Course",
    "CourseCreate",
    "CourseRead",
    "CourseUpdate",
    "UserCourseLink",
    "Message",
    "MessageCreate",
    "MessageRead",
    "Organization",
    "OrganizationCreate",
    "OrganizationRead",
    "OrganizationUpdate",
    "UserOrganizationLink",
    "Project",
    "ProjectCreate",
    "ProjectRead",
    "ProjectUpdate",
    "UserProjectLink",
    "Room",
    "RoomCreate",
    "RoomRead",
    "RoomUpdate",
    "UserRoomLink",
    "RoomAgentLink",
    "AgentThread",
    "AgentThreadCreate",
    "AgentThreadRead",
    "ThreadMessage",
    "ThreadMessageCreate",
    "ThreadMessageRead",
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



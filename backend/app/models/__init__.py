# Import A2A models to ensure table creation
from app.core.a2a.store import A2AMessageRecord

from .agent_config import AgentCategory, AgentConfig, AgentConfigCreate, AgentConfigRead, AgentType
from .agent_key import AgentKey
from .agent_room_state import AgentRoomState
from .agent_type_metadata import AgentTypeMetadata, AgentTypeMetadataCreate, AgentTypeMetadataRead
from .analytics import AnalyticsReport
from .announcement import Announcement, AnnouncementCreate, AnnouncementRead
from .artifact import (
    AgentCapability,
    Artifact,
    ArtifactCreate,
    ArtifactRead,
    ArtifactType,
    ArtifactUpdate,
)
from .audit_log import AuditLog

# Backward compatibility aliases (Course → Space)
from .course import (
    Course,
    CourseCreate,
    CourseMember,
    CourseMemberUpdate,
    CourseRead,
    CourseUpdate,
    UserCourseLink,
)
from .knowledge_base import KBCreate, KBRead, KBUpdate, KnowledgeBase
from .message import Message, MessageCreate, MessageRead
from .organization import (
    Organization,
    OrganizationCreate,
    OrganizationRead,
    OrganizationUpdate,
    UserOrganizationLink,
)
from .project import Project, ProjectCreate, ProjectRead, ProjectUpdate, UserProjectLink
from .room import Room, RoomAgentLink, RoomCreate, RoomRead, RoomUpdate, UserRoomLink
from .space import (
    Space,
    SpaceCreate,
    SpaceMember,
    SpaceMemberUpdate,
    SpaceRead,
    SpaceUpdate,
    UserSpaceLink,
)
from .thread import (
    AgentThread,
    AgentThreadCreate,
    AgentThreadRead,
    ThreadMessage,
    ThreadMessageCreate,
    ThreadMessageRead,
)
from .trigger import (
    TriggerEventType,
    TriggerPolicy,
    TriggerPolicyCreate,
    TriggerPolicyRead,
    TriggerPolicyUpdate,
)
from .user import User, UserCreate, UserRead, UserRole, UserUpdate
from .user_api_key import UserAPIKey, UserAPIKeyCreate, UserAPIKeyRead
from .workflow import (
    # Backward-compatible aliases
    RoomWorkflow,
    RoomWorkflowCreate,
    RoomWorkflowRead,
    RoomWorkflowUpdate,
    Workflow,
    WorkflowCreate,
    WorkflowRead,
    WorkflowRun,
    WorkflowRunRead,
    WorkflowStatus,
    WorkflowUpdate,
)

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
    # New canonical names
    "Space",
    "SpaceCreate",
    "SpaceRead",
    "SpaceUpdate",
    "SpaceMember",
    "SpaceMemberUpdate",
    "UserSpaceLink",
    # Backward compat aliases
    "Course",
    "CourseCreate",
    "CourseRead",
    "CourseUpdate",
    "CourseMember",
    "CourseMemberUpdate",
    "UserCourseLink",
    # Knowledge Base
    "KnowledgeBase",
    "KBCreate",
    "KBRead",
    "KBUpdate",
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
    "AgentRoomState",
    "AuditLog",
    "A2AMessageRecord",
    # Workflow Engine
    "Workflow",
    "WorkflowCreate",
    "WorkflowRead",
    "WorkflowUpdate",
    "WorkflowRun",
    "WorkflowRunRead",
    "WorkflowStatus",
    "RoomWorkflow",
    "RoomWorkflowCreate",
    "RoomWorkflowRead",
    "RoomWorkflowUpdate",
    # Trigger Policies
    "TriggerPolicy",
    "TriggerPolicyCreate",
    "TriggerPolicyRead",
    "TriggerPolicyUpdate",
    "TriggerEventType",
]

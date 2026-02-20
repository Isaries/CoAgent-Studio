export interface Organization {
    id: string
    name: string
    description?: string
    created_at: string
}

export interface Project {
    id: string
    organization_id: string
    name: string
    description?: string
    created_at: string
}

export interface UserOrganizationLink {
    user_id: string
    organization_id: string
    role: string
}

export interface UserProjectLink {
    user_id: string
    project_id: string
    role: string
}

export interface RoomAgentLink {
    room_id: string
    agent_id: string
}

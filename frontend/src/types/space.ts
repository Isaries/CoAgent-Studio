export interface Space {
  id: string
  title: string
  description: string
  owner_id: string
  owner_name?: string
  preset: string
  created_at: string
}

export interface Room {
  id: string
  name: string
  space_id: string
  is_ai_active: boolean
  ai_mode?: string
  ai_frequency?: number
  enabled_tabs?: Record<string, boolean>
  room_kb_id?: string
}

export interface SpaceMember {
  user_id: string
  email: string
  full_name?: string
  avatar_url?: string
  role: 'guest' | 'student' | 'ta' | 'teacher' | 'admin' | 'super_admin'
}

export interface Announcement {
  id: string
  space_id: string
  title: string
  content: string
  author_id: string
  created_at: string
}

export interface Course {
    id: string
    title: string
    description: string
    owner_id: string
}

export interface Room {
    id: string
    name: string
    course_id: string
    is_ai_active: boolean
    ai_mode?: string
    ai_frequency?: number
}

export interface CourseMember {
    user_id: string
    email: string
    full_name?: string
    avatar_url?: string
    role: 'student' | 'ta'
}

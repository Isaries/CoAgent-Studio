export interface User {
    id: string
    email: string
    username?: string
    full_name: string
    role: 'student' | 'teacher' | 'admin' | 'ta' | 'guest' | 'super_admin'
    is_active: boolean
    avatar_url?: string
}

export interface CreateUserPayload {
    email?: string
    username?: string
    password?: string
    full_name: string
    role: string
}

export interface UpdateUserPayload {
    full_name?: string
    role?: string
    password?: string
}

export enum UserRole {
    ADMIN = 'admin',
    SUPER_ADMIN = 'super_admin',
    TEACHER = 'teacher',
    TA = 'ta',
    STUDENT = 'student',
    GUEST = 'guest'
}

export enum AgentType {
    TEACHER = 'teacher',
    STUDENT = 'student',
    DESIGN = 'design',
    ANALYTICS = 'analytics'
}

export enum ModelProvider {
    GEMINI = 'gemini',
    OPENAI = 'openai'
}

export enum CalendarMode {
    NONE = 'none',
    RANGE_DAILY = 'range_daily',
    RANGE_WEEKLY = 'range_weekly'
}

export enum TriggerType {
    MESSAGE_COUNT = 'message_count',
    TIME_INTERVAL = 'time_interval',
    SILENCE = 'silence',
    MANUAL = 'manual'
}

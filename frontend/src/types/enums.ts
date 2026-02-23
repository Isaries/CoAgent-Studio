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

// Dynamic agent classification
export enum AgentCategory {
    INSTRUCTOR = 'instructor',
    PARTICIPANT = 'participant',
    UTILITY = 'utility',
    EXTERNAL = 'external'
}

export enum ModelProvider {
    GEMINI = 'gemini',
    OPENAI = 'openai'
}

// Legacy — kept for backward compatibility
export enum CalendarMode {
    NONE = 'none',
    RANGE_DAILY = 'range_daily',
    RANGE_WEEKLY = 'range_weekly'
}

// Legacy — kept for backward compatibility
export enum TriggerType {
    MESSAGE_COUNT = 'message_count',
    TIME_INTERVAL = 'time_interval',
    SILENCE = 'silence',
    MANUAL = 'manual'
}

// ============================================================
// New Scheduling & Triggering Enums
// ============================================================

export enum ScheduleMode {
    WHITELIST = 'whitelist',
    BLACKLIST = 'blacklist',
}

export enum ScheduleRuleType {
    EVERYDAY = 'everyday',
    SPECIFIC_DATE = 'specific_date',
    DAY_OF_WEEK = 'day_of_week',
}

export enum TriggerLogic {
    OR = 'or',
    AND = 'and',
}

export enum TriggerCondition {
    MESSAGE_COUNT = 'message_count',
    TIME_INTERVAL_MINS = 'time_interval_mins',
    USER_SILENT_MINS = 'user_silent_mins',
}

export enum CloseStrategy {
    NONE = 'none',
    AGENT_MONOLOGUE = 'agent_monologue',
    USER_TIMEOUT = 'user_timeout',
}

export enum ContextStrategyType {
    LAST_N = 'last_n',
    ALL = 'all',
}

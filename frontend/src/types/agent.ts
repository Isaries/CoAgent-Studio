export interface TriggerConfig {
  type: string
  value: number
}

export interface ScheduleRule {
  start_time: string
  end_time: string
  days?: number[]
}

export interface SpecificScheduleException {
  date: string
  start: string
  end: string
}

export interface GeneralSchedule {
  mode: 'none' | 'range_daily' | 'range_weekly'
  start_date?: string
  end_date?: string
  rules: ScheduleRule[]
}

export interface ScheduleConfig {
  specific: SpecificScheduleException[]
  general: GeneralSchedule
}

export interface AgentSettings {
  sync_schedule?: boolean
  [key: string]: any
}

export interface AgentKey {
  id: string
  key_type: string
  masked_key?: string
}

export interface AgentConfig {
  id: string
  name: string
  course_id: string
  type: 'teacher' | 'student' | 'design' | 'analytics'
  system_prompt: string
  model_provider: string
  model: string
  is_active: boolean
  context_window: number
  trigger_config: TriggerConfig
  schedule_config: ScheduleConfig
  settings?: AgentSettings
  created_by: string
  updated_at: string
  api_key?: string | null // For updates
  masked_api_key?: string // From read

  keys?: Record<string, string> // Mapped for UI convenience (type -> masked_key)
}

export interface GeneratePromptRequest {
  requirement: string
  target_agent_type: string
  course_context: string
  api_key?: string
  course_id?: string
  provider: string
}

export interface GeneratePromptResponse {
  generated_prompt: string
}

import { AgentType, CalendarMode, TriggerType } from './enums'

export interface TriggerConfig {
  type: TriggerType
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
  mode: CalendarMode
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
  [key: string]: unknown // Safer than any, forces type checking before use
}

// Consolidated AgentKey interface
export interface AgentKeys {
  room_key?: string
  global_key?: string
  backup_key?: string
  [key: string]: string | undefined
}

export interface AgentConfig {
  id: string
  name: string
  course_id: string
  type: AgentType
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

  // Sensitive Data
  api_key?: string | null
  masked_api_key?: string
  keys?: Record<string, string>
}

export interface AgentConfigVersion {
  id: string
  config_id: string
  version_label: string
  system_prompt: string
  model_provider: string
  model: string
  created_at: string
  created_by?: string
  settings?: Record<string, unknown>
}

export interface VersionCreate {
  version_label: string
}

export interface GeneratePromptRequest {
  requirement: string
  target_agent_type: string
  course_context: string
  api_key?: string
  course_id?: string
  provider: string

  // Sandbox extensions
  custom_system_prompt?: string
  custom_api_key?: string
  custom_provider?: string
  custom_model?: string
}

export interface GeneratePromptResponse {
  generated_prompt: string
}

export interface DesignDbState {
  requirement: string
  context: string
  loading: boolean
  refineCurrent: boolean
}

import { ref } from 'vue'
import type { ScheduleConfig, ScheduleRule } from '../types/agent'
import { ScheduleMode, ScheduleRuleType } from '../types/enums'

/**
 * Composable for managing the new ScheduleConfig structure.
 * Supports whitelist/blacklist mode and rule CRUD.
 */
export function useScheduleConfig(initialConfig?: ScheduleConfig | null) {
  const scheduleConfig = ref<ScheduleConfig>(
    initialConfig || {
      mode: ScheduleMode.WHITELIST,
      rules: [],
    }
  )

  const addRule = (type: ScheduleRuleType = ScheduleRuleType.EVERYDAY) => {
    const rule: ScheduleRule = { type, time_range: ['09:00', '17:00'] }

    if (type === ScheduleRuleType.DAY_OF_WEEK) {
      rule.days = [1, 3, 5] // Mon, Wed, Fri default
    }
    if (type === ScheduleRuleType.SPECIFIC_DATE) {
      rule.date = new Date().toISOString().split('T')[0]
    }

    scheduleConfig.value.rules.push(rule)
  }

  const removeRule = (idx: number) => {
    scheduleConfig.value.rules.splice(idx, 1)
  }

  const setMode = (mode: ScheduleMode) => {
    scheduleConfig.value.mode = mode
  }

  const reset = () => {
    scheduleConfig.value = { mode: ScheduleMode.WHITELIST, rules: [] }
  }

  const loadConfig = (config: ScheduleConfig | null | undefined) => {
    if (config) {
      scheduleConfig.value = JSON.parse(JSON.stringify(config))
    } else {
      reset()
    }
  }

  return {
    scheduleConfig,
    addRule,
    removeRule,
    setMode,
    reset,
    loadConfig,
  }
}

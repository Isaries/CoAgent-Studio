import { ref, watch, type Ref } from 'vue'
import type { ScheduleConfig, AgentConfig, ScheduleRule } from '../types/agent'

import { CalendarMode } from '../types/enums'

export function useScheduleConfig(
  activeTab: Ref<string>,
  activeTeacherConfig: Ref<AgentConfig | undefined>
) {
  const scheduleConfig = ref<ScheduleConfig>({
    specific: [],
    general: { mode: CalendarMode.NONE, rules: [] }
  })
  const syncSchedule = ref(false)

  // Helper for Schedule Rules
  const addSpecificDate = () => {
    if (syncSchedule.value) return
    scheduleConfig.value.specific.push({
      date: new Date().toISOString().split('T')[0] || '',
      start: '09:00',
      end: '17:00'
    })
  }
  const removeSpecificDate = (idx: number) => {
    if (syncSchedule.value) return
    scheduleConfig.value.specific.splice(idx, 1)
  }

  const addGeneralRule = () => {
    if (syncSchedule.value) return
    const r: ScheduleRule = { start_time: '09:00', end_time: '17:00', days: [] }
    if (scheduleConfig.value.general.mode === 'range_weekly') {
      r.days = [1, 3, 5] // Mon, Wed, Fri default
    }
    scheduleConfig.value.general.rules.push(r)
  }
  const removeGeneralRule = (idx: number) => {
    if (syncSchedule.value) return
    scheduleConfig.value.general.rules.splice(idx, 1)
  }

  // Watcher to ensure 'days' array exists when switching to Weekly mode
  watch(
    () => scheduleConfig.value.general.mode,
    (newMode) => {
      if (newMode === 'range_weekly') {
        scheduleConfig.value.general.rules.forEach((rule: ScheduleRule) => {
          if (!Array.isArray(rule.days)) {
            rule.days = []
          }
        })
      }
    }
  )

  // Sync Schedule Logic
  watch(syncSchedule, (newVal) => {
    if (newVal && activeTab.value === 'student' && activeTeacherConfig.value) {
      // Deep copy teacher schedule
      try {
        const teacherSch = activeTeacherConfig.value.schedule_config
        if (teacherSch) {
          scheduleConfig.value = JSON.parse(JSON.stringify(teacherSch))
        }
      } catch (e) {
        console.error('Sync error', e)
      }
    }
  })

  return {
    scheduleConfig,
    syncSchedule,
    addSpecificDate,
    removeSpecificDate,
    addGeneralRule,
    removeGeneralRule
  }
}

<script setup lang="ts">
import { ScheduleMode, ScheduleRuleType } from '../../types/enums'
import type { ScheduleConfig } from '../../types/agent'
import { useScheduleConfig } from '../../composables/useScheduleConfig'
import { watch } from 'vue'

const props = defineProps<{
  modelValue: ScheduleConfig | null | undefined
  label?: string
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', val: ScheduleConfig): void
}>()

const { scheduleConfig, addRule, removeRule, setMode, loadConfig } = useScheduleConfig(
  props.modelValue || undefined
)

// Sync from parent
watch(() => props.modelValue, (v) => loadConfig(v), { deep: true })

// Emit on change
watch(scheduleConfig, (v) => emit('update:modelValue', v), { deep: true })

const dayLabels = ['', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
</script>

<template>
  <div class="card bg-base-100 shadow-sm border border-base-200">
    <div class="card-body gap-4">
      <h3 class="card-title text-sm uppercase tracking-wide opacity-70">
        {{ label || 'Schedule Rules' }}
      </h3>

      <!-- Mode Toggle -->
      <div class="flex items-center gap-3">
        <span class="text-sm font-medium opacity-70">Mode</span>
        <div class="join">
          <button
            class="btn btn-sm join-item"
            :class="scheduleConfig.mode === ScheduleMode.WHITELIST ? 'btn-primary' : 'btn-ghost'"
            @click="setMode(ScheduleMode.WHITELIST)"
          >
            ✅ Whitelist
          </button>
          <button
            class="btn btn-sm join-item"
            :class="scheduleConfig.mode === ScheduleMode.BLACKLIST ? 'btn-error' : 'btn-ghost'"
            @click="setMode(ScheduleMode.BLACKLIST)"
          >
            ❌ Blacklist
          </button>
        </div>
        <span class="text-xs opacity-50">
          {{ scheduleConfig.mode === ScheduleMode.WHITELIST ? 'Only allow during these times' : 'Block during these times' }}
        </span>
      </div>

      <!-- Rules List -->
      <div v-if="scheduleConfig.rules.length === 0" class="text-sm opacity-50 py-2">
        No rules defined. Agent runs {{ scheduleConfig.mode === ScheduleMode.WHITELIST ? 'never' : 'always' }}.
      </div>

      <div v-for="(rule, idx) in scheduleConfig.rules" :key="idx" class="border rounded-lg p-3 bg-base-50 flex flex-col gap-2">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <span class="badge badge-sm badge-outline">{{ idx + 1 }}</span>
            <select v-model="rule.type" class="select select-bordered select-xs w-40">
              <option :value="ScheduleRuleType.EVERYDAY">Everyday</option>
              <option :value="ScheduleRuleType.SPECIFIC_DATE">Specific Date</option>
              <option :value="ScheduleRuleType.DAY_OF_WEEK">Day of Week</option>
            </select>
          </div>
          <button class="btn btn-ghost btn-xs text-error" @click="removeRule(idx)">✕</button>
        </div>

        <!-- Specific Date -->
        <div v-if="rule.type === ScheduleRuleType.SPECIFIC_DATE" class="form-control">
          <label class="label py-0"><span class="label-text text-xs">Date</span></label>
          <input type="date" v-model="rule.date" class="input input-bordered input-sm w-48" />
        </div>

        <!-- Day of Week -->
        <div v-if="rule.type === ScheduleRuleType.DAY_OF_WEEK" class="flex flex-wrap gap-1">
          <label
            v-for="d in 7" :key="d"
            class="btn btn-xs"
            :class="(rule.days || []).includes(d) ? 'btn-primary' : 'btn-ghost'"
          >
            <input
              type="checkbox"
              :value="d"
              v-model="rule.days"
              class="hidden"
            />
            {{ dayLabels[d] }}
          </label>
        </div>

        <!-- Time Range -->
        <div class="flex items-center gap-2">
          <label class="flex items-center gap-1 cursor-pointer">
            <input
              type="checkbox"
              class="checkbox checkbox-xs"
              :checked="rule.time_range !== null && rule.time_range !== undefined"
              @change="rule.time_range = ($event.target as HTMLInputElement).checked ? ['09:00', '17:00'] : null"
            />
            <span class="text-xs">Time range</span>
          </label>
          <template v-if="rule.time_range">
            <input type="time" v-model="rule.time_range[0]" class="input input-bordered input-xs w-28" />
            <span class="text-xs opacity-50">to</span>
            <input type="time" v-model="rule.time_range[1]" class="input input-bordered input-xs w-28" />
          </template>
          <span v-else class="text-xs opacity-40">All day</span>
        </div>
      </div>

      <!-- Add Rule -->
      <div class="flex gap-2">
        <button class="btn btn-sm btn-outline btn-primary" @click="addRule(ScheduleRuleType.EVERYDAY)">+ Everyday</button>
        <button class="btn btn-sm btn-outline" @click="addRule(ScheduleRuleType.DAY_OF_WEEK)">+ Weekly</button>
        <button class="btn btn-sm btn-outline" @click="addRule(ScheduleRuleType.SPECIFIC_DATE)">+ Date</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { TriggerLogic, TriggerCondition, CloseStrategy, ContextStrategyType } from '../../types/enums'
import type { TriggerConfig } from '../../types/agent'
import { useTriggerConfig } from '../../composables/useTriggerConfig'

const props = defineProps<{
  modelValue: TriggerConfig | null | undefined
  label?: string
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', val: TriggerConfig): void
}>()

const {
  triggerConfig,
  toggleCondition,
  isConditionEnabled,
  setLogic,
  loadConfig,
} = useTriggerConfig(props.modelValue || undefined)

// Flag to prevent infinite watcher loop between parent sync and child emit
const isLoadingFromParent = ref(false)

// Sync from parent
watch(() => props.modelValue, (v) => {
  isLoadingFromParent.value = true
  loadConfig(v)
  setTimeout(() => { isLoadingFromParent.value = false }, 0)
}, { deep: true })

// Emit on change — skip when loading from parent
watch(triggerConfig, (v) => {
  if (!isLoadingFromParent.value) {
    emit('update:modelValue', v)
  }
}, { deep: true })

const conditionLabels: Record<string, { label: string; unit: string; desc: string }> = {
  [TriggerCondition.MESSAGE_COUNT]: { label: 'Message Count', unit: 'messages', desc: 'Trigger after N user messages' },
  [TriggerCondition.TIME_INTERVAL_MINS]: { label: 'Time Interval', unit: 'mins', desc: 'Trigger every N minutes' },
  [TriggerCondition.USER_SILENT_MINS]: { label: 'User Silence', unit: 'mins', desc: 'Trigger after N minutes of user silence' },
}

const durationOptions = [
  { value: 0, label: 'Disabled' },
  { value: 1, label: '1 hour' },
  { value: 6, label: '6 hours' },
  { value: 24, label: '24 hours' },
  { value: -1, label: 'Permanent' },
]
</script>

<template>
  <div class="card bg-base-100 shadow-sm border border-base-200">
    <div class="card-body gap-5">
      <h3 class="card-title text-sm uppercase tracking-wide opacity-70">
        {{ label || 'Trigger & Behavior' }}
      </h3>

      <!-- ========== SECTION 1: Trigger Conditions ========== -->
      <div class="space-y-3">
        <div class="flex items-center justify-between">
          <span class="text-sm font-semibold">Trigger Conditions</span>
          <div class="join">
            <button
              class="btn btn-xs join-item"
              :class="triggerConfig.logic === TriggerLogic.OR ? 'btn-primary' : 'btn-ghost'"
              @click="setLogic(TriggerLogic.OR)"
            >OR</button>
            <button
              class="btn btn-xs join-item"
              :class="triggerConfig.logic === TriggerLogic.AND ? 'btn-primary' : 'btn-ghost'"
              @click="setLogic(TriggerLogic.AND)"
            >AND</button>
          </div>
        </div>

        <p class="text-xs opacity-50">
          Select which conditions to evaluate. {{ triggerConfig.logic === 'or' ? 'Agent speaks when ANY condition is met.' : 'Agent speaks when ALL conditions are met.' }}
        </p>

        <!-- Condition Checkboxes -->
        <div v-for="(info, key) in conditionLabels" :key="key" class="border rounded-lg p-3 bg-base-50">
          <label class="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              class="checkbox checkbox-primary checkbox-sm"
              :checked="isConditionEnabled(key as TriggerCondition)"
              @change="toggleCondition(key as TriggerCondition)"
            />
            <div class="flex-1">
              <span class="text-sm font-medium">{{ info.label }}</span>
              <p class="text-xs opacity-50">{{ info.desc }}</p>
            </div>
          </label>

          <!-- Value input when enabled -->
          <div v-if="isConditionEnabled(key as TriggerCondition)" class="mt-2 ml-8 flex items-center gap-2">
            <input
              type="number"
              v-model.number="(triggerConfig.trigger as any)[key]"
              class="input input-bordered input-sm w-24"
              :min="1"
            />
            <span class="text-xs opacity-60">{{ info.unit }}</span>
          </div>
        </div>
      </div>

      <!-- ========== SECTION 2: Context Strategy ========== -->
      <div class="divider text-xs opacity-50 my-0">CONTEXT WINDOW</div>
      <div class="flex items-center gap-3">
        <select v-model="triggerConfig.trigger.context_strategy.type" class="select select-bordered select-sm w-32">
          <option :value="ContextStrategyType.LAST_N">Last N</option>
          <option :value="ContextStrategyType.ALL">All</option>
        </select>
        <input
          v-if="triggerConfig.trigger.context_strategy.type === ContextStrategyType.LAST_N"
          type="number"
          v-model.number="triggerConfig.trigger.context_strategy.n"
          class="input input-bordered input-sm w-20"
          :min="1"
          :max="10000"
        />
        <span class="text-xs opacity-50">messages</span>
      </div>

      <!-- ========== SECTION 3: Close Strategy ========== -->
      <div class="divider text-xs opacity-50 my-0">CLOSE / SLEEP</div>
      <div class="space-y-2">
        <select v-model="triggerConfig.close.strategy" class="select select-bordered select-sm w-full">
          <option :value="CloseStrategy.NONE">None — agent never sleeps</option>
          <option :value="CloseStrategy.AGENT_MONOLOGUE">Agent Monologue — sleep after N consecutive replies</option>
          <option :value="CloseStrategy.USER_TIMEOUT">User Timeout — sleep if user doesn't reply in N mins</option>
        </select>

        <div v-if="triggerConfig.close.strategy === CloseStrategy.AGENT_MONOLOGUE" class="flex items-center gap-2 ml-2">
          <span class="text-xs">Max consecutive replies:</span>
          <input type="number" v-model.number="triggerConfig.close.monologue_limit" class="input input-bordered input-xs w-16" :min="1" />
        </div>

        <div v-if="triggerConfig.close.strategy === CloseStrategy.USER_TIMEOUT" class="flex items-center gap-2 ml-2">
          <span class="text-xs">Timeout:</span>
          <input type="number" v-model.number="triggerConfig.close.timeout_mins" class="input input-bordered input-xs w-16" :min="1" />
          <span class="text-xs opacity-60">mins</span>
        </div>
      </div>

      <!-- ========== SECTION 4: Self-Modification ========== -->
      <div class="divider text-xs opacity-50 my-0">AGENT SELF-MODIFICATION</div>
      <div class="space-y-2">
        <div class="flex items-center gap-2">
          <span class="text-xs font-medium">Override duration:</span>
          <select v-model.number="triggerConfig.self_modification.duration_hours" class="select select-bordered select-xs w-32">
            <option v-for="opt in durationOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
          </select>
        </div>
        <p class="text-xs opacity-40 ml-2">
          {{ triggerConfig.self_modification.duration_hours === 0 ? 'Agent cannot modify its own triggers.' :
             triggerConfig.self_modification.duration_hours === -1 ? 'Agent modifications are permanent.' :
             `Overrides expire after ${triggerConfig.self_modification.duration_hours} hours.` }}
        </p>

        <!-- Bounds -->
        <div v-if="triggerConfig.self_modification.duration_hours !== 0" class="ml-2 space-y-1">
          <span class="text-xs font-medium">Bounds (min – max):</span>
          <div v-for="(info, key) in conditionLabels" :key="key" class="flex items-center gap-2">
            <span class="text-xs w-28 opacity-60">{{ info.label }}:</span>
            <input
              type="number"
              :value="(triggerConfig.self_modification.bounds || {} as any)[key]?.min"
              @input="
                if (!triggerConfig.self_modification.bounds) triggerConfig.self_modification.bounds = {};
                if (!triggerConfig.self_modification.bounds[key]) triggerConfig.self_modification.bounds[key] = {};
                triggerConfig.self_modification.bounds[key].min = Number(($event.target as HTMLInputElement).value)
              "
              class="input input-bordered input-xs w-16"
              placeholder="min"
            />
            <span class="text-xs opacity-30">–</span>
            <input
              type="number"
              :value="(triggerConfig.self_modification.bounds || {} as any)[key]?.max"
              @input="
                if (!triggerConfig.self_modification.bounds) triggerConfig.self_modification.bounds = {};
                if (!triggerConfig.self_modification.bounds[key]) triggerConfig.self_modification.bounds[key] = {};
                triggerConfig.self_modification.bounds[key].max = Number(($event.target as HTMLInputElement).value)
              "
              class="input input-bordered input-xs w-16"
              placeholder="max"
            />
            <span class="text-xs opacity-40">{{ info.unit }}</span>
          </div>
        </div>
      </div>

      <!-- ========== SECTION 5: State Reset ========== -->
      <div class="divider text-xs opacity-50 my-0">STATE RESET</div>
      <div class="space-y-2">
        <label class="flex items-center gap-2 cursor-pointer">
          <input type="checkbox" class="toggle toggle-sm toggle-primary" v-model="triggerConfig.state_reset.enabled" />
          <span class="text-sm">Auto-reset counters</span>
        </label>
        <div v-if="triggerConfig.state_reset.enabled" class="ml-8 flex items-center gap-2">
          <span class="text-xs">Every</span>
          <input type="number" v-model.number="triggerConfig.state_reset.interval_days" class="input input-bordered input-xs w-14" :min="1" />
          <span class="text-xs">days at</span>
          <input type="time" v-model="triggerConfig.state_reset.reset_time" class="input input-bordered input-xs w-28" />
        </div>
      </div>
    </div>
  </div>
</template>

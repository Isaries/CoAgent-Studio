<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { ScheduleConfig } from '../../types/agent'

interface Props {
  scheduleConfig: ScheduleConfig
  syncSchedule: boolean
  activeTab: string
  canEdit: boolean
}

const props = defineProps<Props>()
const emit = defineEmits([
  'update:syncSchedule',
  'update:scheduleConfig',
  'addSpecific',
  'removeSpecific',
  'addGeneral',
  'removeGeneral'
])

// Local State for Two-Way Binding (Prevents mutation of props)
const localConfig = ref<ScheduleConfig>({ specific: [], general: { mode: 'none', rules: [] } })

// Update local when prop changes (from parent)
watch(
  () => props.scheduleConfig,
  (newVal) => {
    if (JSON.stringify(newVal) !== JSON.stringify(localConfig.value)) {
      localConfig.value = JSON.parse(JSON.stringify(newVal))
    }
  },
  { deep: true, immediate: true }
)

// Emit update when local changes (to parent)
watch(
  localConfig,
  (newVal) => {
    emit('update:scheduleConfig', newVal)
  },
  { deep: true }
)

// Proxy for v-model syncSchedule
const syncScheduleModel = computed({
  get: () => props.syncSchedule,
  set: (val) => emit('update:syncSchedule', val)
})
</script>

<template>
  <div class="collapse collapse-arrow bg-base-200 mb-6 border border-base-300">
    <input type="checkbox" />
    <div class="collapse-title font-medium flex items-center gap-2">
      <span>⚙️ Advanced: Triggers & Schedule</span>
    </div>
    <div class="collapse-content">
      <div class="p-2 space-y-4">
        <!-- Slot for Triggers which are technically separate but visually grouped in original -->
        <slot name="triggers"></slot>

        <div class="divider my-1"></div>

        <slot name="contextWindow"></slot>

        <div class="divider my-1"></div>

        <!-- Schedule -->
        <div>
          <div class="flex justify-between items-center mb-2">
            <h4 class="font-bold text-sm">Availability Schedule (UTC+8)</h4>

            <!-- Sync Checkbox (Student Only) -->
            <div v-if="activeTab === 'student'" class="form-control">
              <label class="label cursor-pointer gap-2 py-0">
                <span class="label-text text-xs font-bold text-primary"
                  >Use Teacher's Schedule</span
                >
                <input
                  type="checkbox"
                  v-model="syncScheduleModel"
                  class="checkbox checkbox-xs checkbox-primary"
                  :disabled="!canEdit"
                />
              </label>
            </div>
          </div>

          <div :class="{ 'opacity-50 pointer-events-none': syncSchedule }">
            <div v-if="syncSchedule" class="text-xs text-info mb-2 flex items-center gap-1">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="12"
                height="12"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path>
                <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path>
              </svg>
              Linked to Teacher's schedule. Uncheck to customize.
            </div>

            <!-- 1. Specific Exceptions -->
            <div class="mb-4 border rounded-md p-3 bg-base-100">
              <div class="flex justify-between items-center mb-2">
                <span class="text-sm font-bold"
                  >1. Specific Date Exceptions (Highest Priority)</span
                >
                <button
                  @click="$emit('addSpecific')"
                  class="btn btn-xs btn-outline btn-primary"
                  :disabled="syncSchedule || !canEdit"
                >
                  + Add Exception
                </button>
              </div>
              <div
                v-if="localConfig.specific.length === 0"
                class="text-xs text-gray-400 italic mb-2"
              >
                No specific exceptions defined.
              </div>
              <div
                v-for="(rule, idx) in localConfig.specific"
                :key="idx"
                class="flex items-center gap-2 mb-2 last:mb-0"
              >
                <input
                  type="date"
                  v-model="rule.date"
                  class="input input-xs input-bordered"
                  :disabled="syncSchedule || !canEdit"
                />
                <input
                  type="time"
                  v-model="rule.start"
                  class="input input-xs input-bordered"
                  :disabled="syncSchedule || !canEdit"
                />
                <span class="text-xs">-</span>
                <input
                  type="time"
                  v-model="rule.end"
                  class="input input-xs input-bordered"
                  :disabled="syncSchedule || !canEdit"
                />
                <button
                  @click="$emit('removeSpecific', idx)"
                  class="btn btn-xs btn-ghost text-error"
                  :disabled="syncSchedule || !canEdit"
                >
                  ✕
                </button>
              </div>
            </div>

            <!-- 2. General Pattern -->
            <div class="border rounded-md p-3 bg-base-100">
              <span class="text-sm font-bold block mb-2">2. General Schedule Pattern</span>
              <select
                v-model="localConfig.general.mode"
                class="select select-sm select-bordered w-full mb-2"
                :disabled="syncSchedule || !canEdit"
              >
                <option value="none">Always Active (unless restricted by Schedule)</option>
                <option value="range_daily">Date Range (Daily Time Period)</option>
                <option value="range_weekly">Date Range (Weekly Pattern)</option>
              </select>

              <div v-if="localConfig.general.mode !== 'none'" class="mt-2 space-y-2">
                <!-- Global Date Range -->
                <div class="grid grid-cols-2 gap-2 p-2 bg-base-200 rounded">
                  <div class="form-control">
                    <label class="label-text text-xs font-bold">Effective From</label>
                    <input
                      type="date"
                      v-model="localConfig.general.start_date"
                      class="input input-xs input-bordered"
                      :disabled="syncSchedule || !canEdit"
                    />
                  </div>
                  <div class="form-control">
                    <label class="label-text text-xs font-bold">Effective To</label>
                    <input
                      type="date"
                      v-model="localConfig.general.end_date"
                      class="input input-xs input-bordered"
                      :disabled="syncSchedule || !canEdit"
                    />
                  </div>
                </div>

                <!-- Time Rules List -->
                <div>
                  <label class="label-text text-xs font-bold mb-1 block">Time Rules</label>
                  <div
                    v-for="(rule, rIdx) in localConfig.general.rules"
                    :key="rIdx"
                    class="border p-2 rounded mb-2 relative"
                  >
                    <button
                      @click="$emit('removeGeneral', rIdx)"
                      class="btn btn-xs btn-circle btn-ghost absolute right-1 top-1 text-error"
                      :disabled="syncSchedule || !canEdit"
                    >
                      ✕
                    </button>

                    <div class="grid grid-cols-2 gap-2 mb-1">
                      <div class="form-control">
                        <label class="label-text text-[10px]">Start Time</label>
                        <input
                          type="time"
                          v-model="rule.start_time"
                          class="input input-xs input-bordered"
                          :disabled="syncSchedule || !canEdit"
                        />
                      </div>
                      <div class="form-control">
                        <label class="label-text text-[10px]">End Time</label>
                        <input
                          type="time"
                          v-model="rule.end_time"
                          class="input input-xs input-bordered"
                          :disabled="syncSchedule || !canEdit"
                        />
                      </div>
                    </div>

                    <!-- Weekly Days -->
                    <div
                      v-if="localConfig.general.mode === 'range_weekly'"
                      class="flex gap-1 flex-wrap pt-1 border-t mt-1"
                    >
                      <label
                        v-for="(d, i) in ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']"
                        :key="d"
                        class="cursor-pointer label p-0 gap-1 border rounded px-1 hover:bg-base-200"
                      >
                        <span class="label-text text-[10px]">{{ d }}</span>
                        <input
                          type="checkbox"
                          :value="i"
                          v-model="rule.days"
                          class="checkbox checkbox-xs"
                          :disabled="syncSchedule || !canEdit"
                        />
                      </label>
                    </div>
                  </div>
                  <div
                    v-if="localConfig.general.rules.length === 0"
                    class="text-xs text-error italic mb-2"
                  >
                    ⚠️ No time rules added. Agent will NOT be active.
                  </div>
                  <button
                    @click="$emit('addGeneral')"
                    class="btn btn-xs btn-outline w-full text-xs"
                    :disabled="syncSchedule || !canEdit"
                  >
                    + Add Time Rule
                  </button>
                </div>
              </div>
              <div v-else class="text-xs text-gray-400 italic">
                Agent is active 24/7 (except during Specific Exceptions if set).
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

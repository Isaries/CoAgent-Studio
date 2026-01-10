<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  agentType: 'teacher' | 'student' | 'analytics'
  canEdit: boolean
  // Simple Key Props (Teacher/Student)
  simpleKey: string
  maskedSimpleKey?: string
  // Analytics Key Props
  analyticsKeys: {
    room_key: string
    global_key: string
    backup_key: string
  }
}>()

const emit = defineEmits<{
  (e: 'update:simpleKey', value: string): void
  (e: 'update:analyticsKeys', value: any): void
  (e: 'clearSimpleKey'): void
}>()

// Computed proxies for v-model
const simpleKeyProxy = computed({
  get: () => props.simpleKey,
  set: (val) => emit('update:simpleKey', val)
})

const analyticsKeysProxy = computed({
  get: () => props.analyticsKeys,
  set: (val) => emit('update:analyticsKeys', val)
})
</script>

<template>
  <div class="form-control mb-6">
    <!-- Standard Agent Key (Teacher/Student) -->
    <div v-if="agentType !== 'analytics'">
      <label class="label">
        <span class="label-text">API Key</span>
        <span class="label-text-alt text-gray-500">Leave empty to keep existing</span>
      </label>
      <div class="join w-full">
        <input
          type="password"
          v-model="simpleKeyProxy"
          :disabled="!canEdit"
          placeholder="Enter new API Key..."
          class="input input-bordered join-item w-full"
        />
        <button
          v-if="canEdit && maskedSimpleKey"
          @click="$emit('clearSimpleKey')"
          class="btn btn-warning join-item"
          type="button"
        >
          Clear
        </button>
      </div>
      <div
        v-if="maskedSimpleKey && !simpleKeyProxy"
        class="label text-xs text-success flex gap-1 items-center"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
        >
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
        </svg>
        Current Key: {{ maskedSimpleKey }}
      </div>
    </div>

    <!-- Analytics Agent Keys (3 distinct keys) -->
    <div v-else class="space-y-4 border p-4 rounded bg-base-50">
      <div class="alert alert-info shadow-sm text-xs py-2">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          class="stroke-current shrink-0 w-4 h-4"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
          ></path>
        </svg>
        <span>Usage Order: Room Key &rarr; Global Key &rarr; Backup Key.</span>
      </div>

      <div
        v-for="(label, key) in {
          room_key: 'Room API Key',
          global_key: 'Global API Key',
          backup_key: 'Backup API Key'
        }"
        :key="key"
        class="form-control"
      >
        <label class="label">
          <span class="label-text text-sm font-semibold">{{ label }}</span>
          <span
            class="label-text-alt text-gray-400"
            v-if="!analyticsKeysProxy[key as keyof typeof analyticsKeysProxy]"
            >Not Set</span
          >
          <!-- If value is present and looks like mask (sk-...) or just present -->
          <span
            class="label-text-alt text-success font-bold font-mono"
            v-else-if="analyticsKeysProxy[key as keyof typeof analyticsKeysProxy].includes('****')"
            >Bound: {{ analyticsKeysProxy[key as keyof typeof analyticsKeysProxy] }}</span
          >
          <span class="label-text-alt text-info" v-else>New Value Entered</span>
        </label>
        <div class="join w-full">
          <input
            type="password"
            v-model="analyticsKeysProxy[key as keyof typeof analyticsKeysProxy]"
            :disabled="!canEdit"
            :placeholder="'Enter ' + label + '...'"
            class="input input-sm input-bordered join-item w-full"
          />
          <button
            v-if="analyticsKeysProxy[key as keyof typeof analyticsKeysProxy] && canEdit"
            @click="analyticsKeysProxy[key as keyof typeof analyticsKeysProxy] = ''"
            class="btn btn-sm btn-square join-item btn-outline btn-error"
            title="Clear / Unbind Key"
            type="button"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              class="h-4 w-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

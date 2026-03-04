<script setup lang="ts">
import { ref } from 'vue'
import { useNotificationStore } from '../../stores/notifications'
import { storeToRefs } from 'pinia'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
const store = useNotificationStore()
const { items, unreadCount } = storeToRefs(store)
const isOpen = ref(false)

const toggle = () => {
  isOpen.value = !isOpen.value
}

const handleClick = (id: string) => {
  store.markRead(id)
}

const typeClass = (type: string) => {
  switch (type) {
    case 'success': return 'text-success'
    case 'warning': return 'text-warning'
    case 'error': return 'text-error'
    default: return 'text-info'
  }
}

const formatTime = (ts: string) => {
  const d = new Date(ts)
  const now = new Date()
  const diff = now.getTime() - d.getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'now'
  if (mins < 60) return `${mins}m`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h`
  return `${Math.floor(hours / 24)}d`
}
</script>

<template>
  <div class="dropdown dropdown-end">
    <label tabindex="0" class="btn btn-ghost btn-sm btn-circle indicator" @click="toggle">
      <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="M14.857 17.082a23.848 23.848 0 0 0 5.454-1.31A8.967 8.967 0 0 1 18 9.75V9A6 6 0 0 0 6 9v.75a8.967 8.967 0 0 1-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 0 1-5.714 0m5.714 0a3 3 0 1 1-5.714 0" />
      </svg>
      <span v-if="unreadCount > 0" class="badge badge-xs badge-primary indicator-item">{{ unreadCount }}</span>
    </label>
    <div v-if="isOpen" tabindex="0" class="dropdown-content z-50 menu p-0 shadow-lg bg-base-100 rounded-box w-80 border border-base-300">
      <div class="flex items-center justify-between px-4 py-3 border-b border-base-300">
        <h3 class="font-bold text-sm">{{ t('notifications.title') }}</h3>
        <button v-if="items.length > 0" class="btn btn-ghost btn-xs" @click="store.markAllRead()">
          {{ t('notifications.markAllRead') }}
        </button>
      </div>
      <div class="max-h-72 overflow-y-auto">
        <div v-if="items.length === 0" class="px-4 py-8 text-center text-base-content/50 text-sm">
          {{ t('notifications.noNotifications') }}
        </div>
        <div
          v-for="item in items.slice(0, 20)"
          :key="item.id"
          @click="handleClick(item.id)"
          class="px-4 py-3 hover:bg-base-200 cursor-pointer border-b border-base-200 last:border-0 transition-colors"
          :class="{ 'bg-base-200/50': !item.read }"
        >
          <div class="flex items-start gap-2">
            <span class="mt-0.5 w-2 h-2 rounded-full shrink-0" :class="item.read ? 'bg-transparent' : 'bg-primary'"></span>
            <div class="flex-1 min-w-0">
              <div class="flex items-center justify-between">
                <span class="text-sm font-medium truncate" :class="typeClass(item.type)">{{ item.title }}</span>
                <span class="text-xs text-base-content/40 ml-2 shrink-0">{{ formatTime(item.timestamp) }}</span>
              </div>
              <p class="text-xs text-base-content/60 mt-0.5 truncate">{{ item.message }}</p>
            </div>
          </div>
        </div>
      </div>
      <div v-if="items.length > 0" class="border-t border-base-300 px-4 py-2">
        <button class="btn btn-ghost btn-xs btn-block" @click="store.clear()">{{ t('notifications.clear') }}</button>
      </div>
    </div>
  </div>
</template>

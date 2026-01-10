<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { watchDebounced } from '@vueuse/core'
import api from '../api'

const tables = ref<string[]>([])
const selectedTable = ref<string | null>(null)
const tableData = ref<any[]>([])
const loading = ref(false)
const error = ref<string | null>(null)

// Pagination
const limit = ref(100)
const offset = ref(0)
const hasMore = ref(true)
const searchQuery = ref('')
const resolveRelations = ref(true)
const startDate = ref('')
const endDate = ref('')
const isSidebarOpen = ref(true)

const supportedRelationsTables = ['message', 'course', 'room', 'usercourselink', 'userroomlink']
import { computed } from 'vue'
const isResolveSupported = computed(() => {
  return selectedTable.value && supportedRelationsTables.includes(selectedTable.value)
})

const hiddenColumns = ['sender_id', 'room_id', 'owner_id', 'course_id', 'user_id']
const visibleColumns = computed(() => {
  if (tableData.value.length === 0) return []
  const keys = Object.keys(tableData.value[0])

  if (resolveRelations.value && isResolveSupported.value) {
    return keys.filter((key) => !hiddenColumns.includes(key))
  }
  return keys
})

const onStartDateChange = () => {
  // Auto-sync End Date to Strat Date for convenience (Single Day Filter)
  if (startDate.value) {
    endDate.value = startDate.value
  }
  performSearch()
}

const performSearch = () => {
  offset.value = 0
  tableData.value = []
  hasMore.value = true
  fetchTableData()
}

// Real-time search with debounce
watchDebounced(
  searchQuery,
  () => {
    performSearch()
  },
  { debounce: 500, maxWait: 1000 }
)

const toggleResolvedView = () => {
  offset.value = 0
  tableData.value = []
  hasMore.value = true
  fetchTableData()
}

const fetchTables = async () => {
  try {
    const res = await api.get('/admin/db/tables')
    tables.value = res.data
  } catch (e: any) {
    error.value = 'Failed to fetch tables'
  }
}

const fetchTableData = async () => {
  if (!selectedTable.value) return

  loading.value = true
  error.value = null
  try {
    // Format dates
    const params: any = {
      limit: limit.value,
      offset: offset.value,
      resolve_relations: resolveRelations.value,
      search: searchQuery.value || undefined
    }

    if (startDate.value) {
      params.start_date = new Date(startDate.value + 'T00:00:00').toISOString()
    }
    if (endDate.value) {
      // End of the day
      params.end_date = new Date(endDate.value + 'T23:59:59').toISOString()
    }

    const res = await api.get(`/admin/db/tables/${selectedTable.value}`, {
      params: params
    })
    tableData.value = res.data
    if (res.data.length < limit.value) {
      hasMore.value = false
    } else {
      hasMore.value = true
    }
  } catch (e: any) {
    console.error('Full error object:', e)
    if (e.response && e.response.data) {
      error.value = `Server Error: ${JSON.stringify(e.response.data)}`
    } else {
      error.value = `Error: ${e.message || 'Unknown error'}`
    }
    tableData.value = []
  } finally {
    loading.value = false
  }
}

const selectTable = (table: string) => {
  selectedTable.value = table
  offset.value = 0
  searchQuery.value = '' // Reset search
  hasMore.value = true
  tableData.value = []
  fetchTableData()
}

const nextPage = () => {
  offset.value += limit.value
  fetchTableData()
}

const prevPage = () => {
  if (offset.value >= limit.value) {
    offset.value -= limit.value
    fetchTableData()
  }
}

onMounted(() => {
  fetchTables()
})
</script>

<template>
  <div class="flex h-[calc(100vh-64px)] overflow-hidden">
    <!-- Sidebar: Table List -->
    <div
      v-show="isSidebarOpen"
      class="w-64 flex-shrink-0 bg-base-100 border-r border-base-200 overflow-y-auto p-4 transition-all duration-300"
    >
      <div class="flex justify-between items-center mb-4">
        <h2 class="text-lg font-bold">Database Tables</h2>
        <button
          class="btn btn-sm btn-ghost btn-square"
          @click="isSidebarOpen = false"
          title="Collapse Sidebar"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="h-5 w-5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M11 19l-7-7 7-7m8 14l-7-7 7-7"
            />
          </svg>
        </button>
      </div>

      <div
        class="form-control mb-4"
        :class="{ 'opacity-50': !isResolveSupported }"
        :title="!isResolveSupported ? 'Not available for this table' : ''"
      >
        <label class="label cursor-pointer justify-start gap-2">
          <span class="label-text">Resolve Relations</span>
          <input
            type="checkbox"
            class="toggle toggle-primary toggle-sm"
            v-model="resolveRelations"
            @change="toggleResolvedView"
            :disabled="!isResolveSupported"
          />
        </label>
      </div>

      <ul class="menu w-full p-0">
        <li v-for="table in tables" :key="table">
          <a :class="{ active: selectedTable === table }" @click="selectTable(table)">
            {{ table }}
          </a>
        </li>
      </ul>
    </div>

    <!-- Main Area: Data View -->
    <div class="flex-1 p-4 flex flex-col overflow-hidden transition-all duration-300">
      <div class="flex justify-between items-center mb-4">
        <div class="flex items-center gap-2">
          <button
            v-show="!isSidebarOpen"
            class="btn btn-sm btn-ghost btn-square"
            @click="isSidebarOpen = true"
            title="Open Sidebar"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              class="h-5 w-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M4 6h16M4 12h16M4 18h16"
              />
            </svg>
          </button>
          <h2 class="text-xl font-bold">
            <span v-if="selectedTable">Table: {{ selectedTable }}</span>
            <span v-else>Select a table to view data</span>
          </h2>
        </div>
        <div v-if="selectedTable" class="flex items-center gap-2">
          <input
            type="date"
            v-model="startDate"
            class="input input-bordered input-sm"
            @change="onStartDateChange"
          />
          <span class="text-xs text-base-content/50">to</span>
          <input
            type="date"
            v-model="endDate"
            class="input input-bordered input-sm"
            @change="performSearch"
          />
          <div class="divider divider-horizontal m-0"></div>

          <input
            type="text"
            v-model="searchQuery"
            placeholder="Search..."
            class="input input-bordered input-sm w-full max-w-xs"
            @keyup.enter="performSearch"
          />
          <button class="btn btn-sm btn-ghost" @click="performSearch">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              class="h-5 w-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
          </button>
          <div class="divider divider-horizontal m-0"></div>
          <button class="btn btn-sm btn-ghost" @click="prevPage" :disabled="offset === 0">
            Previous
          </button>
          <span class="text-sm">Page {{ Math.floor(offset / limit) + 1 }}</span>
          <button class="btn btn-sm btn-ghost" @click="nextPage" :disabled="!hasMore">Next</button>
        </div>
      </div>

      <div v-if="error" class="alert alert-error mb-4">
        {{ error }}
      </div>

      <div v-if="loading" class="flex justify-center items-center h-full">
        <span class="loading loading-spinner loading-lg"></span>
      </div>

      <div
        v-else-if="selectedTable && tableData.length > 0"
        class="overflow-auto flex-1 border rounded-lg"
      >
        <table class="table table-pin-rows table-xs">
          <thead>
            <tr>
              <th v-for="key in visibleColumns" :key="key">{{ key }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, index) in tableData" :key="index">
              <td
                v-for="key in visibleColumns"
                :key="key"
                class="whitespace-nowrap max-w-xs overflow-hidden text-ellipsis"
                :title="String(row[key])"
              >
                <!-- Define value for cleaner template -->
                <template v-for="(value, vIdx) in [row[key]]" :key="vIdx">
                  <!-- Avatars -->
                  <span
                    v-if="
                      (String(key) === 'avatar_url' || String(key).includes('image')) &&
                      value &&
                      typeof value === 'string' &&
                      value.startsWith('http')
                    "
                  >
                    <div class="avatar">
                      <div class="w-8 h-8 rounded-full">
                        <img :src="value" alt="avatar" />
                      </div>
                    </div>
                  </span>
                  <!-- Status (Boolean) -->
                  <span v-else-if="typeof value === 'boolean' || String(key).startsWith('is_')">
                    <div class="badge" :class="value ? 'badge-success gap-2' : 'badge-ghost gap-2'">
                      <span v-if="value">Active</span>
                      <span v-else>Inactive</span>
                    </div>
                    <span class="text-xs opacity-50 ml-1">({{ value }})</span>
                  </span>
                  <!-- Roles -->
                  <span v-else-if="String(key) === 'role' && typeof value === 'string'">
                    <div
                      class="badge"
                      :class="{
                        'badge-primary': value === 'admin' || value === 'super_admin',
                        'badge-secondary': value === 'teacher',
                        'badge-accent': value === 'ta',
                        'badge-ghost': value === 'student' || value === 'guest'
                      }"
                    >
                      {{ value }}
                    </div>
                  </span>
                  <!-- Date Time -->
                  <span
                    v-else-if="
                      (String(key) === 'created_at' || String(key) === 'updated_at') && value
                    "
                  >
                    {{ new Date(value).toLocaleString() }}
                  </span>
                  <!-- Default -->
                  <span v-else>
                    {{
                      typeof value === 'object' && value !== null ? JSON.stringify(value) : value
                    }}
                  </span>
                </template>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div
        v-else-if="selectedTable"
        class="flex justify-center items-center h-full text-base-content/50"
      >
        No data found or empty table.
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
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

const fetchTables = async () => {
    try {
        const res = await api.get('/admin/db/tables')
        tables.value = res.data
    } catch (e: any) {
        error.value = "Failed to fetch tables"
    }
}

const fetchTableData = async () => {
    if (!selectedTable.value) return
    
    loading.value = true
    error.value = null
    try {
        const res = await api.get(`/admin/db/tables/${selectedTable.value}`, {
            params: {
                limit: limit.value,
                offset: offset.value
            }
        })
        tableData.value = res.data
        if (res.data.length < limit.value) {
            hasMore.value = false
        } else {
            hasMore.value = true
        }
    } catch (e: any) {
        error.value = e.response?.data?.detail || "Failed to fetch table data"
        tableData.value = []
    } finally {
        loading.value = false
    }
}

const selectTable = (table: string) => {
    selectedTable.value = table
    offset.value = 0
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
        <div class="w-1/4 bg-base-100 border-r border-base-200 overflow-y-auto p-4">
            <h2 class="text-lg font-bold mb-4">Database Tables</h2>
            <ul class="menu w-full p-0">
                <li v-for="table in tables" :key="table">
                    <a :class="{ 'active': selectedTable === table }" @click="selectTable(table)">
                        {{ table }}
                    </a>
                </li>
            </ul>
        </div>

        <!-- Main Area: Data View -->
        <div class="w-3/4 p-4 flex flex-col overflow-hidden">
            <div class="flex justify-between items-center mb-4">
                <h2 class="text-xl font-bold">
                    <span v-if="selectedTable">Table: {{ selectedTable }}</span>
                    <span v-else>Select a table to view data</span>
                </h2>
                <div v-if="selectedTable" class="flex items-center gap-2">
                    <button class="btn btn-sm btn-ghost" @click="prevPage" :disabled="offset === 0">Previous</button>
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

            <div v-else-if="selectedTable && tableData.length > 0" class="overflow-auto flex-1 border rounded-lg">
                <table class="table table-pin-rows table-xs">
                    <thead>
                        <tr>
                            <th v-for="(_, key) in tableData[0]" :key="key">{{ key }}</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr v-for="(row, index) in tableData" :key="index">
                            <td v-for="(value, key) in row" :key="key" class="whitespace-nowrap max-w-xs overflow-hidden text-ellipsis" :title="String(value)">
                                {{ typeof value === 'object' && value !== null ? JSON.stringify(value) : value }}
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
            
            <div v-else-if="selectedTable" class="flex justify-center items-center h-full text-base-content/50">
                No data found or empty table.
            </div>
        </div>
    </div>
</template>

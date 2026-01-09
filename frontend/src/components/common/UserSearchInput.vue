<script setup lang="ts">
import { ref } from 'vue'
import api from '../../api'

export interface UserResult {
    id: string
    email: string
    full_name?: string
    username?: string
}

const props = defineProps<{
    placeholder?: string
}>()

const emit = defineEmits<{
    (e: 'select', user: UserResult): void
}>()

const searchQuery = ref('')
const searchResults = ref<UserResult[]>([])
const searchLoading = ref(false)
let searchTimeout: any = null

const handleSearch = () => {
    if (searchTimeout) clearTimeout(searchTimeout)
    if (!searchQuery.value) {
        searchResults.value = []
        return
    }
    
    searchTimeout = setTimeout(async () => {
        searchLoading.value = true
        try {
            const res = await api.get('/users/search', { params: { q: searchQuery.value } })
            searchResults.value = res.data
        } catch (e) {
            console.error(e)
            // Ideally handle error UI
        } finally {
            searchLoading.value = false
        }
    }, 300)
}

const selectUser = (user: UserResult) => {
    emit('select', user)
    resetSearch()
}

const resetSearch = () => {
    searchQuery.value = ''
    searchResults.value = []
}

defineExpose({ resetSearch })
</script>

<template>
    <div class="form-control w-full relative">
        <label v-if="$slots.label" class="label">
            <slot name="label"></slot>
        </label>
        
        <input 
            type="text" 
            v-model="searchQuery" 
            @input="handleSearch"
            :placeholder="props.placeholder || 'Type to search...'" 
            class="input input-bordered w-full" 
        />
        
        <!-- Dropdown Results -->
        <ul v-if="searchResults.length > 0 && searchQuery" class="absolute top-full left-0 w-full bg-base-100 shadow-xl rounded-box z-50 p-2 mt-1 border border-base-200 max-h-60 overflow-y-auto">
            <li v-for="user in searchResults" :key="user.id">
                <a @click="selectUser(user)" class="block p-2 hover:bg-base-200 rounded cursor-pointer">
                    <div class="font-bold">{{ user.full_name || 'No Name' }}</div>
                    <div class="text-xs opacity-70">{{ user.email }} <span v-if="user.username">({{ user.username }})</span></div>
                </a>
            </li>
        </ul>
        
        <div v-else-if="searchQuery && !searchLoading && searchResults.length === 0" class="absolute top-full left-0 w-full bg-base-100 p-2 mt-1 text-sm text-center opacity-50 z-50">
            No users found.
        </div>
        
        <div v-if="searchLoading" class="absolute right-3 top-[3rem] loading loading-spinner loading-xs text-secondary"></div>
    </div>
</template>

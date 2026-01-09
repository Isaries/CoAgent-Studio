<script setup lang="ts">
import { ref } from 'vue'
import api from '../../../api'
import { AxiosError } from 'axios'
import UserSearchInput, { type UserResult } from '../../common/UserSearchInput.vue'

import { useToastStore } from '../../../stores/toast'

const props = defineProps<{
    roomId: string
}>()

const emit = defineEmits<{
    (e: 'assigned'): void
}>()

const dialogRef = ref<HTMLDialogElement | null>(null)
const searchInputRef = ref<InstanceType<typeof UserSearchInput> | null>(null)
const toast = useToastStore()

const assignEmail = ref('')
const assignUserId = ref('')
const assignLoading = ref(false)

const open = () => {
    assignEmail.value = ''
    assignUserId.value = ''
    if (searchInputRef.value) searchInputRef.value.resetSearch()
    dialogRef.value?.showModal()
}

const close = () => {
    dialogRef.value?.close()
}

const handleUserSelect = (user: UserResult) => {
    assignEmail.value = user.email || 'No Email'
    assignUserId.value = user.id
}

const assignUser = async () => {
    if (!assignUserId.value && (!assignEmail.value || assignEmail.value === 'No Email')) return
    if (!props.roomId) return

    assignLoading.value = true
    try {
        await api.post(`/rooms/${props.roomId}/assign`, {
            user_email: assignEmail.value !== 'No Email' ? assignEmail.value : null,
            user_id: assignUserId.value || null
        })
        toast.success(`User assigned successfully!`)
        emit('assigned')
        close()
    } catch (e: unknown) {
        if (e instanceof AxiosError && e.response) {
             toast.error('Assignment failed: ' + (e.response.data?.detail || e.message))
        } else {
             toast.error('Assignment failed: ' + String(e))
        }
    } finally {
        assignLoading.value = false
    }
}

defineExpose({ open, close })
</script>

<template>
    <dialog ref="dialogRef" class="modal">
        <div class="modal-box overflow-visible">
            <h3 class="font-bold text-lg">Assign Student to Room</h3>
            <p class="py-4">Search for a user to link to this room.</p>
            
            <UserSearchInput 
                ref="searchInputRef"
                placeholder="Search User"
                @select="handleUserSelect"
            >
                <template #label><span class="label-text">Search User</span></template>
            </UserSearchInput>

            <div v-if="assignEmail" class="alert alert-success shadow-sm mt-4 mb-4">
                <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                <span>Selected: {{ assignEmail }}</span>
            </div>

            <div class="modal-action">
                <form method="dialog"><button class="btn btn-ghost mr-2">Cancel</button></form>
                <button @click="assignUser" class="btn btn-secondary" :disabled="assignLoading || !assignEmail">Assign</button>
            </div>
        </div>
    </dialog>
</template>

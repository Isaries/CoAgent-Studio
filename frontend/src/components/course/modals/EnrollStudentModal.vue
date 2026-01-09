<script setup lang="ts">
import { ref } from 'vue'
import api from '../../../api'
import { AxiosError } from 'axios'
import UserSearchInput, { type UserResult } from '../../common/UserSearchInput.vue'

const props = defineProps<{
    courseId: string
}>()

const emit = defineEmits<{
    (e: 'enrolled'): void
}>()

const dialogRef = ref<HTMLDialogElement | null>(null)
const searchInputRef = ref<InstanceType<typeof UserSearchInput> | null>(null)

const enrollEmail = ref('')
const enrollUserId = ref('')
const enrollLoading = ref(false)

const open = () => {
    enrollEmail.value = ''
    enrollUserId.value = ''
    if (searchInputRef.value) searchInputRef.value.resetSearch()
    dialogRef.value?.showModal()
}

const close = () => {
    dialogRef.value?.close()
}

const handleUserSelect = (user: UserResult) => {
    enrollEmail.value = user.email || 'No Email'
    enrollUserId.value = user.id
}


const enrollUser = async () => {
    if (!enrollUserId.value && (!enrollEmail.value || enrollEmail.value === 'No Email')) return
    
    enrollLoading.value = true
    try {
        await api.post(`/courses/${props.courseId}/enroll`, {
           user_email: enrollEmail.value !== 'No Email' ? enrollEmail.value : null,
           user_id: enrollUserId.value || null,
           role: 'student'
        })
        alert(`User enrolled successfully!`)
        emit('enrolled')
        close()
    } catch (e: unknown) {
        if (e instanceof AxiosError && e.response) {
             alert('Enrollment failed: ' + (e.response.data?.detail || e.message))
        } else {
             alert('Enrollment failed: ' + String(e))
        }
    } finally {
        enrollLoading.value = false
    }
}

defineExpose({ open, close })
</script>

<template>
    <dialog ref="dialogRef" class="modal">
        <div class="modal-box overflow-visible">
            <h3 class="font-bold text-lg">Enroll Student</h3>
            <p class="py-4">Search for a user to add to this course.</p>
            
            <UserSearchInput 
                ref="searchInputRef"
                placeholder="Search User (Name, Email, Username)"
                @select="handleUserSelect"
            >
                <template #label><span class="label-text">Search User</span></template>
            </UserSearchInput>
            
            <!-- Selected User Display -->
            <div v-if="enrollEmail" class="alert alert-success shadow-sm mt-4 mb-4">
                <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                <span>Selected: {{ enrollEmail }}</span>
            </div>

            <div class="modal-action">
                <form method="dialog"><button class="btn btn-ghost mr-2">Cancel</button></form>
                <button @click="enrollUser" class="btn btn-secondary" :disabled="enrollLoading || !enrollEmail">Enroll</button>
            </div>
        </div>
    </dialog>
</template>

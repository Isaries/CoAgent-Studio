<script setup lang="ts">
import { ref } from 'vue'
import api from '../../../api'
import { AxiosError } from 'axios'

import { useToastStore } from '../../../stores/toast'

const props = defineProps<{
    courseId: string
}>()

const emit = defineEmits<{
    (e: 'created'): void
}>()

const dialogRef = ref<HTMLDialogElement | null>(null)
const name = ref('')
const loading = ref(false)
const toast = useToastStore()

const open = () => {
    name.value = ''
    loading.value = false
    dialogRef.value?.showModal()
}

const close = () => {
    dialogRef.value?.close()
}

const createRoom = async () => {
    if (!name.value) return
    loading.value = true
    
    try {
        await api.post('/rooms/', {
            name: name.value,
            course_id: props.courseId
        })
        
        emit('created')
        close()
        toast.success("Room created")
    } catch (e: unknown) {
        console.error(e)
        if (e instanceof AxiosError && e.response) {
            toast.error('Failed to create room: ' + (e.response.data?.detail || e.message))
        } else {
             toast.error('Failed to create room: ' + String(e))
        }
    } finally {
        loading.value = false
    }
}

defineExpose({ open, close })
</script>

<template>
    <dialog ref="dialogRef" class="modal">
        <div class="modal-box">
            <h3 class="font-bold text-lg">Create New Room</h3>
            <p class="py-4">Create a new discussion space.</p>
            <div class="form-control w-full mb-4">
                <label class="label"><span class="label-text">Room Name</span></label>
                <input type="text" v-model="name" placeholder="e.g. Group A Discussion" class="input input-bordered w-full" />
            </div>
            <div class="modal-action">
                <form method="dialog"><button class="btn btn-ghost mr-2">Cancel</button></form>
                <button @click="createRoom" class="btn btn-primary" :disabled="loading">Create</button>
            </div>
        </div>
    </dialog>
</template>

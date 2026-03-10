<script setup lang="ts">
import { ref } from 'vue'
import api from '../../../api'
import { AxiosError } from 'axios'
import { useToastStore } from '../../../stores/toast'
import AppModal from '../../common/AppModal.vue'

const props = defineProps<{
  spaceId: string
}>()

const emit = defineEmits<{
  (e: 'created'): void
}>()

const show = ref(false)
const name = ref('')
const loading = ref(false)
const toast = useToastStore()

const open = () => {
  name.value = ''
  loading.value = false
  show.value = true
}

const close = () => {
  show.value = false
}

const createRoom = async () => {
  if (!name.value) return
  loading.value = true

  try {
    await api.post('/rooms/', {
      name: name.value,
      space_id: props.spaceId
    })

    emit('created')
    close()
    toast.success('Room created')
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
  <AppModal v-model="show" title="Create New Room" size="md">
    <p class="py-4">Create a new discussion space.</p>
    <div class="form-control w-full mb-4">
      <label class="label"><span class="label-text">Room Name</span></label>
      <input
        type="text"
        v-model="name"
        placeholder="e.g. Group A Discussion"
        class="input input-bordered w-full"
      />
    </div>
    <template #actions>
      <button class="btn btn-ghost mr-2" @click="close">Cancel</button>
      <button @click="createRoom" class="btn btn-primary" :disabled="loading">Create</button>
    </template>
  </AppModal>
</template>

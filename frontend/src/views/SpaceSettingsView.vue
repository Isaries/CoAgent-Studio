<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useToastStore } from '../stores/toast'
import api from '../api'

const route = useRoute()
const router = useRouter()
const spaceId = route.params.id as string
const toast = useToastStore()

const space = ref<any>(null)
const isLoading = ref(false)
const isSaving = ref(false)

const presetBadgeClass = (preset: string) => {
  switch (preset) {
    case 'colearn': return 'badge-primary'
    case 'support': return 'badge-secondary'
    case 'research': return 'badge-accent'
    default: return 'badge-ghost'
  }
}

const loadSpace = async () => {
  isLoading.value = true
  try {
    const res = await api.get(`/spaces/${spaceId}`)
    space.value = res.data
  } catch (e: any) {
    console.error(e)
    if (e.response?.status === 403 || e.response?.status === 404) {
      toast.error('You do not have access to this space.')
      router.push('/spaces')
      return
    }
    toast.error('Failed to load space details')
  } finally {
    isLoading.value = false
  }
}

const saveSpace = async () => {
  isSaving.value = true
  try {
    await api.put(`/spaces/${spaceId}`, {
      title: space.value.title,
      description: space.value.description
    })
    toast.success('Space updated successfully')
  } catch (e) {
    console.error(e)
    toast.error('Failed to update space')
  } finally {
    isSaving.value = false
  }
}

onMounted(() => {
  loadSpace()
})
</script>

<template>
  <div class="h-full flex flex-col p-6 max-w-2xl mx-auto">
    <div class="flex justify-between items-center mb-6">
      <div class="flex items-center gap-3">
        <router-link :to="`/spaces/${spaceId}`" class="btn btn-ghost btn-sm">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7" />
          </svg>
          Back
        </router-link>
        <h1 class="text-2xl font-bold">Space Settings</h1>
      </div>
      <button
        class="btn btn-primary"
        @click="saveSpace"
        :disabled="isSaving || isLoading"
      >
        <span v-if="isSaving" class="loading loading-spinner loading-sm"></span>
        Save Changes
      </button>
    </div>

    <div v-if="isLoading" class="flex justify-center p-12">
      <span class="loading loading-spinner loading-lg"></span>
    </div>

    <div v-else-if="space" class="card bg-base-100 shadow-sm border border-base-200">
      <div class="card-body">
        <div class="form-control w-full mb-4">
          <label class="label"><span class="label-text font-bold">Space Title</span></label>
          <input type="text" v-model="space.title" class="input input-bordered w-full" />
        </div>

        <div class="form-control w-full mb-4">
          <label class="label"><span class="label-text font-bold">Description</span></label>
          <textarea v-model="space.description" class="textarea textarea-bordered h-32"></textarea>
        </div>

        <div class="form-control w-full">
          <label class="label"><span class="label-text font-bold">Preset</span></label>
          <div>
            <span class="badge badge-lg" :class="presetBadgeClass(space.preset)">
              {{ space.preset }}
            </span>
            <p class="text-xs text-base-content/50 mt-2">
              The preset determines the default configuration for your space. It cannot be changed after creation.
            </p>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="alert alert-error">
      Space not found.
    </div>
  </div>
</template>

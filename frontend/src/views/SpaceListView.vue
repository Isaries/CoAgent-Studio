<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useToastStore } from '../stores/toast'
import { spaceService } from '../services/spaceService'
import { useFormValidation } from '../composables/useFormValidation'
import { required } from '../utils/validators'
import type { Space } from '../types/space'
import type { SpacePreset } from '../types/enums'

const toast = useToastStore()

const spaces = ref<Space[]>([])
const loading = ref(true)

// Create Modal State
const createModal = ref<HTMLDialogElement | null>(null)
const newSpace = ref({
  title: '',
  description: '',
  preset: 'custom' as SpacePreset,
  loading: false
})

const spaceValidation = useFormValidation({
  title: { rules: [required('Space title is required')] },
})

const presets: { key: SpacePreset; label: string; icon: string; description: string }[] = [
  {
    key: 'colearn',
    label: 'CoLearn',
    icon: 'M12 14l9-5-9-5-9 5 9 5z M12 14l6.16-3.422a12.083 12.083 0 01.665 6.479A11.952 11.952 0 0012 20.055a11.952 11.952 0 00-6.824-2.998 12.078 12.078 0 01.665-6.479L12 14z',
    description: 'Collaborative learning with announcements, analytics, and group rooms'
  },
  {
    key: 'support',
    label: 'Support',
    icon: 'M18.364 5.636l-3.536 3.536m0 5.656l3.536 3.536M9.172 9.172L5.636 5.636m3.536 9.192l-3.536 3.536M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-5 0a4 4 0 11-8 0 4 4 0 018 0z',
    description: 'Customer or user support with agent-powered rooms'
  },
  {
    key: 'research',
    label: 'Research',
    icon: 'M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z',
    description: 'Research workspace with knowledge graphs and data analysis'
  },
  {
    key: 'custom',
    label: 'Custom',
    icon: 'M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z M15 12a3 3 0 11-6 0 3 3 0 016 0z',
    description: 'Start from scratch with full flexibility'
  }
]

const presetBadgeClass = (preset: string) => {
  switch (preset) {
    case 'colearn': return 'badge-primary'
    case 'support': return 'badge-secondary'
    case 'research': return 'badge-accent'
    default: return 'badge-ghost'
  }
}

const fetchSpaces = async () => {
  try {
    const res = await spaceService.getSpaces()
    spaces.value = res.data
  } catch (e) {
    console.error(e)
    toast.error('Failed to load spaces')
  } finally {
    loading.value = false
  }
}

const openCreateModal = () => {
  newSpace.value = { title: '', description: '', preset: 'custom', loading: false }
  spaceValidation.reset()
  createModal.value?.showModal()
}

const selectPreset = (key: SpacePreset) => {
  newSpace.value.preset = key
}

const createSpace = async () => {
  const valid = spaceValidation.validateAll({ title: newSpace.value.title })
  if (!valid) return
  newSpace.value.loading = true

  try {
    await spaceService.createSpace({
      title: newSpace.value.title,
      description: newSpace.value.description,
      preset: newSpace.value.preset
    } as any)

    createModal.value?.close()
    toast.success('Space created successfully')
    await fetchSpaces()
  } catch (e: any) {
    console.error(e)
    toast.error('Failed to create space: ' + (e.response?.data?.detail || e.message))
  } finally {
    newSpace.value.loading = false
  }
}

onMounted(() => {
  fetchSpaces()
})
</script>

<template>
  <div class="p-6">
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-3xl font-bold">My Spaces</h1>
      <button @click="openCreateModal" class="btn btn-primary">Create Space</button>
    </div>

    <div v-if="loading" class="flex justify-center">
      <span class="loading loading-spinner loading-lg"></span>
    </div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <div v-for="space in spaces" :key="space.id" class="card bg-base-100 shadow-xl">
        <div class="card-body">
          <div class="flex items-start justify-between">
            <h2 class="card-title">{{ space.title }}</h2>
            <span class="badge badge-sm" :class="presetBadgeClass(space.preset)">
              {{ space.preset }}
            </span>
          </div>
          <p class="text-sm opacity-70 mb-2">{{ space.description }}</p>
          <div class="text-xs text-base-content/60">
            <div v-if="space.owner_name">By {{ space.owner_name }}</div>
            <div>{{ new Date(space.created_at).toLocaleDateString() }}</div>
          </div>
          <div class="card-actions justify-end">
            <router-link :to="`/spaces/${space.id}`" class="btn btn-sm btn-primary">
              Enter
            </router-link>
          </div>
        </div>
      </div>

      <div v-if="spaces.length === 0" class="col-span-full text-center py-10 opacity-50">
        No spaces yet.
      </div>
    </div>

    <!-- Create Space Modal -->
    <dialog ref="createModal" class="modal">
      <div class="modal-box max-w-2xl">
        <h3 class="font-bold text-lg">Create New Space</h3>
        <p class="py-2 text-sm opacity-70">Choose a preset and enter your space details.</p>

        <!-- Preset Selector -->
        <div class="grid grid-cols-2 gap-3 my-4">
          <div
            v-for="preset in presets"
            :key="preset.key"
            @click="selectPreset(preset.key)"
            class="card border-2 cursor-pointer transition-all hover:shadow-md p-4"
            :class="newSpace.preset === preset.key ? 'border-primary bg-primary/5' : 'border-base-300'"
          >
            <div class="flex items-center gap-3 mb-2">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                class="h-6 w-6"
                :class="newSpace.preset === preset.key ? 'text-primary' : 'text-base-content/60'"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                stroke-width="1.5"
              >
                <path stroke-linecap="round" stroke-linejoin="round" :d="preset.icon" />
              </svg>
              <span class="font-semibold text-sm">{{ preset.label }}</span>
            </div>
            <p class="text-xs opacity-60 leading-relaxed">{{ preset.description }}</p>
          </div>
        </div>

        <div class="form-control w-full mb-4">
          <label class="label"><span class="label-text">Space Title</span></label>
          <input
            type="text"
            v-model="newSpace.title"
            placeholder="e.g. CS 101 Study Group"
            class="input input-bordered w-full"
            :class="{ 'input-error': spaceValidation.touched.title && spaceValidation.errors.title }"
            @blur="spaceValidation.touchField('title', newSpace.title)"
          />
          <label v-if="spaceValidation.touched.title && spaceValidation.errors.title" class="label">
            <span class="label-text-alt text-error">{{ spaceValidation.errors.title }}</span>
          </label>
        </div>

        <div class="form-control w-full mb-4">
          <label class="label"><span class="label-text">Description</span></label>
          <textarea
            v-model="newSpace.description"
            class="textarea textarea-bordered h-24"
            placeholder="Space description..."
          ></textarea>
        </div>

        <div class="modal-action">
          <form method="dialog">
            <button class="btn btn-ghost mr-2">Cancel</button>
          </form>
          <button @click="createSpace" class="btn btn-primary" :disabled="newSpace.loading">
            <span v-if="newSpace.loading" class="loading loading-spinner loading-xs"></span>
            Create
          </button>
        </div>
      </div>
    </dialog>
  </div>
</template>

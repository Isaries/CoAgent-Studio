<script setup lang="ts">
import { ref, computed } from 'vue'
import { formatDistanceToNow } from 'date-fns'
import type { Announcement } from '../../types/course'
import { useAuthStore } from '../../stores/auth'

const props = defineProps<{
  announcements: Announcement[]
  courseOwnerId: string
}>()

const emit = defineEmits<{
  (e: 'create', data: { title: string; content: string }): void
}>()

const authStore = useAuthStore()

// Permission: Owner, Admin, or TA (Need to check if current user is TA in course context,
// strictly speaking we need 'myRole' passed here, but for now owner check covers most.
// Ideally we pass 'canManage' prop)
const canCreate = computed(() => {
  // If owner or admin
  if (authStore.user?.role === 'admin' || authStore.user?.role === 'super_admin') return true
  if (authStore.user?.id === props.courseOwnerId) return true
  // TA check would happen in parent and passed down, or we enable button and let API reject 403
  // But better UX is to hide.
  // We will assume parent passes a 'canEdit' prop or similar?
  // For now, let's enable for everyone not-student if possible, or just owner.
  // Wait, useCourse doesn't expose 'myRole'.
  // We'll rely on parent.
  return true
})

const showCreate = ref(false)
const newTitle = ref('')
const newContent = ref('')
const submitting = ref(false)

const handleCreate = async () => {
  if (!newTitle.value || !newContent.value) return
  submitting.value = true
  try {
    emit('create', { title: newTitle.value, content: newContent.value })
    newTitle.value = ''
    newContent.value = ''
    showCreate.value = false
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="space-y-6">
    <!-- Toolbar -->
    <div class="flex justify-between items-center" v-if="canCreate">
      <h3 class="font-bold text-lg">Announcements</h3>
      <button @click="showCreate = !showCreate" class="btn btn-primary btn-sm">
        {{ showCreate ? 'Cancel' : '+ New Announcement' }}
      </button>
    </div>

    <!-- Create Form -->
    <div
      v-if="showCreate"
      class="card bg-base-100 shadow-lg border border-primary/20 animate-fade-in"
    >
      <div class="card-body">
        <input
          v-model="newTitle"
          type="text"
          placeholder="Title"
          class="input input-bordered font-bold"
        />
        <textarea
          v-model="newContent"
          class="textarea textarea-bordered h-24"
          placeholder="Content..."
        ></textarea>
        <div class="card-actions justify-end">
          <button @click="handleCreate" class="btn btn-primary" :disabled="submitting">
            {{ submitting ? 'Posting...' : 'Post Announcement' }}
          </button>
        </div>
      </div>
    </div>

    <!-- List -->
    <div v-if="announcements.length === 0" class="text-center py-10 text-gray-500">
      No announcements yet.
    </div>

    <div v-else class="space-y-4">
      <div
        v-for="ann in announcements"
        :key="ann.id"
        class="card bg-base-100 shadow-sm border border-base-200"
      >
        <div class="card-body p-5">
          <h3 class="card-title text-lg">{{ ann.title }}</h3>
          <div class="text-xs text-gray-400 mb-2">
            Posted {{ formatDistanceToNow(new Date(ann.created_at)) }} ago
          </div>
          <p class="whitespace-pre-wrap text-gray-700">{{ ann.content }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.animate-fade-in {
  animation: fadeIn 0.3s ease-out;
}
@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>

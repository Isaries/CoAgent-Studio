<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useToastStore } from '../stores/toast'
import { courseService } from '../services/courseService'
import type { Course } from '../types/course'
import AppModal from '../components/common/AppModal.vue'
import AppCard from '../components/common/AppCard.vue'

const authStore = useAuthStore()
const toast = useToastStore()

const courses = ref<Course[]>([])
const loading = ref(true)

// Create Modal State
const showCreateModal = ref(false)
const newCourse = ref({
  title: '',
  description: '',
  loading: false
})

const fetchCourses = async () => {
  try {
    const res = await courseService.getCourses()
    courses.value = res.data
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

const openCreateModal = () => {
  newCourse.value = { title: '', description: '', loading: false }
  showCreateModal.value = true
}

const createCourse = async () => {
  if (!newCourse.value.title) return
  newCourse.value.loading = true

  try {
    await courseService.createCourse({
      title: newCourse.value.title,
      description: newCourse.value.description
    })

    showCreateModal.value = false

    await fetchCourses() // Refresh list
  } catch (e: any) {
    console.error(e)
    toast.error('Failed to create course: ' + (e.response?.data?.detail || e.message))
  } finally {
    newCourse.value.loading = false
  }
}

onMounted(() => {
  fetchCourses()
})
</script>

<template>
  <div class="p-6">
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-3xl font-bold">My Courses</h1>
      <button @click="openCreateModal" class="btn btn-primary">Create Course</button>
    </div>

    <div v-if="loading" class="flex justify-center">
      <span class="loading loading-spinner loading-lg"></span>
    </div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <AppCard v-for="course in courses" :key="course.id" variant="hover">
        <div class="card-body">
          <h2 class="card-title">{{ course.title }}</h2>
          <p class="text-sm opacity-70 mb-2">{{ course.description }}</p>
          <div class="text-xs text-base-content/60">
            <div v-if="course.owner_name">By {{ course.owner_name }}</div>
            <div>{{ new Date(course.created_at).toLocaleDateString() }}</div>
          </div>
          <div class="card-actions justify-end">
            <router-link :to="`/spaces/${course.id}`" class="btn btn-sm btn-ghost"
              >Enter</router-link
            >
            <router-link
              v-if="!authStore.isStudent"
              :to="`/spaces/${course.id}/settings`"
              class="btn btn-sm btn-primary"
              >Manage</router-link
            >
          </div>
        </div>
      </AppCard>

      <div v-if="courses.length === 0" class="col-span-full text-center py-16 bg-base-100 rounded-box shadow-sm">
        <div class="w-16 h-16 mx-auto rounded-full bg-base-200 flex items-center justify-center mb-4">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-8 w-8 text-base-content/30" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 14l9-5-9-5-9 5 9 5z M12 14l6.16-3.422a12.083 12.083 0 01.665 6.479A11.952 11.952 0 0012 20.055a11.952 11.952 0 00-6.824-2.998 12.078 12.078 0 01.665-6.479L12 14z" />
          </svg>
        </div>
        <h3 class="font-bold text-lg mb-2">No Courses Yet</h3>
        <p class="text-base-content/60 mb-4">Create your first course to get started.</p>
        <button class="btn btn-primary" @click="openCreateModal">Create Course</button>
      </div>
    </div>

    <!-- Create Course Modal -->
    <AppModal v-model="showCreateModal" title="Create New Course" size="md">
      <p class="py-4">Enter course details below.</p>

      <div class="form-control w-full mb-4">
        <label class="label"><span class="label-text">Course Title</span></label>
        <input
          type="text"
          v-model="newCourse.title"
          placeholder="e.g. History 101"
          class="input input-bordered w-full"
        />
      </div>

      <div class="form-control w-full mb-4">
        <label class="label"><span class="label-text">Description</span></label>
        <textarea
          v-model="newCourse.description"
          class="textarea textarea-bordered h-24"
          placeholder="Course description..."
        ></textarea>
      </div>

      <template #actions>
        <button class="btn btn-ghost mr-2" @click="showCreateModal = false">Cancel</button>
        <button @click="createCourse" class="btn btn-primary" :disabled="newCourse.loading">
          <span v-if="newCourse.loading" class="loading loading-spinner loading-xs"></span>
          Create
        </button>
      </template>
    </AppModal>
  </div>
</template>

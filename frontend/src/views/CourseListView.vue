<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useAuthStore } from '../stores/auth'
import { courseService } from '../services/courseService'
import type { Course } from '../types/course'

const authStore = useAuthStore()

const courses = ref<Course[]>([])
const loading = ref(true)

// Create Modal State
const createModal = ref<HTMLDialogElement | null>(null)
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
  // Use template ref instead of document.getElementById
  createModal.value?.showModal()
}

const createCourse = async () => {
  if (!newCourse.value.title) return
  newCourse.value.loading = true

  try {
    await courseService.createCourse({
      title: newCourse.value.title,
      description: newCourse.value.description
    })

    // Close modal
    createModal.value?.close()

    await fetchCourses() // Refresh list
  } catch (e: any) {
    console.error(e)
    alert('Failed to create course: ' + (e.response?.data?.detail || e.message))
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
      <div v-for="course in courses" :key="course.id" class="card bg-base-100 shadow-xl">
        <div class="card-body">
          <h2 class="card-title">{{ course.title }}</h2>
          <p class="text-sm opacity-70 mb-2">{{ course.description }}</p>
          <div class="text-xs text-base-content/60">
            <div v-if="course.owner_name">By {{ course.owner_name }}</div>
            <div>{{ new Date(course.created_at).toLocaleDateString() }}</div>
          </div>
          <div class="card-actions justify-end">
            <router-link :to="`/courses/${course.id}`" class="btn btn-sm btn-ghost"
              >Enter</router-link
            >
            <router-link
              v-if="!authStore.isStudent"
              :to="`/courses/${course.id}`"
              class="btn btn-sm btn-primary"
              >Manage</router-link
            >
          </div>
        </div>
      </div>

      <div v-if="courses.length === 0" class="col-span-full text-center py-10 opacity-50">
        No courses found.
      </div>
    </div>

    <!-- Using ref="createModal" instead of just ID -->
    <dialog ref="createModal" id="create_course_modal" class="modal">
      <div class="modal-box">
        <h3 class="font-bold text-lg">Create New Course</h3>
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

        <div class="modal-action">
          <form method="dialog">
            <!-- if there is a button in form, it will close the modal -->
            <button class="btn btn-ghost mr-2">Cancel</button>
          </form>
          <button @click="createCourse" class="btn btn-primary" :disabled="newCourse.loading">
            <span v-if="newCourse.loading" class="loading loading-spinner loading-xs"></span>
            Create
          </button>
        </div>
      </div>
    </dialog>
  </div>
</template>

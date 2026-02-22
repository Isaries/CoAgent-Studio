<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useToastStore } from '../stores/toast'
import api from '../api'

const route = useRoute()
const router = useRouter()
const courseId = route.params.id as string
const toast = useToastStore()

const course = ref<any>(null)
const isLoading = ref(false)
const isSaving = ref(false)

const loadCourse = async () => {
  isLoading.value = true
  try {
    const res = await api.get(`/courses/${courseId}`)
    course.value = res.data
  } catch (e: any) {
    console.error(e)
    if (e.response?.status === 403 || e.response?.status === 404) {
      toast.error('You do not have access to this course.')
      router.push('/courses')
      return
    }
    toast.error('Failed to load course details')
  } finally {
    isLoading.value = false
  }
}

const saveCourse = async () => {
  isSaving.value = true
  try {
    await api.put(`/courses/${courseId}`, {
      title: course.value.title,
      description: course.value.description
    })
    toast.success('Course updated successfully')
  } catch (e) {
    console.error(e)
    toast.error('Failed to update course')
  } finally {
    isSaving.value = false
  }
}

onMounted(() => {
  loadCourse()
})
</script>

<template>
  <div class="h-full flex flex-col p-6 max-w-2xl mx-auto">
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-2xl font-bold">Course Settings</h1>
      <button 
        class="btn btn-primary" 
        @click="saveCourse" 
        :disabled="isSaving || isLoading"
      >
        <span v-if="isSaving" class="loading loading-spinner loading-sm"></span>
        Save Changes
      </button>
    </div>

    <div v-if="isLoading" class="flex justify-center p-12">
      <span class="loading loading-spinner loading-lg"></span>
    </div>

    <div v-else-if="course" class="card bg-base-100 shadow-sm border border-base-200">
      <div class="card-body">
        <div class="form-control w-full mb-4">
          <label class="label"><span class="label-text font-bold">Course Title</span></label>
          <input type="text" v-model="course.title" class="input input-bordered w-full" />
        </div>
        
        <div class="form-control w-full">
          <label class="label"><span class="label-text font-bold">Description</span></label>
          <textarea v-model="course.description" class="textarea textarea-bordered h-32"></textarea>
        </div>
      </div>
    </div>
    
    <div v-else class="alert alert-error">
      Course not found.
    </div>
  </div>
</template>

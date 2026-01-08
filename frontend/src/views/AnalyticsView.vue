<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import api from '../api'

const route = useRoute()
// Handle the case where params.id might be undefined (global analytics route)
const courseId = route.params.id as string | undefined

interface Report {
    id: string
    course_id: string
    content: string
    created_at: string
    report_type: string
}

const reports = ref<Report[]>([])
const loading = ref(false)
const generating = ref(false)

const fetchReports = async () => {
    if (!courseId) return
    loading.value = true
    try {
        const res = await api.get(`/analytics/${courseId}`)
        reports.value = res.data
    } catch (e) {
        console.error("Failed to fetch reports", e)
    } finally {
        loading.value = false
    }
}

const generateReport = async () => {
    if (!courseId) return
    generating.value = true
    try {
        await api.post(`/analytics/${courseId}/generate`)
        await fetchReports() // Refresh list
    } catch (e) {
        alert("Failed to generate report. Ensure Analytics Agent is configured.")
    } finally {
        generating.value = false
    }
}

const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString()
}

onMounted(() => {
    if (courseId) {
        fetchReports()
    }
})
</script>

<template>
  <div class="p-6">
    <div class="flex justify-between items-center mb-6">
        <div>
            <h1 class="text-3xl font-bold">Course Analytics</h1>
            <p class="text-gray-500">AI-driven insights for your course rooms.</p>
        </div>
        <div class="flex gap-2" v-if="courseId">
            <router-link :to="`/courses/${courseId}`" class="btn btn-ghost">Back to Course</router-link>
            <button @click="generateReport" class="btn btn-primary" :disabled="generating">
                <span v-if="generating" class="loading loading-spinner loading-xs"></span>
                {{ generating ? 'Analyzing...' : 'Generate New Report' }}
            </button>
        </div>
    </div>
    
    <div v-if="!courseId" class="text-center p-12 bg-base-100 rounded-box shadow">
        <h3 class="font-bold text-lg mb-2">No Course Selected</h3>
        <p class="mb-4">Please select a course to view its analytics.</p>
        <router-link to="/courses" class="btn btn-primary">Go to My Courses</router-link>
    </div>
    
    <div v-else-if="loading" class="flex justify-center p-12">
        <span class="loading loading-spinner loading-lg"></span>
    </div>
    
    <div v-else-if="reports.length === 0" class="text-center p-12 bg-base-100 rounded-box shadow">
        <h3 class="font-bold text-lg mb-2">No reports yet</h3>
        <p class="mb-4">Click generate to let the AI analyze recent discussions.</p>
        <button @click="generateReport" class="btn btn-primary">Generate First Report</button>
    </div>
    
    <div v-else class="space-y-8">
        <div v-for="report in reports" :key="report.id" class="card bg-base-100 shadow-xl">
            <div class="card-body">
                <div class="flex justify-between w-full mb-4 border-b pb-2">
                    <h2 class="card-title text-primary">
                        {{ report.report_type === 'course_summary' ? 'Course Summary Report' : 'Analytics Report' }}
                    </h2>
                    <span class="badge badge-ghost">{{ formatDate(report.created_at) }}</span>
                </div>
                
                <!-- Content Display (Markdown-ish) -->
                <div class="prose max-w-none whitespace-pre-wrap font-sans">
                    {{ report.content }}
                </div>
            </div>
        </div>
    </div>
  </div>
</template>

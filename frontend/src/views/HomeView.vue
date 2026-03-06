<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { spaceService } from '../services/spaceService'
import { dashboardService, type DashboardStats } from '../services/dashboardService'
import SkeletonCard from '../components/common/SkeletonCard.vue'
import type { Space } from '../types/space'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
const router = useRouter()
const auth = useAuthStore()

// Dashboard state
const spaces = ref<Space[]>([])
const stats = ref<DashboardStats>({ spaceCount: 0, agentCount: 0, workflowCount: 0 })
const recentRooms = ref<any[]>([])
const loading = ref(false)
const statsLoading = ref(false)
const currentDate = computed(() => {
  return new Date().toLocaleDateString('en-US', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  })
})

const displaySpaces = computed(() => spaces.value.slice(0, 6))

// Fetch data when authenticated
onMounted(async () => {
  if (auth.isAuthenticated) {
    loading.value = true
    statsLoading.value = true
    try {
      const [spacesRes, dashStats, rooms] = await Promise.all([
        spaceService.getSpaces(),
        dashboardService.getStats(auth.isStudent),
        dashboardService.getRecentRooms()
      ])
      spaces.value = spacesRes.data
      stats.value = dashStats
      recentRooms.value = rooms
    } catch (e) {
      console.error('Failed to fetch dashboard data', e)
    } finally {
      loading.value = false
      statsLoading.value = false
    }
  }
})
</script>

<template>
  <!-- Landing Page for Non-Authenticated Users -->
  <div v-if="!auth.isAuthenticated" class="hero min-h-screen bg-base-200">
    <div class="hero-content text-center">
      <div class="max-w-lg">
        <h1 class="text-5xl font-bold">CoAgent Studio</h1>
        <p class="py-6 text-lg text-base-content/70">
          AI Agent Orchestration Platform. Design, deploy, and manage multi-agent workflows with
          ease.
        </p>
        <button class="btn btn-primary btn-lg" @click="router.push('/login')">
          {{ t('login.signIn') }}
        </button>
      </div>
    </div>
  </div>

  <!-- Dashboard for Authenticated Users -->
  <div v-else class="space-y-6">
    <!-- Welcome Banner -->
    <div class="bg-gradient-to-r from-primary/10 via-primary/5 to-transparent rounded-box p-6">
      <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 class="text-2xl font-bold">
            {{ t('dashboard.welcome', { name: auth.user?.full_name || 'User' }) }}
          </h1>
          <p class="text-base-content/60 mt-1">{{ currentDate }}</p>
        </div>
        <div class="flex flex-wrap gap-2">
          <button class="btn btn-primary btn-sm" @click="router.push('/spaces')">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              class="h-4 w-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              stroke-width="2"
            >
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
            </svg>
            {{ t('dashboard.createSpace') }}
          </button>
          <button
            v-if="!auth.isStudent"
            class="btn btn-outline btn-sm"
            @click="router.push('/platform/workflows')"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              class="h-4 w-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              stroke-width="2"
            >
              <path stroke-linecap="round" stroke-linejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            {{ t('dashboard.newWorkflow') }}
          </button>
          <button
            v-if="!auth.isStudent"
            class="btn btn-outline btn-sm"
            @click="router.push('/agents')"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              class="h-4 w-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              stroke-width="2"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                d="M9.75 3.104v5.714a2.25 2.25 0 0 1-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 0 1 4.5 0m0 0v5.714a2.25 2.25 0 0 0 .659 1.591L19 14.5M14.25 3.104c.251.023.501.05.75.082M19 14.5l-1.39 4.17a2.25 2.25 0 0 1-2.135 1.58H8.525a2.25 2.25 0 0 1-2.135-1.58L5 14.5m14 0H5"
              />
            </svg>
            {{ t('nav.agentLab') }}
          </button>
        </div>
      </div>
    </div>

    <!-- Stats Bar -->
    <div class="stats stats-vertical sm:stats-horizontal shadow w-full bg-base-100">
      <div class="stat">
        <div class="stat-figure text-primary">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="h-6 w-6"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            stroke-width="2"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M2.25 7.125C2.25 6.504 2.754 6 3.375 6h6c.621 0 1.125.504 1.125 1.125v3.75c0 .621-.504 1.125-1.125 1.125h-6A1.125 1.125 0 0 1 2.25 10.875v-3.75ZM14.25 8.625c0-.621.504-1.125 1.125-1.125h5.25c.621 0 1.125.504 1.125 1.125v8.25c0 .621-.504 1.125-1.125 1.125h-5.25a1.125 1.125 0 0 1-1.125-1.125v-8.25ZM3.75 16.125c0-.621.504-1.125 1.125-1.125h5.25c.621 0 1.125.504 1.125 1.125v2.25c0 .621-.504 1.125-1.125 1.125h-5.25a1.125 1.125 0 0 1-1.125-1.125v-2.25Z"
            />
          </svg>
        </div>
        <div class="stat-title">{{ t('dashboard.mySpaces') }}</div>
        <div class="stat-value text-primary">
          <span v-if="statsLoading" class="loading loading-spinner loading-sm"></span>
          <span v-else>{{ stats.spaceCount }}</span>
        </div>
        <div class="stat-desc">{{ t('dashboard.spacesDesc') }}</div>
      </div>

      <div class="stat">
        <div class="stat-figure text-secondary">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="h-6 w-6"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            stroke-width="2"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M15 19.128a9.38 9.38 0 0 0 2.625.372 9.337 9.337 0 0 0 4.121-.952 4.125 4.125 0 0 0-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 0 1 8.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0 1 11.964-3.07M12 6.375a3.375 3.375 0 1 1-6.75 0 3.375 3.375 0 0 1 6.75 0Zm8.25 2.25a2.625 2.625 0 1 1-5.25 0 2.625 2.625 0 0 1 5.25 0Z"
            />
          </svg>
        </div>
        <div class="stat-title">{{ t('dashboard.activeAgents') }}</div>
        <div class="stat-value text-secondary">
          <span v-if="statsLoading" class="loading loading-spinner loading-sm"></span>
          <span v-else>{{ stats.agentCount }}</span>
        </div>
        <div class="stat-desc">{{ t('dashboard.agentsDesc') }}</div>
      </div>

      <div class="stat">
        <div class="stat-figure text-accent">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="h-6 w-6"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            stroke-width="2"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M3.75 6A2.25 2.25 0 0 1 6 3.75h2.25A2.25 2.25 0 0 1 10.5 6v2.25a2.25 2.25 0 0 1-2.25 2.25H6a2.25 2.25 0 0 1-2.25-2.25V6ZM3.75 15.75A2.25 2.25 0 0 1 6 13.5h2.25a2.25 2.25 0 0 1 2.25 2.25V18a2.25 2.25 0 0 1-2.25 2.25H6A2.25 2.25 0 0 1 3.75 18v-2.25ZM13.5 6a2.25 2.25 0 0 1 2.25-2.25H18A2.25 2.25 0 0 1 20.25 6v2.25A2.25 2.25 0 0 1 18 10.5h-2.25a2.25 2.25 0 0 1-2.25-2.25V6ZM13.5 15.75a2.25 2.25 0 0 1 2.25-2.25H18a2.25 2.25 0 0 1 2.25 2.25V18A2.25 2.25 0 0 1 18 20.25h-2.25A2.25 2.25 0 0 1 13.5 18v-2.25Z"
            />
          </svg>
        </div>
        <div class="stat-title">{{ t('dashboard.workflows') }}</div>
        <div class="stat-value text-accent">
          <span v-if="statsLoading" class="loading loading-spinner loading-sm"></span>
          <span v-else>{{ stats.workflowCount }}</span>
        </div>
        <div class="stat-desc">{{ t('dashboard.workflowsDesc') }}</div>
      </div>
    </div>

    <!-- My Spaces -->
    <div>
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-xl font-semibold">{{ t('dashboard.mySpaces') }}</h2>
        <router-link to="/spaces" class="btn btn-ghost btn-sm">
          {{ t('common.viewAll') }}
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="h-4 w-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            stroke-width="2"
          >
            <path stroke-linecap="round" stroke-linejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
          </svg>
        </router-link>
      </div>

      <!-- Loading State -->
      <div v-if="loading" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <SkeletonCard v-for="i in 3" :key="i" :lines="3" :show-action="true" />
      </div>

      <!-- Empty State -->
      <div v-else-if="spaces.length === 0" class="card bg-base-100 shadow-sm">
        <div class="card-body items-center text-center py-12">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="h-12 w-12 text-base-content/30 mb-2"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            stroke-width="1.5"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M2.25 7.125C2.25 6.504 2.754 6 3.375 6h6c.621 0 1.125.504 1.125 1.125v3.75c0 .621-.504 1.125-1.125 1.125h-6A1.125 1.125 0 0 1 2.25 10.875v-3.75ZM14.25 8.625c0-.621.504-1.125 1.125-1.125h5.25c.621 0 1.125.504 1.125 1.125v8.25c0 .621-.504 1.125-1.125 1.125h-5.25a1.125 1.125 0 0 1-1.125-1.125v-8.25ZM3.75 16.125c0-.621.504-1.125 1.125-1.125h5.25c.621 0 1.125.504 1.125 1.125v2.25c0 .621-.504 1.125-1.125 1.125h-5.25a1.125 1.125 0 0 1-1.125-1.125v-2.25Z"
            />
          </svg>
          <p class="text-base-content/60">{{ t('dashboard.noSpaces') }}</p>
          <button class="btn btn-primary btn-sm mt-4" @click="router.push('/spaces')">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              class="h-4 w-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              stroke-width="2"
            >
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
            </svg>
            {{ t('dashboard.createSpace') }}
          </button>
        </div>
      </div>

      <!-- Space Cards Grid -->
      <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <div
          v-for="space in displaySpaces"
          :key="space.id"
          class="card bg-base-100 shadow-sm hover:shadow-md transition-shadow"
        >
          <div class="card-body p-5">
            <h3 class="card-title text-base">{{ space.title }}</h3>
            <div class="flex items-center gap-2 mt-1">
              <span class="badge badge-outline badge-sm">{{ space.preset }}</span>
            </div>
            <div class="card-actions justify-end mt-3">
              <button class="btn btn-primary btn-sm" @click="router.push(`/spaces/${space.id}`)">
                {{ t('common.enter') }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Recent Rooms -->
    <div v-if="recentRooms.length > 0">
      <h2 class="text-xl font-semibold mb-4">{{ t('dashboard.recentRooms') }}</h2>
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <div
          v-for="room in recentRooms"
          :key="room.id"
          class="card bg-base-100 shadow-sm hover:shadow-md transition-shadow cursor-pointer"
          @click="router.push(`/rooms/${room.id}`)"
        >
          <div class="card-body p-4">
            <h3 class="font-semibold text-sm">{{ room.name }}</h3>
            <p v-if="room.description" class="text-xs text-base-content/60 truncate">
              {{ room.description }}
            </p>
          </div>
        </div>
      </div>
    </div>

    <!-- Quick Links (non-students only) -->
    <div v-if="!auth.isStudent">
      <h2 class="text-xl font-semibold mb-4">{{ t('dashboard.quickLinks') }}</h2>
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <!-- Agent Lab -->
        <router-link
          to="/agents"
          class="card bg-base-100 shadow-sm hover:shadow-md transition-shadow cursor-pointer"
        >
          <div class="card-body p-5">
            <div class="flex items-center gap-3">
              <div class="bg-primary/10 rounded-btn p-2">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  class="h-6 w-6 text-primary"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  stroke-width="2"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    d="M9.75 3.104v5.714a2.25 2.25 0 0 1-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 0 1 4.5 0m0 0v5.714a2.25 2.25 0 0 0 .659 1.591L19 14.5M14.25 3.104c.251.023.501.05.75.082M19 14.5l-1.39 4.17a2.25 2.25 0 0 1-2.135 1.58H8.525a2.25 2.25 0 0 1-2.135-1.58L5 14.5m14 0H5"
                  />
                </svg>
              </div>
              <div>
                <h3 class="font-semibold text-sm">{{ t('nav.agentLab') }}</h3>
                <p class="text-xs text-base-content/60">Design and configure AI agents</p>
              </div>
            </div>
          </div>
        </router-link>

        <!-- Workflows -->
        <router-link
          to="/platform/workflows"
          class="card bg-base-100 shadow-sm hover:shadow-md transition-shadow cursor-pointer"
        >
          <div class="card-body p-5">
            <div class="flex items-center gap-3">
              <div class="bg-secondary/10 rounded-btn p-2">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  class="h-6 w-6 text-secondary"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  stroke-width="2"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    d="M3.75 6A2.25 2.25 0 0 1 6 3.75h2.25A2.25 2.25 0 0 1 10.5 6v2.25a2.25 2.25 0 0 1-2.25 2.25H6a2.25 2.25 0 0 1-2.25-2.25V6ZM3.75 15.75A2.25 2.25 0 0 1 6 13.5h2.25a2.25 2.25 0 0 1 2.25 2.25V18a2.25 2.25 0 0 1-2.25 2.25H6A2.25 2.25 0 0 1 3.75 18v-2.25ZM13.5 6a2.25 2.25 0 0 1 2.25-2.25H18A2.25 2.25 0 0 1 20.25 6v2.25A2.25 2.25 0 0 1 18 10.5h-2.25a2.25 2.25 0 0 1-2.25-2.25V6ZM13.5 15.75a2.25 2.25 0 0 1 2.25-2.25H18a2.25 2.25 0 0 1 2.25 2.25V18A2.25 2.25 0 0 1 18 20.25h-2.25A2.25 2.25 0 0 1 13.5 18v-2.25Z"
                  />
                </svg>
              </div>
              <div>
                <h3 class="font-semibold text-sm">{{ t('nav.workflows') }}</h3>
                <p class="text-xs text-base-content/60">Build multi-agent workflows</p>
              </div>
            </div>
          </div>
        </router-link>

        <!-- Triggers -->
        <router-link
          to="/platform/triggers"
          class="card bg-base-100 shadow-sm hover:shadow-md transition-shadow cursor-pointer"
        >
          <div class="card-body p-5">
            <div class="flex items-center gap-3">
              <div class="bg-accent/10 rounded-btn p-2">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  class="h-6 w-6 text-accent"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  stroke-width="2"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    d="M13 10V3L4 14h7v7l9-11h-7z"
                  />
                </svg>
              </div>
              <div>
                <h3 class="font-semibold text-sm">{{ t('nav.triggers') }}</h3>
                <p class="text-xs text-base-content/60">Set up automated triggers</p>
              </div>
            </div>
          </div>
        </router-link>

        <!-- Knowledge Engine -->
        <router-link
          to="/platform/knowledge"
          class="card bg-base-100 shadow-sm hover:shadow-md transition-shadow cursor-pointer"
        >
          <div class="card-body p-5">
            <div class="flex items-center gap-3">
              <div class="bg-info/10 rounded-btn p-2">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  class="h-6 w-6 text-info"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  stroke-width="2"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    d="M12 6.042A8.967 8.967 0 0 0 6 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 0 1 6 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 0 1 6-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0 0 18 18a8.967 8.967 0 0 0-6 2.292m0-14.25v14.25"
                  />
                </svg>
              </div>
              <div>
                <h3 class="font-semibold text-sm">{{ t('nav.knowledgeEngine') }}</h3>
                <p class="text-xs text-base-content/60">Manage knowledge graphs</p>
              </div>
            </div>
          </div>
        </router-link>
      </div>
    </div>
  </div>
</template>

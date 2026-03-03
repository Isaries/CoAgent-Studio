import { createRouter, createWebHistory } from 'vue-router'
import LoginView from '../views/LoginView.vue'
import { useAuthStore } from '../stores/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      component: () => import('../layouts/BaseLayout.vue'),
      meta: { requiresAuth: true },
      children: [
        // ─── HOME (Dashboard) ────────────────────────────────
        {
          path: '',
          name: 'home',
          component: () => import('../views/HomeView.vue')
        },

        // ─── PLATFORM ─────────────────────────────────────────
        {
          path: 'agents',
          name: 'agents',
          component: () => import('../views/WorkspaceView.vue'),
          meta: { requiresNonStudent: true }
        },
        {
          path: 'projects/:projectId/agents/:agentId',
          name: 'agent-detail',
          component: () => import('../views/AgentView.vue'),
          meta: { requiresNonStudent: true }
        },
        {
          path: 'my-agents',
          name: 'my-agents',
          component: () => import('../views/MyAgentsView.vue'),
          meta: { requiresNonStudent: true }
        },
        {
          path: 'platform/workflows',
          name: 'platform-workflows',
          component: () => import('../views/studio/WorkflowsView.vue'),
          meta: { requiresNonStudent: true }
        },
        {
          path: 'platform/workflows/:workflowId',
          name: 'platform-workflow-editor',
          component: () => import('../views/WorkflowEditorView.vue'),
          meta: { requiresNonStudent: true }
        },
        {
          path: 'platform/triggers',
          name: 'platform-triggers',
          component: () => import('../views/studio/TriggersView.vue'),
          meta: { requiresNonStudent: true }
        },
        {
          path: 'platform/knowledge',
          name: 'platform-knowledge',
          component: () => import('../views/KnowledgeView.vue'),
          meta: { requiresNonStudent: true }
        },

        // ─── SPACES (renamed from COURSES) ────────────────────
        {
          path: 'spaces',
          name: 'spaces',
          component: () => import('../views/SpaceListView.vue')
        },
        {
          path: 'spaces/:id',
          name: 'space-hub',
          component: () => import('../views/SpaceHubView.vue')
        },
        {
          path: 'spaces/:id/settings',
          name: 'space-settings',
          component: () => import('../views/SpaceSettingsView.vue')
        },
        {
          path: 'spaces/:id/analytics',
          name: 'space-analytics',
          component: () => import('../views/AnalyticsView.vue'),
          meta: { requiresNonStudent: true }
        },

        // ─── ROOMS ────────────────────────────────────────────
        {
          path: 'rooms/:id',
          name: 'room',
          component: () => import('../views/RoomView.vue')
        },
        {
          path: 'rooms/:id/settings',
          name: 'room-settings',
          component: () => import('../views/RoomSettingsView.vue')
        },
        {
          path: 'rooms/:id/workflow',
          name: 'room-workflow',
          component: () => import('../views/WorkflowEditorView.vue'),
          meta: { requiresNonStudent: true }
        },

        // ─── SYSTEM ───────────────────────────────────────────
        {
          path: 'my-keys',
          name: 'my-keys',
          component: () => import('../views/UserKeysView.vue')
        },
        {
          path: 'analytics',
          name: 'analytics',
          component: () => import('../views/AnalyticsView.vue'),
          meta: { requiresAdmin: true }
        },
        {
          path: 'dashboard',
          name: 'dashboard',
          component: () => import('../views/DashboardView.vue'),
          meta: { requiresAdmin: true }
        },
        {
          path: 'admin/users',
          name: 'user-list',
          component: () => import('../views/UserListView.vue'),
          meta: { requiresAdmin: true }
        },
        {
          path: 'admin/database',
          name: 'database-view',
          component: () => import('../views/DatabaseView.vue'),
          meta: { requiresAdmin: true }
        },
        {
          path: 'admin/system-agents',
          name: 'system-agent-settings',
          component: () => import('../views/SystemSettingsView.vue'),
          meta: { requiresAdmin: true }
        },

        // ─── BACKWARD COMPAT REDIRECTS ────────────────────────
        { path: 'courses', redirect: '/spaces' },
        { path: 'courses/:id', redirect: (to: any) => `/spaces/${to.params.id}` },
        { path: 'courses/:id/settings', redirect: (to: any) => `/spaces/${to.params.id}/settings` },
        { path: 'courses/:id/analytics', redirect: (to: any) => `/spaces/${to.params.id}/analytics` },
        { path: 'workspace', redirect: '/agents' },
        { path: 'studio/workflows', redirect: '/platform/workflows' },
        { path: 'studio/workflows/:workflowId', redirect: (to: any) => `/platform/workflows/${to.params.workflowId}` },
        { path: 'studio/triggers', redirect: '/platform/triggers' },
      ]
    },
    {
      path: '/login',
      name: 'login',
      component: LoginView
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'NotFound',
      component: () => import('../views/HomeView.vue'),
      meta: { title: 'Page Not Found' }
    }
  ]
})

router.beforeEach(async (to, _from, next) => {
  const authStore = useAuthStore()
  const requiresAuth = to.matched.some((record) => record.meta.requiresAuth)
  const requiresAdmin = to.matched.some((record) => record.meta.requiresAdmin)

  // Sync auth state if user is not loaded
  if (!authStore.user) {
    try {
      await authStore.fetchUser()
    } catch (e) {
      // Token might be invalid
    }
  }

  // Check auth requirement
  if (requiresAuth && !authStore.isAuthenticated) {
    next('/login')
    return
  }

  // Check admin role
  if (requiresAdmin && !authStore.isAdmin) {
    next('/spaces') // Redirect non-admins to spaces
    return
  }

  const requiresNonStudent = to.matched.some((record) => record.meta.requiresNonStudent)
  if (requiresNonStudent && authStore.isStudent) {
    next('/spaces')
    return
  }

  next()
})

export default router

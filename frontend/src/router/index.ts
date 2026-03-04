import { createRouter, createWebHistory } from 'vue-router'
import LoginView from '../views/LoginView.vue'
import { useAuthStore } from '../stores/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      component: () => import('../layouts/BaseLayout.vue'),
      meta: { requiresAuth: true, breadcrumb: 'Home' },
      children: [
        // ─── HOME (Dashboard) ────────────────────────────────
        {
          path: '',
          name: 'home',
          component: () => import('../views/HomeView.vue'),
          meta: { breadcrumb: 'Home' }
        },

        // ─── PLATFORM ─────────────────────────────────────────
        {
          path: 'agents',
          name: 'agents',
          component: () => import('../views/WorkspaceView.vue'),
          meta: { requiresNonStudent: true, breadcrumb: 'Agent Lab' }
        },
        {
          path: 'projects/:projectId/agents/:agentId',
          name: 'agent-detail',
          component: () => import('../views/AgentView.vue'),
          meta: { requiresNonStudent: true, breadcrumb: 'Agent Detail' }
        },
        {
          path: 'my-agents',
          name: 'my-agents',
          component: () => import('../views/MyAgentsView.vue'),
          meta: { requiresNonStudent: true, breadcrumb: 'My Agents' }
        },
        {
          path: 'platform/workflows',
          name: 'platform-workflows',
          component: () => import('../views/studio/WorkflowsView.vue'),
          meta: { requiresNonStudent: true, breadcrumb: 'Workflows' }
        },
        {
          path: 'platform/workflows/:workflowId',
          name: 'platform-workflow-editor',
          component: () => import('../views/WorkflowEditorView.vue'),
          meta: { requiresNonStudent: true, breadcrumb: 'Workflow Editor' }
        },
        {
          path: 'platform/triggers',
          name: 'platform-triggers',
          component: () => import('../views/studio/TriggersView.vue'),
          meta: { requiresNonStudent: true, breadcrumb: 'Triggers' }
        },
        {
          path: 'platform/knowledge',
          name: 'platform-knowledge',
          component: () => import('../views/KnowledgeView.vue'),
          meta: { requiresNonStudent: true, breadcrumb: 'Knowledge Engine' }
        },

        // ─── SPACES (renamed from COURSES) ────────────────────
        {
          path: 'spaces',
          name: 'spaces',
          component: () => import('../views/SpaceListView.vue'),
          meta: { breadcrumb: 'My Spaces' }
        },
        {
          path: 'spaces/:id',
          name: 'space-hub',
          component: () => import('../views/SpaceHubView.vue'),
          meta: { breadcrumb: 'Space' }
        },
        {
          path: 'spaces/:id/settings',
          name: 'space-settings',
          component: () => import('../views/SpaceSettingsView.vue'),
          meta: { breadcrumb: 'Space Settings' }
        },
        {
          path: 'spaces/:id/analytics',
          name: 'space-analytics',
          component: () => import('../views/AnalyticsView.vue'),
          meta: { requiresNonStudent: true, breadcrumb: 'Space Analytics' }
        },

        // ─── ROOMS ────────────────────────────────────────────
        {
          path: 'rooms/:id',
          name: 'room',
          component: () => import('../views/RoomView.vue'),
          meta: { breadcrumb: 'Room' }
        },
        {
          path: 'rooms/:id/settings',
          name: 'room-settings',
          component: () => import('../views/RoomSettingsView.vue'),
          meta: { breadcrumb: 'Room Settings' }
        },
        {
          path: 'rooms/:id/workflow',
          name: 'room-workflow',
          component: () => import('../views/WorkflowEditorView.vue'),
          meta: { requiresNonStudent: true, breadcrumb: 'Workflow Editor' }
        },

        // ─── SYSTEM ───────────────────────────────────────────
        {
          path: 'my-keys',
          name: 'my-keys',
          component: () => import('../views/UserKeysView.vue'),
          meta: { breadcrumb: 'My API Keys' }
        },
        {
          path: 'analytics',
          name: 'analytics',
          component: () => import('../views/AnalyticsView.vue'),
          meta: { requiresAdmin: true, breadcrumb: 'Analytics' }
        },
        {
          path: 'dashboard',
          name: 'dashboard',
          component: () => import('../views/DashboardView.vue'),
          meta: { requiresAdmin: true, breadcrumb: 'Dashboard' }
        },
        {
          path: 'admin/users',
          name: 'user-list',
          component: () => import('../views/UserListView.vue'),
          meta: { requiresAdmin: true, breadcrumb: 'Users' }
        },
        {
          path: 'admin/database',
          name: 'database-view',
          component: () => import('../views/DatabaseView.vue'),
          meta: { requiresAdmin: true, breadcrumb: 'Database' }
        },
        {
          path: 'admin/system-agents',
          name: 'system-agent-settings',
          component: () => import('../views/SystemSettingsView.vue'),
          meta: { requiresAdmin: true, breadcrumb: 'System Agents' }
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
      redirect: '/'
    }
  ]
})

router.beforeEach(async (to, _from, next) => {
  const authStore = useAuthStore()
  const requiresAuth = to.matched.some((record) => record.meta.requiresAuth)
  const requiresAdmin = to.matched.some((record) => record.meta.requiresAdmin)

  // Sync auth state if user is not loaded (guard against parallel in-flight calls)
  if (!authStore.user) {
    if (!fetchingUserPromise) {
      fetchingUserPromise = authStore.fetchUser().finally(() => {
        fetchingUserPromise = null
      })
    }
    try {
      await fetchingUserPromise
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

let fetchingUserPromise: Promise<void> | null = null

export default router

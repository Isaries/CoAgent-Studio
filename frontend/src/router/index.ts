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
                {
                    path: 'dashboard',
                    name: 'dashboard',
                    component: () => import('../views/DashboardView.vue'),
                    meta: { requiresAdmin: true }
                },
                {
                    path: 'analytics',
                    name: 'analytics',
                    component: () => import('../views/AnalyticsView.vue'),
                },
                {
                    path: 'courses',
                    name: 'courses',
                    component: () => import('../views/CourseListView.vue'),
                },
                {
                    path: 'courses/:id/settings',
                    name: 'course-settings',
                    component: () => import('../views/CourseSettingsView.vue'),
                },
                {
                    path: 'courses/:id/analytics',
                    name: 'course-analytics',
                    component: () => import('../views/AnalyticsView.vue'),
                },
                {
                    path: 'courses/:id',
                    name: 'course-detail',
                    component: () => import('../views/CourseDetailView.vue'),
                },
                {
                    path: 'rooms/:id',
                    name: 'room',
                    component: () => import('../views/RoomView.vue'),
                },
                {
                    path: 'rooms/:id/settings',
                    name: 'room-settings',
                    component: () => import('../views/RoomSettingsView.vue'),
                },
                {
                    path: 'admin/users',
                    name: 'user-list',
                    component: () => import('../views/UserListView.vue'),
                }
            ]
        },
        {
            path: '/login',
            name: 'login',
            component: LoginView
        }
    ]
})

router.beforeEach(async (to, _from, next) => {
    const authStore = useAuthStore()

    // Check auth for protected routes
    if (to.meta.requiresAuth && !authStore.isAuthenticated) {
        next('/login')
        return
    }

    // Check admin role
    if (to.meta.requiresAdmin && !authStore.isAdmin) {
        next('/courses') // Redirect non-admins to courses
        return
    }

    next()
})

export default router

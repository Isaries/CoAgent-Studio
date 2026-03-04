import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createI18n } from 'vue-i18n'
import LoginView from '../../views/LoginView.vue'
import en from '../../locales/en'

// Mock useAuth
vi.mock('../../composables/useAuth', () => ({
  useAuth: () => ({
    login: vi.fn().mockResolvedValue(false),
    user: { value: null },
    isAuthenticated: { value: false },
    isAdmin: { value: false },
    isSuperAdmin: { value: false },
    isStudent: { value: false },
    isImpersonating: { value: false },
    logout: vi.fn(),
    impersonate: vi.fn(),
    stopImpersonating: vi.fn(),
  }),
}))

const i18n = createI18n({ legacy: false, locale: 'en', messages: { en } })

const createTestRouter = () =>
  createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/login', component: LoginView },
      { path: '/', component: { template: '<div />' } },
    ],
  })

describe('LoginView', () => {
  it('renders login form', async () => {
    setActivePinia(createPinia())
    const router = createTestRouter()
    await router.push('/login')
    await router.isReady()

    const wrapper = mount(LoginView, {
      global: { plugins: [createPinia(), router, i18n] },
    })

    expect(wrapper.find('form').exists()).toBe(true)
    expect(wrapper.find('input[type="text"]').exists()).toBe(true)
    expect(wrapper.find('input[type="password"]').exists()).toBe(true)
    expect(wrapper.find('button[type="submit"]').exists()).toBe(true)
  })

  it('renders Google OAuth button in user mode', async () => {
    setActivePinia(createPinia())
    const router = createTestRouter()
    await router.push('/login')
    await router.isReady()

    const wrapper = mount(LoginView, {
      global: { plugins: [createPinia(), router, i18n] },
    })

    expect(wrapper.text()).toContain('Continue with Google')
  })

  it('has admin login toggle', async () => {
    setActivePinia(createPinia())
    const router = createTestRouter()
    await router.push('/login')
    await router.isReady()

    const wrapper = mount(LoginView, {
      global: { plugins: [createPinia(), router, i18n] },
    })

    const adminBtn = wrapper.findAll('button').find((b) => b.text().includes('Admin Login'))
    expect(adminBtn).toBeDefined()
  })

  it('shows error on failed login', async () => {
    setActivePinia(createPinia())
    const router = createTestRouter()
    await router.push('/login')
    await router.isReady()

    const wrapper = mount(LoginView, {
      global: { plugins: [createPinia(), router, i18n] },
    })

    await wrapper.find('input[type="text"]').setValue('user')
    await wrapper.find('input[type="password"]').setValue('wrongpass')
    await wrapper.find('form').trigger('submit')

    // Wait for async
    await new Promise((r) => setTimeout(r, 100))
    await wrapper.vm.$nextTick()

    // The error message should appear (login returns false)
    expect(wrapper.text()).toContain('Invalid credentials')
  })
})

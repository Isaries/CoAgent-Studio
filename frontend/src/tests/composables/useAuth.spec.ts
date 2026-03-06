import { describe, it, expect, vi, beforeEach } from 'vitest'
import { defineComponent } from 'vue'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'

// ---------------------------------------------------------------------------
// Store mock — declared before composable import so vi.mock hoisting works
// ---------------------------------------------------------------------------
let mockAuthStore = {
  user: null as { id: string; email: string; full_name: string; role: string } | null,
  isAuthenticated: false,
  isAdmin: false,
  isSuperAdmin: false,
  isStudent: false,
  isImpersonating: false,
  fetchUser: vi.fn(),
  logout: vi.fn(),
  impersonateUser: vi.fn(),
  stopImpersonating: vi.fn()
}

vi.mock('@/stores/auth', () => ({
  useAuthStore: vi.fn(() => mockAuthStore)
}))

// storeToRefs() wraps each property in a computed ref so the composable
// destructuring works without error.
vi.mock('pinia', async (importOriginal) => {
  const actual = await importOriginal<typeof import('pinia')>()
  const { ref, computed } = await import('vue')
  return {
    ...actual,
    storeToRefs: vi.fn((store: typeof mockAuthStore) => ({
      user: ref(store.user),
      isAuthenticated: computed(() => store.isAuthenticated),
      isAdmin: computed(() => store.isAdmin),
      isSuperAdmin: computed(() => store.isSuperAdmin),
      isStudent: computed(() => store.isStudent),
      isImpersonating: computed(() => store.isImpersonating)
    }))
  }
})

vi.mock('@/services/authService', () => ({
  authService: {
    login: vi.fn(),
    fetchUser: vi.fn(),
    logout: vi.fn(),
    refreshToken: vi.fn(),
    impersonateUser: vi.fn(),
    stopImpersonating: vi.fn()
  }
}))

import { useAuth } from '@/composables/useAuth'
import { authService } from '@/services/authService'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: { template: '<div />' } },
      { path: '/login', component: { template: '<div />' } },
      { path: '/spaces', component: { template: '<div />' } },
      { path: '/dashboard', component: { template: '<div />' } },
      { path: '/admin/users', component: { template: '<div />' } }
    ]
  })
}

const TestComponent = defineComponent({
  setup() {
    const auth = useAuth()
    return { auth }
  },
  template: '<div />'
})

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('useAuth composable', () => {
  let router: ReturnType<typeof makeRouter>

  beforeEach(() => {
    setActivePinia(createPinia())
    router = makeRouter()

    mockAuthStore = {
      user: null,
      isAuthenticated: false,
      isAdmin: false,
      isSuperAdmin: false,
      isStudent: false,
      isImpersonating: false,
      fetchUser: vi.fn(),
      logout: vi.fn(),
      impersonateUser: vi.fn(),
      stopImpersonating: vi.fn()
    }

    vi.clearAllMocks()
  })

  // --------------------------------------------------------------------------
  // provides current user
  // --------------------------------------------------------------------------

  it('provides current user as null when not authenticated', () => {
    const wrapper = mount(TestComponent, {
      global: { plugins: [router] }
    })

    // auth.user and auth.isAuthenticated are refs — access .value
    expect(wrapper.vm.auth.user.value).toBeNull()
    expect(wrapper.vm.auth.isAuthenticated.value).toBe(false)
  })

  it('provides current user object when store has a user', () => {
    const fakeUser = { id: '1', email: 'alice@test.com', full_name: 'Alice', role: 'student' }
    mockAuthStore.user = fakeUser
    mockAuthStore.isAuthenticated = true

    const wrapper = mount(TestComponent, {
      global: { plugins: [router] }
    })

    expect(wrapper.vm.auth.user.value).toEqual(fakeUser)
  })

  it('exposes isAdmin, isSuperAdmin, isStudent, isImpersonating refs from store', () => {
    mockAuthStore.isAdmin = true
    mockAuthStore.isSuperAdmin = false
    mockAuthStore.isStudent = false
    mockAuthStore.isImpersonating = true

    const wrapper = mount(TestComponent, {
      global: { plugins: [router] }
    })

    expect(wrapper.vm.auth.isAdmin.value).toBe(true)
    expect(wrapper.vm.auth.isSuperAdmin.value).toBe(false)
    expect(wrapper.vm.auth.isStudent.value).toBe(false)
    expect(wrapper.vm.auth.isImpersonating.value).toBe(true)
  })

  // --------------------------------------------------------------------------
  // does not redirect when authenticated
  // --------------------------------------------------------------------------

  it('does not redirect on mount — useAuth has no route guard', async () => {
    mockAuthStore.isAuthenticated = true
    mockAuthStore.user = { id: '2', email: 'bob@test.com', full_name: 'Bob', role: 'student' }

    await router.push('/spaces')

    mount(TestComponent, {
      global: { plugins: [router] }
    })

    // useAuth has no mount-time guard; current route stays unchanged
    expect(router.currentRoute.value.path).toBe('/spaces')
  })

  // --------------------------------------------------------------------------
  // logout calls store logout and redirects
  // --------------------------------------------------------------------------

  it('logout calls authStore.logout() exactly once', async () => {
    mockAuthStore.logout.mockResolvedValue(undefined)
    await router.push('/spaces')

    const wrapper = mount(TestComponent, {
      global: { plugins: [router] }
    })

    await wrapper.vm.auth.logout()
    await flushPromises()

    expect(mockAuthStore.logout).toHaveBeenCalledOnce()
  })

  it('logout redirects to /login after calling store logout', async () => {
    mockAuthStore.logout.mockResolvedValue(undefined)
    await router.push('/spaces')

    const wrapper = mount(TestComponent, {
      global: { plugins: [router] }
    })

    await wrapper.vm.auth.logout()
    await flushPromises()

    expect(router.currentRoute.value.path).toBe('/login')
  })

  // --------------------------------------------------------------------------
  // login routing
  // --------------------------------------------------------------------------

  it('login calls authService.login with form data and returns true on success', async () => {
    vi.mocked(authService.login).mockResolvedValue(true)
    mockAuthStore.fetchUser.mockResolvedValue(undefined)
    mockAuthStore.isAdmin = false

    const wrapper = mount(TestComponent, {
      global: { plugins: [router] }
    })

    const formData = new FormData()
    formData.append('username', 'student@test.com')
    formData.append('password', 'secret')

    const result = await wrapper.vm.auth.login(formData)
    await flushPromises()

    expect(result).toBe(true)
    expect(authService.login).toHaveBeenCalledWith(formData)
  })

  it('login calls authStore.fetchUser() after successful API call', async () => {
    vi.mocked(authService.login).mockResolvedValue(true)
    mockAuthStore.fetchUser.mockResolvedValue(undefined)

    const wrapper = mount(TestComponent, {
      global: { plugins: [router] }
    })

    await wrapper.vm.auth.login(new FormData())
    await flushPromises()

    expect(mockAuthStore.fetchUser).toHaveBeenCalledOnce()
  })

  it('login redirects non-admin to /spaces on success', async () => {
    vi.mocked(authService.login).mockResolvedValue(true)
    mockAuthStore.fetchUser.mockResolvedValue(undefined)
    mockAuthStore.isAdmin = false

    await router.push('/login')

    const wrapper = mount(TestComponent, {
      global: { plugins: [router] }
    })

    await wrapper.vm.auth.login(new FormData())
    await flushPromises()

    expect(router.currentRoute.value.path).toBe('/spaces')
  })

  it('login redirects admin to /dashboard on success', async () => {
    vi.mocked(authService.login).mockResolvedValue(true)
    mockAuthStore.fetchUser.mockResolvedValue(undefined)
    mockAuthStore.isAdmin = true

    await router.push('/login')

    const wrapper = mount(TestComponent, {
      global: { plugins: [router] }
    })

    await wrapper.vm.auth.login(new FormData())
    await flushPromises()

    expect(router.currentRoute.value.path).toBe('/dashboard')
  })

  it('login returns false and does not navigate when authService returns false', async () => {
    vi.mocked(authService.login).mockResolvedValue(false)
    await router.push('/login')

    const wrapper = mount(TestComponent, {
      global: { plugins: [router] }
    })

    const result = await wrapper.vm.auth.login(new FormData())
    await flushPromises()

    expect(result).toBe(false)
    expect(mockAuthStore.fetchUser).not.toHaveBeenCalled()
    expect(router.currentRoute.value.path).toBe('/login')
  })

  // --------------------------------------------------------------------------
  // impersonate / stopImpersonating
  // --------------------------------------------------------------------------

  it('impersonate navigates to /spaces when store returns true', async () => {
    mockAuthStore.impersonateUser.mockResolvedValue(true)
    await router.push('/')

    const wrapper = mount(TestComponent, {
      global: { plugins: [router] }
    })

    await wrapper.vm.auth.impersonate('user-abc')
    await flushPromises()

    expect(mockAuthStore.impersonateUser).toHaveBeenCalledWith('user-abc')
    expect(router.currentRoute.value.path).toBe('/spaces')
  })

  it('impersonate does not navigate when store returns false', async () => {
    mockAuthStore.impersonateUser.mockResolvedValue(false)
    await router.push('/')

    const wrapper = mount(TestComponent, {
      global: { plugins: [router] }
    })

    await wrapper.vm.auth.impersonate('user-abc')
    await flushPromises()

    expect(router.currentRoute.value.path).toBe('/')
  })

  it('stopImpersonating calls store method and navigates to /admin/users', async () => {
    mockAuthStore.stopImpersonating.mockResolvedValue(undefined)
    await router.push('/spaces')

    const wrapper = mount(TestComponent, {
      global: { plugins: [router] }
    })

    await wrapper.vm.auth.stopImpersonating()
    await flushPromises()

    expect(mockAuthStore.stopImpersonating).toHaveBeenCalledOnce()
    expect(router.currentRoute.value.path).toBe('/admin/users')
  })
})

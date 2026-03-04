<script setup lang="ts">
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import { useAuth } from '../composables/useAuth'
import { useKeyboardShortcuts } from '../composables/useKeyboardShortcuts'
import { useCommandPalette } from '../composables/useCommandPalette'
import { useFormValidation } from '../composables/useFormValidation'
import { required, url as urlRule } from '../utils/validators'
import { useI18n } from 'vue-i18n'
import iconUser from '../assets/iconUser.png'
import api from '../api'

// Components — Stream 1
import ThemeToggle from '../components/common/ThemeToggle.vue'
import LanguageSwitcher from '../components/common/LanguageSwitcher.vue'
// Components — Stream 3
import BreadcrumbNav from '../components/common/BreadcrumbNav.vue'
// Components — Stream 6
import NotificationCenter from '../components/common/NotificationCenter.vue'
import CommandPalette from '../components/common/CommandPalette.vue'
import KeyboardShortcutsHelp from '../components/common/KeyboardShortcutsHelp.vue'
import ErrorBoundary from '../components/common/ErrorBoundary.vue'
import NetworkStatus from '../components/common/NetworkStatus.vue'

const { t } = useI18n()
const { user, logout, isImpersonating, stopImpersonating, isAdmin, isStudent } = useAuth()
const route = useRoute()

// Stream 6: Command Palette + Keyboard Shortcuts
const { open: openPalette } = useCommandPalette()
const { isHelpOpen: shortcutsOpen, register, registerDefaults } = useKeyboardShortcuts()
registerDefaults()
register({
  keys: 'Ctrl+K',
  label: 'commandPalette',
  scope: 'global',
  action: () => openPalette(),
})

// Profile Edit State
const showProfileModal = ref(false)
const editForm = ref({
  full_name: '',
  avatar_url: ''
})
const editLoading = ref(false)

// Stream 7: Profile form validation
const profileValidation = useFormValidation({
  full_name: { rules: [required(t('validation.required', { field: t('profile.displayName') }))] },
  avatar_url: { rules: [urlRule(t('validation.url'))] },
})

const openProfileModal = () => {
  editForm.value.full_name = user.value?.full_name || ''
  editForm.value.avatar_url = user.value?.avatar_url || ''
  profileValidation.reset()
  showProfileModal.value = true
}

const handleAvatarUpload = async (event: Event) => {
  const input = event.target as HTMLInputElement
  if (input.files && input.files[0]) {
    const file = input.files[0]
    if (file.size > 2 * 1024 * 1024) {
      alert('File size exceeds 2MB limit.')
      return
    }
    if (!['image/jpeg', 'image/png', 'image/jpg'].includes(file.type)) {
      alert('Only JPG and PNG files are allowed.')
      return
    }

    const formData = new FormData()
    formData.append('file', file)

    editLoading.value = true
    try {
      const res = await api.post('/users/me/avatar', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      editForm.value.avatar_url = res.data.avatar_url
      if (user.value) {
        user.value.avatar_url = res.data.avatar_url
      }
    } catch (e) {
      console.error(e)
      alert('Failed to upload avatar')
    } finally {
      editLoading.value = false
    }
  }
}

const updateProfile = async () => {
  const valid = profileValidation.validateAll({
    full_name: editForm.value.full_name,
    avatar_url: editForm.value.avatar_url,
  })
  if (!valid) return

  editLoading.value = true
  try {
    const res = await api.put('/users/me', {
      full_name: editForm.value.full_name,
      avatar_url: editForm.value.avatar_url
    })
    if (user.value) {
      user.value.full_name = res.data.full_name
      user.value.avatar_url = res.data.avatar_url
    }
    showProfileModal.value = false
  } catch (e) {
    alert('Failed to update profile')
  } finally {
    editLoading.value = false
  }
}
</script>

<script lang="ts">
import ToastContainer from '../components/common/ToastContainer.vue'
export default {
  components: { ToastContainer }
}
</script>

<template>
  <ToastContainer />
  <div
    class="drawer lg:drawer-open"
    :class="{ 'border-4 border-error': isImpersonating }"
  >
    <input id="my-drawer-2" type="checkbox" class="drawer-toggle" />

    <!-- Impersonation Banner -->
    <div v-if="isImpersonating" class="fixed bottom-6 right-6 z-50 animate-bounce">
      <button @click="stopImpersonating()" class="btn btn-error shadow-lg gap-2">
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
          <polyline points="16 17 21 12 16 7"></polyline>
          <line x1="21" y1="12" x2="9" y2="12"></line>
        </svg>
        Exit Impersonation
      </button>
    </div>

    <div class="drawer-content flex flex-col bg-base-200">
      <!-- Navbar (mobile) -->
      <div class="w-full navbar bg-base-100 lg:hidden user-select-none">
        <div class="flex-none lg:hidden">
          <label for="my-drawer-2" class="btn btn-square btn-ghost">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" class="inline-block w-6 h-6 stroke-current">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"></path>
            </svg>
          </label>
        </div>
        <div class="flex-1 px-2 mx-2">
          <div @click="openProfileModal" class="avatar cursor-pointer mr-2">
            <div class="w-8 rounded-full ring ring-primary ring-offset-base-100 ring-offset-2">
              <img :src="user?.avatar_url || iconUser" />
            </div>
          </div>
          CoAgent Studio
        </div>
      </div>

      <!-- Network Status (Stream 6) -->
      <NetworkStatus />

      <!-- Page Content -->
      <main
        role="main"
        class="flex-1 overflow-y-auto"
        :class="{
          'p-6': !route.name?.toString().includes('room'),
          'overflow-y-hidden': route.name?.toString().includes('room')
        }"
      >
        <!-- Breadcrumb (Stream 3) -->
        <BreadcrumbNav v-if="!route.name?.toString().includes('room')" />

        <!-- Error Boundary (Stream 6) -->
        <ErrorBoundary>
          <router-view v-slot="{ Component }">
            <transition name="fade" mode="out-in">
              <component :is="Component" />
            </transition>
          </router-view>
        </ErrorBoundary>
      </main>

      <!-- Profile Modal (Stream 3: ARIA + Stream 7: validation) -->
      <dialog
        :class="{ 'modal-open': showProfileModal }"
        class="modal"
        role="dialog"
        aria-modal="true"
        :aria-labelledby="'profile-modal-title'"
      >
        <div class="modal-box">
          <h3 id="profile-modal-title" class="font-bold text-lg">{{ t('profile.editProfile') }}</h3>
          <div class="py-4">
            <div class="flex justify-center mb-4">
              <div class="avatar">
                <div class="w-24 rounded-full ring ring-primary ring-offset-base-100 ring-offset-2">
                  <img :src="editForm.avatar_url || iconUser" />
                </div>
              </div>
            </div>

            <div class="form-control w-full mb-2">
              <label class="label"><span class="label-text">{{ t('profile.displayName') }}</span></label>
              <input
                type="text"
                v-model="editForm.full_name"
                placeholder="John Doe"
                class="input input-bordered w-full"
                :class="{ 'input-error': profileValidation.touched.full_name && profileValidation.errors.full_name }"
                @blur="profileValidation.touchField('full_name', editForm.full_name)"
              />
              <label v-if="profileValidation.touched.full_name && profileValidation.errors.full_name" class="label">
                <span class="label-text-alt text-error">{{ profileValidation.errors.full_name }}</span>
              </label>
            </div>

            <div class="form-control w-full mb-2">
              <label class="label"><span class="label-text">{{ t('profile.avatarImage') }}</span></label>
              <input
                type="file"
                @change="handleAvatarUpload"
                accept="image/png, image/jpeg"
                class="file-input file-input-bordered w-full"
              />
              <label class="label">
                <span class="label-text-alt">{{ t('profile.maxSize') }}</span>
              </label>
            </div>

            <div class="divider text-xs">OR</div>

            <div class="form-control w-full mb-2">
              <label class="label"><span class="label-text">{{ t('profile.avatarUrl') }}</span></label>
              <input
                type="text"
                v-model="editForm.avatar_url"
                placeholder="https://..."
                class="input input-bordered w-full"
                :class="{ 'input-error': profileValidation.touched.avatar_url && profileValidation.errors.avatar_url }"
                @blur="profileValidation.touchField('avatar_url', editForm.avatar_url)"
              />
              <label v-if="profileValidation.touched.avatar_url && profileValidation.errors.avatar_url" class="label">
                <span class="label-text-alt text-error">{{ profileValidation.errors.avatar_url }}</span>
              </label>
              <label v-else class="label">
                <span class="label-text-alt">{{ t('profile.leaveEmpty') }}</span>
              </label>
            </div>
          </div>

          <div class="modal-action flex justify-between items-center w-full">
            <button class="btn btn-error btn-outline btn-sm" @click="logout">{{ t('profile.logout') }}</button>
            <div class="flex gap-2">
              <button class="btn btn-ghost" @click="showProfileModal = false">{{ t('common.cancel') }}</button>
              <button class="btn btn-primary" @click="updateProfile" :disabled="editLoading">
                {{ t('common.save') }}
              </button>
            </div>
          </div>
        </div>
      </dialog>
    </div>

    <!-- Sidebar -->
    <div class="drawer-side">
      <label for="my-drawer-2" aria-label="close sidebar" class="drawer-overlay"></label>
      <ul
        role="navigation"
        aria-label="Main navigation"
        class="menu p-4 w-80 min-h-full bg-base-100 text-base-content flex flex-col justify-between"
      >
        <div>
          <!-- Desktop Avatar & Brand -->
          <li class="mb-4">
            <div
              @click="openProfileModal"
              class="flex flex-row items-center gap-4 hover:bg-base-200 p-2 rounded-lg cursor-pointer"
            >
              <div class="avatar">
                <div class="w-12 rounded-full ring ring-primary ring-offset-base-100 ring-offset-2">
                  <img :src="user?.avatar_url || iconUser" />
                </div>
              </div>
              <div>
                <div class="font-bold text-lg text-primary">
                  {{ user?.full_name || 'User' }}
                </div>
                <div class="text-xs opacity-50">CoAgent Studio</div>
              </div>
            </div>
          </li>

          <!-- Notification Center (Stream 6) -->
          <li class="mb-2">
            <NotificationCenter />
          </li>

          <!-- Home -->
          <li>
            <router-link to="/spaces" active-class="active">{{ t('nav.home') }}</router-link>
          </li>

          <!-- PLATFORM section (non-students only) -->
          <template v-if="!isStudent">
            <div class="divider text-xs opacity-50 uppercase tracking-widest">{{ t('nav.platform') }}</div>
            <li>
              <router-link to="/agents" active-class="active">{{ t('nav.agentLab') }}</router-link>
            </li>
            <li>
              <router-link to="/my-agents" active-class="active">{{ t('nav.myAgents') }}</router-link>
            </li>
            <li>
              <router-link to="/platform/workflows" active-class="active">{{ t('nav.workflows') }}</router-link>
            </li>
            <li>
              <router-link to="/platform/triggers" active-class="active">{{ t('nav.triggers') }}</router-link>
            </li>
            <li>
              <router-link to="/platform/knowledge" active-class="active">{{ t('nav.knowledgeEngine') }}</router-link>
            </li>
          </template>

          <!-- SPACES section -->
          <div class="divider text-xs opacity-50 uppercase tracking-widest">{{ t('nav.spaces') }}</div>
          <li>
            <router-link to="/spaces" active-class="active">{{ t('nav.mySpaces') }}</router-link>
          </li>

          <!-- SYSTEM section -->
          <div class="divider text-xs opacity-50 uppercase tracking-widest">{{ t('nav.system') }}</div>
          <li v-if="!isStudent">
            <router-link to="/my-keys" active-class="active">{{ t('nav.myApiKeys') }}</router-link>
          </li>
          <li v-if="isAdmin">
            <router-link to="/analytics" active-class="active">{{ t('nav.analytics') }}</router-link>
          </li>

          <!-- ADMIN section (admin only) -->
          <template v-if="isAdmin">
            <div class="divider text-xs opacity-50 uppercase tracking-widest">{{ t('nav.admin') }}</div>
            <li>
              <router-link to="/dashboard" active-class="active">{{ t('nav.dashboard') }}</router-link>
            </li>
            <li>
              <router-link to="/admin/users" active-class="active">{{ t('nav.users') }}</router-link>
            </li>
            <li>
              <router-link to="/admin/system-agents" active-class="active">{{ t('nav.systemAgents') }}</router-link>
            </li>
            <li>
              <router-link to="/admin/database" active-class="active">{{ t('nav.database') }}</router-link>
            </li>
          </template>

          <div class="divider"></div>

          <li><a @click="openProfileModal">{{ t('nav.settings') }}</a></li>
        </div>

        <!-- Sidebar Bottom: Theme + Language (Stream 1) -->
        <div class="flex items-center justify-center gap-2 py-2 border-t border-base-200">
          <ThemeToggle />
          <LanguageSwitcher />
          <kbd class="kbd kbd-sm cursor-pointer opacity-50 hover:opacity-100" @click="openPalette" title="Ctrl+K">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </kbd>
        </div>
      </ul>
    </div>
  </div>

  <!-- Global Overlays (Stream 6) -->
  <CommandPalette />
  <KeyboardShortcutsHelp v-model="shortcutsOpen" />
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useAuth } from '../composables/useAuth'
import { useFormValidation } from '../composables/useFormValidation'
import { required, minLength } from '../utils/validators'
import { useI18n } from 'vue-i18n'
import ThemeToggle from '../components/common/ThemeToggle.vue'
import LanguageSwitcher from '../components/common/LanguageSwitcher.vue'

const { t } = useI18n()

const credentials = ref({
  username: '',
  password: ''
})

const errorMessage = ref('')
const isLoading = ref(false)
const isAdminMode = ref(false)
const { login } = useAuth()

const {
  errors,
  touched,
  touchField,
  validateAll,
  reset: resetValidation
} = useFormValidation({
  username: { rules: [required(t('validation.required', { field: t('login.username') }))] },
  password: {
    rules: [
      required(t('validation.required', { field: t('login.password') })),
      minLength(4, t('validation.minLength', { field: t('login.password'), min: 4 }))
    ]
  }
})

const formValid = computed(() => {
  return credentials.value.username.trim().length > 0 && credentials.value.password.length >= 4
})

const toggleAdminMode = () => {
  isAdminMode.value = !isAdminMode.value
  credentials.value = { username: '', password: '' }
  errorMessage.value = ''
  resetValidation()
}

const handleLogin = async () => {
  const valid = validateAll({
    username: credentials.value.username,
    password: credentials.value.password
  })
  if (!valid) return

  isLoading.value = true
  errorMessage.value = ''

  const formData = new FormData()
  formData.append('username', credentials.value.username)
  formData.append('password', credentials.value.password)

  const success = await login(formData)
  if (!success) {
    errorMessage.value = t('login.invalidCredentials')
  }
  isLoading.value = false
}
</script>

<template>
  <div class="min-h-screen flex items-center justify-center bg-base-200 relative">
    <!-- Theme/Language controls -->
    <div class="absolute top-4 right-4 flex items-center gap-2">
      <ThemeToggle />
      <LanguageSwitcher />
    </div>

    <div class="card w-full max-w-md bg-base-100 shadow-xl">
      <div class="card-body">
        <!-- Header -->
        <div class="text-center mb-6">
          <h1 class="text-3xl font-bold text-primary">
            {{ isAdminMode ? t('login.adminTitle') : t('login.title') }}
          </h1>
          <p class="text-base-content/60 mt-2 text-sm">
            {{ isAdminMode ? t('login.adminSubtitle') : t('login.subtitle') }}
          </p>
        </div>

        <!-- Google OAuth (user mode only) -->
        <button v-if="!isAdminMode" class="btn btn-outline w-full gap-2">
          <svg
            class="w-5 h-5"
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill="currentColor"
          >
            <path
              d="M20.283 10.356h-8.327v3.451h4.792c-.446 2.193-2.313 3.453-4.792 3.453a5.27 5.27 0 0 1-5.279-5.28 5.27 5.27 0 0 1 5.279-5.279c1.259 0 2.397.447 3.29 1.178l2.6-2.599c-1.584-1.381-3.615-2.233-5.89-2.233a8.908 8.908 0 0 0-8.934 8.934 8.907 8.907 0 0 0 8.934 8.934c4.467 0 8.529-3.249 8.529-8.934 0-.528-.081-1.097-.202-1.625z"
            />
          </svg>
          {{ t('login.continueWithGoogle') }}
        </button>

        <div v-if="!isAdminMode" class="divider text-xs text-base-content/40">
          {{ t('login.orAccessWithId') }}
        </div>

        <!-- Login Form -->
        <form @submit.prevent="handleLogin" class="space-y-4">
          <div class="form-control">
            <label class="label">
              <span class="label-text">{{ t('login.username') }}</span>
            </label>
            <input
              type="text"
              v-model="credentials.username"
              :placeholder="isAdminMode ? 'admin' : t('login.username')"
              class="input input-bordered w-full"
              :class="{ 'input-error': touched.username && errors.username }"
              @blur="touchField('username', credentials.username)"
              required
            />
            <label v-if="touched.username && errors.username" class="label">
              <span class="label-text-alt text-error">{{ errors.username }}</span>
            </label>
          </div>

          <div class="form-control">
            <label class="label">
              <span class="label-text">{{ t('login.password') }}</span>
            </label>
            <input
              type="password"
              v-model="credentials.password"
              placeholder="••••••••"
              class="input input-bordered w-full"
              :class="{ 'input-error': touched.password && errors.password }"
              @blur="touchField('password', credentials.password)"
              required
            />
            <label v-if="touched.password && errors.password" class="label">
              <span class="label-text-alt text-error">{{ errors.password }}</span>
            </label>
          </div>

          <!-- Error Message -->
          <div v-if="errorMessage" class="alert alert-error py-2 text-sm">
            {{ errorMessage }}
          </div>

          <!-- Submit -->
          <button type="submit" class="btn btn-primary w-full" :disabled="isLoading || !formValid">
            <span v-if="isLoading" class="loading loading-spinner loading-sm"></span>
            {{ isLoading ? t('login.signingIn') : t('login.signIn') }}
          </button>
        </form>

        <!-- Admin toggle link -->
        <div class="text-center mt-4">
          <button class="btn btn-ghost btn-sm text-base-content/50" @click="toggleAdminMode">
            {{ isAdminMode ? t('login.userLogin') : t('login.adminLogin') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

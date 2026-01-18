<script setup lang="ts">
import { ref, computed } from 'vue'
import { useAuth } from '../composables/useAuth'
import CyberDroid from '../components/CyberDroid.vue'

// State for Login
const credentials = ref({
  username: '',
  password: ''
})

const errorMessage = ref('')
const isLoading = ref(false)
const { login } = useAuth() // Use Composable

// Admin Secret Trigger Logic
const secretCount = ref(0)
const isAdminMode = ref(false)

const handleSecretTrigger = () => {
  secretCount.value++
  if (secretCount.value >= 3) {
    isAdminMode.value = !isAdminMode.value
    secretCount.value = 0
    // Reset credentials when switching modes for security/convenience
    credentials.value = { username: '', password: '' }
    errorMessage.value = ''
  }
}

// Dynamic classes based on mode
const themeColors = computed(() => {
  return isAdminMode.value
    ? {
        // Admin: Red/Gold/Dark scheme
        wrapper: 'from-red-900/40 to-orange-900/40',
        border: 'border-red-500/20 group-hover:border-red-500/40',
        textGradient: 'from-red-500 via-orange-500 to-yellow-500',
        glow: 'shadow-[0_0_40px_rgba(220,38,38,0.3)]',
        button:
          'from-red-700 to-orange-700 hover:from-red-600 hover:to-orange-600 shadow-red-900/50',
        inputFocus:
          'focus:border-red-500/50 focus:bg-red-900/10 focus:shadow-[0_0_15px_rgba(220,38,38,0.15)]',
        meshPrimary: 'bg-red-600/20',
        meshSecondary: 'bg-orange-600/20'
      }
    : {
        // Guest: Cyan/Purple/Blue scheme (Original)
        wrapper: 'from-cyan-500 to-purple-600',
        border: 'border-white/10 group-hover:border-white/20',
        textGradient: 'from-cyan-400 via-blue-400 to-purple-500',
        glow: 'shadow-2xl',
        button:
          'from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 shadow-cyan-500/20',
        inputFocus:
          'focus:border-cyan-500/50 focus:bg-cyan-500/10 focus:shadow-[0_0_15px_rgba(6,182,212,0.15)]',
        meshPrimary: 'bg-cyan-600/20',
        meshSecondary: 'bg-violet-600/20'
      }
})

// Combined login handler
const handleLogin = async () => {
  isLoading.value = true
  await new Promise((r) => setTimeout(r, 600))

  const formData = new FormData()
  formData.append('username', credentials.value.username)
  formData.append('password', credentials.value.password)

  const success = await login(formData) // useAuth handles routing
  if (!success) {
    errorMessage.value = 'Invalid credentials'
    isLoading.value = false
  }
}
</script>

<template>
  <!-- Global Container with Cyberpunk Background -->
  <div
    class="min-h-screen w-full flex items-center justify-center bg-black overflow-hidden relative selection:bg-cyan-500/30"
  >
    <!-- Animated Background Mesh (Fallback / Base Layer) -->
    <div
      class="absolute inset-0 z-0 overflow-hidden pointer-events-none transition-colors duration-1000"
    >
      <div
        :class="[
          'absolute top-[-20%] left-[-10%] w-[60%] h-[60%] rounded-full blur-[120px] animate-pulse-slow transition-colors duration-1000',
          themeColors.meshPrimary
        ]"
      ></div>
      <div
        :class="[
          'absolute bottom-[-20%] right-[-10%] w-[60%] h-[60%] rounded-full blur-[120px] animate-pulse-slow delay-1000 transition-colors duration-1000',
          themeColors.meshSecondary
        ]"
      ></div>
      <div
        class="absolute top-[30%] left-[40%] w-[40%] h-[40%] bg-blue-500/10 rounded-full blur-[100px] animate-float"
      ></div>
      <!-- Grid overlay -->
      <div
        class="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAiIGhlaWdodD0iNDAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PGRlZnM+PHBhdHRlcm4gaWQ9ImdyaWQiIHdpZHRoPSI0MCIgaGVpZ2h0PSI0MCIgcGF0dGVyblVuaXRzPSJ1c2VyU3BhY2VPblVzZSI+PHBhdGggZD0iTTAgNDBMMCAwSDEiIHN0cm9rZT0icmdiYSgyNTUsIDI1NSwgMjU1LCAwLjAzKSIgZmlsbD0ibm9uZSIvPjwvcGF0dGVybj48L2RlZnM+PHJlY3Qgd2lkdGg9IjEwMCUiIGhlaWdodD0iMTAwJSIgZmlsbD0idXJsKCNncmlkKSIvPjwvc3ZnPg==')] opacity-20"
      ></div>
    </div>

    <!-- 3D Three.js Layer (Extracted Component) -->
    <CyberDroid :is-admin-mode="isAdminMode" :is-loading="isLoading" />

    <!-- Main Card Container -->
    <div class="relative z-10 w-full max-w-md p-6 animate-fade-in-up">
      <!-- Glass Effect Wrapper -->
      <div class="relative group">
        <!-- Glow border effect -->
        <div
          :class="[
            'absolute -inset-0.5 bg-gradient-to-r rounded-2xl opacity-30 group-hover:opacity-50 blur transition-all duration-1000',
            themeColors.wrapper
          ]"
        ></div>

        <div
          :class="[
            'relative bg-black/40 backdrop-blur-xl border rounded-2xl p-8 transition-all duration-500',
            themeColors.border,
            themeColors.glow
          ]"
        >
          <!-- Header Section -->
          <div class="text-center mb-8">
            <h1
              @click="handleSecretTrigger"
              :class="[
                'text-4xl font-black mb-4 tracking-tight text-transparent bg-clip-text bg-gradient-to-r animate-gradient-x select-none cursor-default pb-2 transition-all duration-1000',
                themeColors.textGradient
              ]"
            >
              {{ isAdminMode ? 'SYSTEM CORE' : 'CoAgent Studio' }}
            </h1>
            <p
              class="text-white/40 text-sm font-light tracking-widest uppercase transition-all duration-300"
            >
              {{ isAdminMode ? 'Administrator Access Level 0' : 'AI-Native Learning Platform' }}
            </p>
          </div>

          <!-- Login Form -->
          <div class="space-y-6">
            <button
              v-if="!isAdminMode"
              class="w-full relative group overflow-hidden rounded-lg p-[1px] focus:outline-none focus:ring-2 focus:ring-cyan-400/50"
            >
              <div
                class="absolute inset-0 bg-gradient-to-r from-cyan-500/20 to-purple-500/20 group-hover:from-cyan-500/40 group-hover:to-purple-500/40 transition-all duration-300"
              ></div>
              <div
                class="relative bg-black/50 hover:bg-black/30 backdrop-blur-sm rounded-lg py-3 px-4 flex items-center justify-center gap-3 transition-all duration-300 border border-white/10 group-hover:border-white/20"
              >
                <svg
                  class="w-5 h-5 text-current"
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 24 24"
                  fill="currentColor"
                >
                  <path
                    d="M20.283 10.356h-8.327v3.451h4.792c-.446 2.193-2.313 3.453-4.792 3.453a5.27 5.27 0 0 1-5.279-5.28 5.27 5.27 0 0 1 5.279-5.279c1.259 0 2.397.447 3.29 1.178l2.6-2.599c-1.584-1.381-3.615-2.233-5.89-2.233a8.908 8.908 0 0 0-8.934 8.934 8.907 8.907 0 0 0 8.934 8.934c4.467 0 8.529-3.249 8.529-8.934 0-.528-.081-1.097-.202-1.625z"
                  />
                </svg>
                <span class="text-sm font-medium text-gray-200 group-hover:text-white"
                  >Continue with Google</span
                >
              </div>
            </button>

            <div v-if="!isAdminMode" class="relative flex items-center py-2">
              <div class="flex-grow border-t border-white/10"></div>
              <span class="flex-shrink-0 mx-4 text-xs text-white/30 uppercase tracking-widest"
                >Or access with ID</span
              >
              <div class="flex-grow border-t border-white/10"></div>
            </div>

            <form @submit.prevent="handleLogin" class="space-y-4">
              <div class="space-y-1">
                <label
                  :class="[
                    'text-xs font-medium ml-1 transition-colors',
                    isAdminMode ? 'text-red-400/70' : 'text-cyan-200/70'
                  ]"
                >
                  {{ isAdminMode ? 'ROOT USER' : 'IDENTITY' }}
                </label>
                <input
                  type="text"
                  v-model="credentials.username"
                  :placeholder="isAdminMode ? 'root' : 'Enter username'"
                  :class="[
                    'w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-sm text-white placeholder-white/20 focus:outline-none transition-all duration-300',
                    themeColors.inputFocus
                  ]"
                  required
                />
              </div>

              <div class="space-y-1">
                <label
                  :class="[
                    'text-xs font-medium ml-1 transition-colors',
                    isAdminMode ? 'text-red-400/70' : 'text-cyan-200/70'
                  ]"
                >
                  {{ isAdminMode ? 'ACCESS KEY' : 'PASSPHRASE' }}
                </label>
                <input
                  type="password"
                  v-model="credentials.password"
                  placeholder="••••••••"
                  :class="[
                    'w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-sm text-white placeholder-white/20 focus:outline-none transition-all duration-300',
                    themeColors.inputFocus
                  ]"
                  required
                />
              </div>

              <div
                v-if="errorMessage"
                class="text-red-400 text-xs text-center bg-red-500/10 border border-red-500/20 rounded py-2 animate-shake"
              >
                {{ errorMessage }}
              </div>

              <button
                type="submit"
                :disabled="isLoading"
                :class="[
                  'w-full bg-gradient-to-r text-white font-bold py-3 px-4 rounded-lg shadow-lg transition-all duration-300 transform hover:scale-[1.02] active:scale-[0.98] disabled:opacity-70 disabled:cursor-not-allowed flex items-center justify-center relative overflow-hidden',
                  themeColors.button
                ]"
              >
                <span class="relative z-10">{{
                  isLoading
                    ? 'AUTHENTICATING...'
                    : isAdminMode
                      ? 'INITIATE OVERRIDE'
                      : 'ACCESS SYSTEM'
                }}</span>
                <div v-if="isLoading" class="absolute inset-0 bg-white/20 animate-pulse"></div>
              </button>
            </form>

            <div class="text-center">
              <p class="text-[10px] text-white/20 uppercase tracking-widest mt-4">
                {{
                  isAdminMode
                    ? 'Authorized Personnel Only • Security Level 5'
                    : 'Restricted Access Area • Invite Only'
                }}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px) scale(0.95);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}
.animate-fade-in-up {
  animation: fadeInUp 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

@keyframes pulseSlow {
  0%,
  100% {
    opacity: 0.3;
    transform: scale(1);
  }
  50% {
    opacity: 0.5;
    transform: scale(1.1);
  }
}
.animate-pulse-slow {
  animation: pulseSlow 6s ease-in-out infinite;
}

@keyframes float {
  0%,
  100% {
    transform: translate(0, 0);
  }
  33% {
    transform: translate(30px, -30px);
  }
  66% {
    transform: translate(-20px, 20px);
  }
}
.animate-float {
  animation: float 15s ease-in-out infinite;
}

@keyframes gradientX {
  0% {
    background-position: 0% 50%;
  }
  50% {
    background-position: 100% 50%;
  }
  100% {
    background-position: 0% 50%;
  }
}
.animate-gradient-x {
  background-size: 200% 200%;
  animation: gradientX 5s ease infinite;
}

@keyframes shake {
  0%,
  100% {
    transform: translateX(0);
  }
  25% {
    transform: translateX(-4px);
  }
  75% {
    transform: translateX(4px);
  }
}
.animate-shake {
  animation: shake 0.3s ease-in-out;
}
</style>

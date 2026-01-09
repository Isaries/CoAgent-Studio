<script setup lang="ts">
import { ref } from 'vue'
import { useAuthStore } from '../stores/auth'

// State for Guest Login
const guestCredentials = ref({
  username: '',
  password: ''
})

// State for Admin Login
const adminCredentials = ref({
  username: '',
  password: ''
})

const errorMessage = ref('')
const showAdminLogin = ref(false)
const secretCount = ref(0)
const authStore = useAuthStore()

const handleSecretTrigger = () => {
  secretCount.value++
  // Require 3 clicks to reveal
  if (secretCount.value >= 3) {
    showAdminLogin.value = true
    secretCount.value = 0
  }
}

// Unified login handler
const handleLogin = async (type: 'guest' | 'admin') => {
  const credentials = type === 'admin' ? adminCredentials.value : guestCredentials.value

  const success = await authStore.login(credentials.username, credentials.password)
  if (!success) {
    errorMessage.value = 'Invalid credentials'
  }
}
</script>

<template>
  <div class="hero min-h-screen bg-base-200">
    <div class="hero-content text-center">
      <div class="max-w-md">
        <!-- Secret Trigger on Title -->
        <h1 class="text-5xl font-bold select-none cursor-default" @click="handleSecretTrigger">
          CoAgent Studio
        </h1>
        <p class="py-6">The AI-Native Learning Platform.</p>

        <div class="flex flex-col gap-4">
          <button class="btn btn-outline gap-2" disabled>
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="currentColor"
            >
              <path
                d="M20.283 10.356h-8.327v3.451h4.792c-.446 2.193-2.313 3.453-4.792 3.453a5.27 5.27 0 0 1-5.279-5.28 5.27 5.27 0 0 1 5.279-5.279c1.259 0 2.397.447 3.29 1.178l2.6-2.599c-1.584-1.381-3.615-2.233-5.89-2.233a8.908 8.908 0 0 0-8.934 8.934 8.907 8.907 0 0 0 8.934 8.934c4.467 0 8.529-3.249 8.529-8.934 0-.528-.081-1.097-.202-1.625z"
              />
            </svg>
            Continue with Google
          </button>

          <div class="divider">OR</div>

          <!-- Guest Login Form -->
          <div class="card bg-base-100 shadow-xl">
            <form class="card-body p-4" @submit.prevent="handleLogin('guest')">
              <h2 class="card-title text-sm uppercase opacity-50 justify-center">Guest Login</h2>
              <div class="form-control">
                <input
                  type="text"
                  v-model="guestCredentials.username"
                  placeholder="Username"
                  class="input input-bordered input-sm"
                  required
                />
              </div>
              <div class="form-control mt-2">
                <input
                  type="password"
                  v-model="guestCredentials.password"
                  placeholder="Password"
                  class="input input-bordered input-sm"
                  required
                />
              </div>
              <div v-if="errorMessage" class="text-error text-xs mt-2">{{ errorMessage }}</div>
              <button class="btn btn-primary btn-sm mt-4">Login</button>
            </form>
          </div>

          <p class="text-xs opacity-50 mt-2">Currently Invite Only</p>
        </div>

        <!-- Hidden Admin Form (Cyberpunk / AI-Native Style) -->
        <div
          v-if="showAdminLogin"
          class="fixed inset-0 z-50 flex items-center justify-center bg-black/90 backdrop-blur-sm overflow-hidden"
          @click.self="showAdminLogin = false"
        >
          <!-- Context: Animated Background Mesh using CSS shapes/gradients -->
          <div class="absolute inset-0 z-0 overflow-hidden pointer-events-none">
            <div
              class="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] bg-cyan-500/20 rounded-full blur-[120px] animate-pulse-slow"
            ></div>
            <div
              class="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] bg-purple-500/20 rounded-full blur-[120px] animate-pulse-slow delay-1000"
            ></div>
            <div
              class="absolute top-[40%] left-[40%] w-[30%] h-[30%] bg-blue-600/10 rounded-full blur-[100px] animate-float"
            ></div>
          </div>

          <!-- Glass Card -->
          <div
            class="relative z-10 w-full max-w-md p-1 rounded-2xl bg-gradient-to-br from-white/10 to-white/5 shadow-[0_0_40px_rgba(0,0,0,0.5)] backdrop-blur-xl border border-white/10 animate-fade-in-up"
          >
            <div class="bg-black/40 rounded-xl p-8 backdrop-blur-md h-full w-full">
              <!-- Header -->
              <div class="text-center mb-8">
                <div class="inline-block relative">
                  <h2
                    class="text-3xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-purple-500 mb-1 tracking-tight"
                  >
                    CoAgent
                  </h2>
                  <div
                    class="absolute -bottom-2 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-cyan-500 to-transparent opacity-50"
                  ></div>
                </div>
                <p class="text-cyan-100/50 text-xs mt-3 uppercase tracking-[0.2em] font-medium">
                  System Administration
                </p>
              </div>

              <form @submit.prevent="handleLogin('admin')" class="space-y-5">
                <div class="group">
                  <label
                    class="block text-xs uppercase tracking-wider text-cyan-200/60 mb-1.5 font-medium ml-1"
                    >Username</label
                  >
                  <input
                    type="text"
                    v-model="adminCredentials.username"
                    class="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-cyan-50 placeholder-cyan-200/20 transition-all duration-300 focus:outline-none focus:border-cyan-400/50 focus:bg-cyan-900/10 focus:shadow-[0_0_20px_rgba(34,211,238,0.2)]"
                    placeholder="Enter Identity"
                    required
                  />
                </div>

                <div class="group">
                  <label
                    class="block text-xs uppercase tracking-wider text-cyan-200/60 mb-1.5 font-medium ml-1"
                    >Password</label
                  >
                  <input
                    type="password"
                    v-model="adminCredentials.password"
                    class="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-cyan-50 placeholder-cyan-200/20 transition-all duration-300 focus:outline-none focus:border-purple-400/50 focus:bg-purple-900/10 focus:shadow-[0_0_20px_rgba(192,132,252,0.2)]"
                    placeholder="••••••••"
                    required
                  />
                </div>

                <div
                  v-if="errorMessage"
                  class="text-red-400 text-sm text-center bg-red-900/20 border border-red-500/20 rounded-lg p-2 animate-shake"
                >
                  {{ errorMessage }}
                </div>

                <div class="pt-4 flex items-center justify-between gap-4">
                  <button
                    type="button"
                    class="text-sm text-cyan-200/40 hover:text-cyan-200 transition-colors"
                    @click="showAdminLogin = false"
                  >
                    Cancel
                  </button>
                  <button
                    class="flex-1 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white font-bold py-3 px-6 rounded-lg shadow-lg shadow-cyan-900/50 transition-all duration-300 transform hover:scale-[1.02] active:scale-[0.98]"
                  >
                    Authenticate
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.select-none {
  user-select: none;
}

/* Animation Keyframes */
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
  animation: fadeInUp 0.5s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

@keyframes pulseSlow {
  0%,
  100% {
    opacity: 0.4;
    transform: scale(1);
  }
  50% {
    opacity: 0.6;
    transform: scale(1.1);
  }
}
.animate-pulse-slow {
  animation: pulseSlow 4s ease-in-out infinite;
}

@keyframes float {
  0%,
  100% {
    transform: translate(0, 0);
  }
  33% {
    transform: translate(30px, -50px);
  }
  66% {
    transform: translate(-20px, 20px);
  }
}
.animate-float {
  animation: float 10s ease-in-out infinite;
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

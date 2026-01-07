

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
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M20.283 10.356h-8.327v3.451h4.792c-.446 2.193-2.313 3.453-4.792 3.453a5.27 5.27 0 0 1-5.279-5.28 5.27 5.27 0 0 1 5.279-5.279c1.259 0 2.397.447 3.29 1.178l2.6-2.599c-1.584-1.381-3.615-2.233-5.89-2.233a8.908 8.908 0 0 0-8.934 8.934 8.907 8.907 0 0 0 8.934 8.934c4.467 0 8.529-3.249 8.529-8.934 0-.528-.081-1.097-.202-1.625z"/></svg>
                Continue with Google
             </button>
             
             <div class="divider">OR</div>
             
             <!-- Guest Login Form -->
             <div class="card bg-base-100 shadow-xl">
                <form class="card-body p-4" @submit.prevent="handleLogin('guest')">
                    <h2 class="card-title text-sm uppercase opacity-50 justify-center">Guest Login</h2>
                    <div class="form-control">
                        <input type="text" v-model="guestCredentials.username" placeholder="Username" class="input input-bordered input-sm" required />
                    </div>
                    <div class="form-control mt-2">
                        <input type="password" v-model="guestCredentials.password" placeholder="Password" class="input input-bordered input-sm" required />
                    </div>
                    <div v-if="errorMessage" class="text-error text-xs mt-2">{{ errorMessage }}</div>
                    <button class="btn btn-primary btn-sm mt-4">Login</button>
                </form>
             </div>
             
             <p class="text-xs opacity-50 mt-2">Currently Invite Only</p>
        </div>

        <!-- Hidden Admin Form -->
        <div v-if="showAdminLogin" class="card mt-8 w-full shadow-2xl bg-base-100 animate-fade-in">
          <form class="card-body" @submit.prevent="handleLogin('admin')">
            <h2 class="card-title justify-center text-sm uppercase tracking-wide opacity-50 mb-2">Admin Access</h2>
            <div class="form-control">
              <input type="text" v-model="adminCredentials.username" placeholder="Username or Email" class="input input-bordered" required />
            </div>
            <div class="form-control">
              <input type="password" v-model="adminCredentials.password" placeholder="Password" class="input input-bordered" required />
            </div>
            <div v-if="errorMessage" class="text-error text-sm mt-2">{{ errorMessage }}</div>
            <div class="form-control mt-6">
              <button class="btn btn-neutral">Enter</button>
            </div>
            <button type="button" class="btn btn-ghost btn-xs mt-2" @click="showAdminLogin = false">Close</button>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.select-none { user-select: none; }
.animate-fade-in { animation: fadeIn 0.3s ease-out; }
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}
</style>

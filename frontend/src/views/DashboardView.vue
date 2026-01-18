<script setup lang="ts">
import { useAuth } from '../composables/useAuth'
import iconUser from '../assets/iconUser.png'

const { user, logout } = useAuth()
</script>

<template>
  <div class="p-8">
    <h1 class="text-3xl font-bold mb-4">Dashboard</h1>
    <div class="stats shadow">
      <div class="stat">
        <div class="stat-figure text-secondary">
          <div class="avatar online">
            <div class="w-16 rounded-full">
              <img :src="user?.avatar_url || iconUser" />
            </div>
          </div>
        </div>
        <div class="stat-value">Hello</div>
        <div class="stat-title">{{ user?.email }}</div>
        <div class="stat-desc text-secondary">{{ user?.role }}</div>
      </div>
    </div>
    <div class="mt-4">
      <button @click="logout()" class="btn btn-error">Logout</button>
    </div>
  </div>
</template>

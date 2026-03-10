<script setup lang="ts">
import { ref } from 'vue'
import { useUsers } from '../../composables/useUsers'
import type { CreateUserPayload } from '../../types/user'
import AppModal from '../common/AppModal.vue'

import { useToastStore } from '../../stores/toast'

const emit = defineEmits(['created'])
const { createUser, loading, error } = useUsers()
const toast = useToastStore()

const show = ref(false)
const form = ref<CreateUserPayload>({
  email: '',
  username: '',
  password: '',
  full_name: '',
  role: 'student'
})

const open = () => {
  form.value = {
    email: '',
    username: '',
    password: '',
    full_name: '',
    role: 'student'
  }
  show.value = true
}

const close = () => {
  show.value = false
}

const submit = async () => {
  try {
    await createUser(form.value)
    emit('created')
    close()
    toast.success('User created successfully')
  } catch (e) {
    if (!error.value) toast.error('Failed to create user')
  }
}

defineExpose({ open, close })
</script>

<template>
  <AppModal v-model="show" title="Create New User" size="md">
    <div v-if="error" class="alert alert-error my-2 text-sm">{{ error }}</div>

    <div class="py-4 flex flex-col gap-3">
      <div class="form-control">
        <label class="label"><span class="label-text">Email</span></label>
        <input
          type="email"
          v-model="form.email"
          placeholder="user@example.com"
          class="input input-bordered"
        />
      </div>

      <div class="form-control">
        <label class="label"><span class="label-text">Username (For Guest Login)</span></label>
        <input
          type="text"
          v-model="form.username"
          placeholder="johndoe"
          class="input input-bordered"
        />
      </div>

      <div class="form-control">
        <label class="label"><span class="label-text">Full Name</span></label>
        <input
          type="text"
          v-model="form.full_name"
          placeholder="John Doe"
          class="input input-bordered"
        />
      </div>

      <div class="form-control">
        <label class="label"><span class="label-text">Password</span></label>
        <input
          type="password"
          v-model="form.password"
          placeholder="********"
          class="input input-bordered"
        />
      </div>

      <div class="form-control">
        <label class="label"><span class="label-text">Role</span></label>
        <select v-model="form.role" class="select select-bordered" required>
          <option value="guest">Guest</option>
          <option value="student">Student</option>
          <option value="ta">TA</option>
          <option value="teacher">Teacher</option>
          <option value="admin">Admin</option>
        </select>
      </div>
    </div>
    <template #actions>
      <button class="btn btn-ghost" @click="close" :disabled="loading">Cancel</button>
      <button class="btn btn-primary" @click="submit" :disabled="loading">
        <span v-if="loading" class="loading loading-spinner loading-xs"></span>
        Create
      </button>
    </template>
  </AppModal>
</template>

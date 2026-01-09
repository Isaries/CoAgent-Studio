<script setup lang="ts">
import { ref } from 'vue'
import { useUsers } from '../../composables/useUsers'
import { usePermissions } from '../../composables/usePermissions'
import type { User, UpdateUserPayload } from '../../types/user'

import { useToastStore } from '../../stores/toast'

const emit = defineEmits(['updated'])
const { updateUser, loading, error } = useUsers()
const { currentUser, isSuperAdmin } = usePermissions()
const toast = useToastStore()

const show = ref(false)
const targetUser = ref<User | null>(null)
const form = ref<UpdateUserPayload & { id: string }>({
  id: '',
  full_name: '',
  role: '',
  password: ''
})

const open = (user: User) => {
  targetUser.value = user
  form.value = {
    id: user.id,
    full_name: user.full_name,
    role: user.role,
    password: ''
  }
  show.value = true
}

const close = () => {
  show.value = false
  targetUser.value = null
}

const submit = async () => {
  if (!form.value.id) return

  try {
    const payload: UpdateUserPayload = {
      full_name: form.value.full_name,
      role: form.value.role
    }
    if (form.value.password) payload.password = form.value.password

    await updateUser(form.value.id, payload)
    emit('updated')
    close()
    toast.success('User updated successfully')
  } catch (e) {
    // Error handled in composable
    if (!error.value) toast.error('Failed to update user')
  }
}

defineExpose({ open, close })
</script>

<template>
  <dialog :class="{ 'modal-open': show }" class="modal">
    <div v-if="show" class="modal-box">
      <h3 class="font-bold text-lg">Edit User</h3>
      <div v-if="error" class="alert alert-error my-2 text-sm">{{ error }}</div>

      <div class="py-4 flex flex-col gap-3">
        <div class="form-control">
          <label class="label"><span class="label-text">Full Name</span></label>
          <input type="text" v-model="form.full_name" class="input input-bordered" />
        </div>

        <div class="form-control">
          <label class="label"><span class="label-text">Role</span></label>
          <select
            v-model="form.role"
            class="select select-bordered"
            :disabled="form.id === currentUser?.id"
          >
            <option value="guest">Guest</option>
            <option value="student">Student</option>
            <option value="ta">TA</option>
            <option value="teacher">Teacher</option>
            <option value="admin">Admin</option>
            <option v-if="isSuperAdmin()" value="super_admin">Super Admin</option>
          </select>
          <label class="label" v-if="form.id === currentUser?.id">
            <span class="label-text-alt text-warning">You cannot change your own role.</span>
          </label>
        </div>

        <div class="form-control">
          <label class="label"><span class="label-text">New Password</span></label>
          <input
            type="password"
            v-model="form.password"
            placeholder="Leave blank to keep unchanged"
            class="input input-bordered"
          />
        </div>
      </div>
      <div class="modal-action">
        <button class="btn btn-ghost" @click="close" :disabled="loading">Cancel</button>
        <button class="btn btn-primary" @click="submit" :disabled="loading">
          <span v-if="loading" class="loading loading-spinner loading-xs"></span>
          Update
        </button>
      </div>
    </div>
  </dialog>
</template>

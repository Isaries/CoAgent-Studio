<script setup lang="ts">
import { ref, watch } from 'vue'
import { useFormValidation } from '../../composables/useFormValidation'
import { required, url as urlRule } from '../../utils/validators'
import { useI18n } from 'vue-i18n'
import { useToastStore } from '../../stores/toast'
import { useAuth } from '../../composables/useAuth'
import iconUser from '../../assets/iconUser.png'
import api from '../../api'
import AppModal from './AppModal.vue'

const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  'profile-updated': []
}>()

const { t } = useI18n()
const toast = useToastStore()
const { user, logout } = useAuth()

const editForm = ref({
  full_name: '',
  avatar_url: ''
})
const editLoading = ref(false)

const profileValidation = useFormValidation({
  full_name: { rules: [required(t('validation.required', { field: t('profile.displayName') }))] },
  avatar_url: { rules: [urlRule(t('validation.url'))] }
})

watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      editForm.value.full_name = user.value?.full_name || ''
      editForm.value.avatar_url = user.value?.avatar_url || ''
      profileValidation.reset()
    }
  }
)

const handleAvatarUpload = async (event: Event) => {
  const input = event.target as HTMLInputElement
  if (input.files && input.files[0]) {
    const file = input.files[0]
    if (file.size > 2 * 1024 * 1024) {
      toast.error('File size exceeds 2MB limit.')
      return
    }
    if (!['image/jpeg', 'image/png', 'image/jpg'].includes(file.type)) {
      toast.error('Only JPG and PNG files are allowed.')
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
      toast.error('Failed to upload avatar')
    } finally {
      editLoading.value = false
    }
  }
}

const updateProfile = async () => {
  const valid = profileValidation.validateAll({
    full_name: editForm.value.full_name,
    avatar_url: editForm.value.avatar_url
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
    emit('update:modelValue', false)
    emit('profile-updated')
  } catch (e) {
    toast.error('Failed to update profile')
  } finally {
    editLoading.value = false
  }
}

const close = () => {
  emit('update:modelValue', false)
}
</script>

<template>
  <AppModal :model-value="modelValue" @update:model-value="emit('update:modelValue', $event)" :title="t('profile.editProfile')">
    <div class="py-4">
      <div class="flex justify-center mb-4">
        <div class="avatar">
          <div class="w-24 rounded-full ring ring-primary ring-offset-base-100 ring-offset-2">
            <img :src="editForm.avatar_url || iconUser" />
          </div>
        </div>
      </div>

      <div class="form-control w-full mb-2">
        <label class="label"
          ><span class="label-text">{{ t('profile.displayName') }}</span></label
        >
        <input
          type="text"
          v-model="editForm.full_name"
          placeholder="John Doe"
          class="input input-bordered w-full"
          :class="{
            'input-error':
              profileValidation.touched.full_name && profileValidation.errors.full_name
          }"
          @blur="profileValidation.touchField('full_name', editForm.full_name)"
        />
        <label
          v-if="profileValidation.touched.full_name && profileValidation.errors.full_name"
          class="label"
        >
          <span class="label-text-alt text-error">{{
            profileValidation.errors.full_name
          }}</span>
        </label>
      </div>

      <div class="form-control w-full mb-2">
        <label class="label"
          ><span class="label-text">{{ t('profile.avatarImage') }}</span></label
        >
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
        <label class="label"
          ><span class="label-text">{{ t('profile.avatarUrl') }}</span></label
        >
        <input
          type="text"
          v-model="editForm.avatar_url"
          placeholder="https://..."
          class="input input-bordered w-full"
          :class="{
            'input-error':
              profileValidation.touched.avatar_url && profileValidation.errors.avatar_url
          }"
          @blur="profileValidation.touchField('avatar_url', editForm.avatar_url)"
        />
        <label
          v-if="profileValidation.touched.avatar_url && profileValidation.errors.avatar_url"
          class="label"
        >
          <span class="label-text-alt text-error">{{
            profileValidation.errors.avatar_url
          }}</span>
        </label>
        <label v-else class="label">
          <span class="label-text-alt">{{ t('profile.leaveEmpty') }}</span>
        </label>
      </div>
    </div>

    <template #actions>
      <div class="flex justify-between items-center w-full">
        <button class="btn btn-error btn-outline btn-sm" @click="logout">
          {{ t('profile.logout') }}
        </button>
        <div class="flex gap-2">
          <button class="btn btn-ghost" @click="close">
            {{ t('common.cancel') }}
          </button>
          <button class="btn btn-primary" @click="updateProfile" :disabled="editLoading">
            {{ t('common.save') }}
          </button>
        </div>
      </div>
    </template>
  </AppModal>
</template>

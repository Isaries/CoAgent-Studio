<script setup lang="ts">
import { ref } from 'vue'
import api from '../../../api'
import { AxiosError } from 'axios'
import UserSearchInput, { type UserResult } from '../../common/UserSearchInput.vue'
import { useToastStore } from '../../../stores/toast'
import AppModal from '../../common/AppModal.vue'

const props = defineProps<{
  spaceId: string
}>()

const emit = defineEmits<{
  (e: 'invited'): void
}>()

const show = ref(false)
const searchInputRef = ref<InstanceType<typeof UserSearchInput> | null>(null)

const inviteEmail = ref('')
const inviteUserId = ref('')
const inviteLoading = ref(false)
const toast = useToastStore()

const open = () => {
  inviteEmail.value = ''
  inviteUserId.value = ''
  if (searchInputRef.value) searchInputRef.value.resetSearch()
  show.value = true
}

const close = () => {
  show.value = false
}

const handleUserSelect = (user: UserResult) => {
  inviteEmail.value = user.email || 'No Email'
  inviteUserId.value = user.id
}

const inviteUser = async () => {
  if (!inviteUserId.value && (!inviteEmail.value || inviteEmail.value === 'No Email')) return

  inviteLoading.value = true
  try {
    await api.post(`/spaces/${props.spaceId}/members`, {
      user_email: inviteEmail.value !== 'No Email' ? inviteEmail.value : null,
      user_id: inviteUserId.value || null,
      role: 'participant'
    })
    toast.success('Member invited successfully!')
    emit('invited')
    close()
  } catch (e: unknown) {
    if (e instanceof AxiosError && e.response) {
      toast.error('Invitation failed: ' + (e.response.data?.detail || e.message))
    } else {
      toast.error('Invitation failed: ' + String(e))
    }
  } finally {
    inviteLoading.value = false
  }
}

defineExpose({ open, close })
</script>

<template>
  <AppModal v-model="show" title="Invite Member" size="md" box-class="overflow-visible">
    <p class="py-4">Search for a user to add to this space.</p>

    <UserSearchInput
      ref="searchInputRef"
      placeholder="Search User (Name, Email, Username)"
      @select="handleUserSelect"
    >
      <template #label><span class="label-text">Search User</span></template>
    </UserSearchInput>

    <!-- Selected User Display -->
    <div v-if="inviteEmail" class="alert alert-success shadow-sm mt-4 mb-4">
      <svg
        xmlns="http://www.w3.org/2000/svg"
        class="stroke-current shrink-0 h-6 w-6"
        fill="none"
        viewBox="0 0 24 24"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
        />
      </svg>
      <span>Selected: {{ inviteEmail }}</span>
    </div>

    <template #actions>
      <button class="btn btn-ghost mr-2" @click="close">Cancel</button>
      <button
        @click="inviteUser"
        class="btn btn-secondary"
        :disabled="inviteLoading || !inviteEmail"
      >
        Invite
      </button>
    </template>
  </AppModal>
</template>

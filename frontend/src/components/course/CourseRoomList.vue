<script setup lang="ts">
import type { Room } from '../../types/course'

const props = defineProps<{
  rooms: Room[]
  isStudent: boolean
}>()

const emit = defineEmits<{
  (e: 'delete-room', roomId: string): void
  (e: 'assign-student', roomId: string): void
}>()
</script>

<template>
  <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
    <div v-if="rooms.length === 0" class="col-span-full text-center py-4 opacity-70">
      No rooms created yet.
    </div>
    <div
      v-for="room in rooms"
      :key="room.id"
      class="card bg-base-100 shadow border border-base-300"
    >
      <div class="card-body">
        <div class="flex justify-between items-start">
          <h3 class="card-title">
            {{ room.name }}
            <div v-if="room.is_ai_active" class="badge badge-secondary badge-outline text-xs">
              AI Active
            </div>
          </h3>
          <div class="dropdown dropdown-end" v-if="!isStudent">
            <label tabindex="0" class="btn btn-ghost btn-xs btn-circle">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <circle cx="12" cy="12" r="1"></circle>
                <circle cx="12" cy="5" r="1"></circle>
                <circle cx="12" cy="19" r="1"></circle>
              </svg>
            </label>
            <ul
              tabindex="0"
              class="dropdown-content z-[1] menu p-2 shadow bg-base-100 rounded-box w-52"
            >
              <li><a @click="emit('delete-room', room.id)" class="text-error">Delete Room</a></li>
              <li><a @click="emit('assign-student', room.id)">Assign Student</a></li>
            </ul>
          </div>
        </div>

        <div class="card-actions justify-end mt-4">
          <router-link :to="`/rooms/${room.id}`" class="btn btn-primary btn-sm"
            >Enter Room</router-link
          >
        </div>
      </div>
    </div>
  </div>
</template>

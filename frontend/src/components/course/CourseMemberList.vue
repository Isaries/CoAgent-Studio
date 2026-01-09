<script setup lang="ts">
import type { CourseMember } from '../../types/course'
import iconUser from '../../assets/iconUser.png'

const props = defineProps<{
    members: CourseMember[]
    courseOwnerId?: string
    isStudent: boolean
    currentUserRole?: string
}>()

const emit = defineEmits<{
    (e: 'update-role', member: CourseMember, newRole: string): void
    (e: 'remove-member', memberId: string): void
}>()
</script>

<template>
    <div>
        <div v-if="members.length === 0" class="text-center py-4 opacity-70">
            No members found.
        </div>

        <!-- Desktop View (Table) -->
        <div class="hidden md:block overflow-x-auto">
            <table class="table w-full">
                <!-- head -->
                <thead>
                <tr>
                    <th>Name</th>
                    <th>Email</th>
                    <th>Role</th>
                    <th>Actions</th>
                </tr>
                </thead>
                <tbody>
                <tr v-for="member in members" :key="member.user_id + '_desktop'">
                    <td>
                        <div class="flex items-center gap-3">
                            <div class="avatar">
                                <div class="mask mask-squircle w-12 h-12">
                                    <img :src="member.avatar_url || iconUser" alt="Avatar" />
                                </div>
                            </div>
                            <div>
                                <div class="font-bold">{{ member.full_name || 'No Name' }}</div>
                            </div>
                        </div>
                    </td>
                    <td>{{ member.email }}</td>
                    <td>
                        <span class="badge" :class="member.role === 'ta' ? 'badge-accent' : 'badge-ghost'">{{ member.role.toUpperCase() }}</span>
                    </td>
                    <td>
                        <div class="join" v-if="!isStudent && member.user_id !== courseOwnerId">
                            <button 
                                v-if="member.role !== 'ta' && currentUserRole !== 'ta'" 
                                @click="emit('update-role', member, 'ta')" 
                                class="btn btn-xs btn-outline btn-accent join-item">
                                Make TA
                            </button>
                            <button 
                                v-if="member.role === 'ta' && currentUserRole !== 'ta'" 
                                @click="emit('update-role', member, 'student')" 
                                class="btn btn-xs btn-outline join-item">
                                Revoke TA
                            </button>
                            <button 
                                v-if="currentUserRole !== 'ta' || (currentUserRole === 'ta' && member.role === 'student')"
                                @click="emit('remove-member', member.user_id)" 
                                class="btn btn-xs btn-outline btn-error join-item">
                                Remove
                            </button>
                        </div>
                        <div v-else-if="member.user_id === courseOwnerId" class="text-xs opacity-50 italic">Owner</div>
                    </td>
                </tr>
                </tbody>
            </table>
        </div>

        <!-- Mobile View (Cards) -->
        <div class="block md:hidden space-y-4">
            <div v-for="member in members" :key="member.user_id + '_mobile'" class="card bg-base-100 shadow-sm border border-base-200 transition-all active:scale-[0.98]">
                <div class="card-body p-4 flex flex-row items-center gap-4">
                    <div class="avatar">
                        <div class="mask mask-squircle w-12 h-12">
                            <img :src="member.avatar_url || iconUser" alt="Avatar" />
                        </div>
                    </div>
                    <div class="flex-1 min-w-0">
                        <div class="flex justify-between items-start">
                            <h3 class="font-bold truncate">{{ member.full_name || 'No Name' }}</h3>
                            <span class="badge badge-sm" :class="member.role === 'ta' ? 'badge-accent' : 'badge-ghost'">{{ member.role.toUpperCase() }}</span>
                        </div>
                        <p class="text-xs text-gray-500 truncate">{{ member.email }}</p>
                    </div>
                </div>
                 <div class="card-actions px-4 pb-4" v-if="!isStudent && member.user_id !== courseOwnerId">
                     <button 
                        v-if="member.role !== 'ta' && currentUserRole !== 'ta'" 
                        @click="emit('update-role', member, 'ta')" 
                        class="btn btn-sm btn-outline btn-accent w-full">
                        Make TA
                     </button>
                     <button 
                        v-if="member.role === 'ta' && currentUserRole !== 'ta'" 
                        @click="emit('update-role', member, 'student')" 
                        class="btn btn-sm btn-outline w-full">
                        Revoke TA
                     </button>
                     <button 
                        v-if="currentUserRole !== 'ta' || (currentUserRole === 'ta' && member.role === 'student')"
                        @click="emit('remove-member', member.user_id)" 
                        class="btn btn-sm btn-outline btn-error w-full mt-2">
                        Remove
                     </button>
                </div>
                <div class="px-4 pb-4 text-center text-xs opacity-50 italic" v-else-if="member.user_id === courseOwnerId">
                    Course Owner
                </div>
            </div>
        </div>
    </div>
</template>

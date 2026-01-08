<script setup lang="ts">
import { ref } from 'vue'
import { useAuthStore } from '../stores/auth'
import iconUser from '../assets/iconUser.png'
import api from '../api'

const authStore = useAuthStore()
// const router = useRouter()

const logout = () => {
    authStore.logout()
}

// Profile Edit State
const showProfileModal = ref(false)
const editForm = ref({
    full_name: '',
    avatar_url: ''
})
const editLoading = ref(false)

const openProfileModal = () => {
    editForm.value.full_name = authStore.user?.full_name || ''
    editForm.value.avatar_url = authStore.user?.avatar_url || ''
    showProfileModal.value = true
}

const updateProfile = async () => {
    editLoading.value = true
    try {
        const res = await api.put('/users/me', {
            full_name: editForm.value.full_name,
            avatar_url: editForm.value.avatar_url
        })
        // Update local store
        if (authStore.user) {
            authStore.user.full_name = res.data.full_name
            authStore.user.avatar_url = res.data.avatar_url
        }
        showProfileModal.value = false
    } catch (e) {
        alert('Failed to update profile')
    } finally {
        editLoading.value = false
    }
}
</script>

<template>
  <div class="drawer lg:drawer-open">
    <input id="my-drawer-2" type="checkbox" class="drawer-toggle" />
    <div class="drawer-content flex flex-col bg-base-200">
      <!-- Navbar -->
      <div class="w-full navbar bg-base-100 lg:hidden user-select-none">
        <div class="flex-none lg:hidden">
          <label for="my-drawer-2" class="btn btn-square btn-ghost">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" class="inline-block w-6 h-6 stroke-current"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"></path></svg>
          </label>
        </div> 
        <div class="flex-1 px-2 mx-2">
            <!-- Mobile Avatar -->
            <div @click="openProfileModal" class="avatar cursor-pointer mr-2">
                <div class="w-8 rounded-full ring ring-primary ring-offset-base-100 ring-offset-2">
                    <img :src="authStore.user?.avatar_url || iconUser" />
                </div>
            </div>
            CoAgent Studio
        </div>
      </div>
      
      <!-- Page Content -->
      <main class="flex-1 p-6 overflow-y-auto">
        <router-view></router-view>
      </main>

       <!-- Profile Modal -->
       <dialog :class="{ 'modal-open': showProfileModal }" class="modal">
          <div class="modal-box">
            <h3 class="font-bold text-lg">Edit Profile</h3>
            <div class="py-4">
                <div class="flex justify-center mb-4">
                    <div class="avatar">
                        <div class="w-24 rounded-full ring ring-primary ring-offset-base-100 ring-offset-2">
                             <img :src="editForm.avatar_url || iconUser" />
                        </div>
                    </div>
                </div>
                
                <div class="form-control w-full mb-2">
                  <label class="label"><span class="label-text">Display Name</span></label>
                  <input type="text" v-model="editForm.full_name" placeholder="John Doe" class="input input-bordered w-full" />
                </div>
                
                <div class="form-control w-full mb-2">
                  <label class="label"><span class="label-text">Avatar URL (Optional)</span></label>
                  <input type="text" v-model="editForm.avatar_url" placeholder="https://..." class="input input-bordered w-full" />
                  <label class="label"><span class="label-text-alt">Leave empty to use default icon</span></label>
                </div>
            </div>
            
            <div class="modal-action flex justify-between items-center w-full">
              <button class="btn btn-error btn-outline btn-sm" @click="logout">Logout</button>
              <div class="flex gap-2">
                  <button class="btn btn-ghost" @click="showProfileModal = false">Cancel</button>
                  <button class="btn btn-primary" @click="updateProfile" :disabled="editLoading">Save</button>
              </div>
            </div>
          </div>
       </dialog>

    </div> 
    
    <div class="drawer-side">
      <label for="my-drawer-2" aria-label="close sidebar" class="drawer-overlay"></label> 
      <ul class="menu p-4 w-80 min-h-full bg-base-100 text-base-content flex flex-col justify-between">
        <!-- Sidebar content here -->
        <div>
          <!-- Desktop Avatar & Brand -->
          <li class="mb-4">
               <div @click="openProfileModal" class="flex flex-row items-center gap-4 hover:bg-base-200 p-2 rounded-lg cursor-pointer">
                    <div class="avatar">
                        <div class="w-12 rounded-full ring ring-primary ring-offset-base-100 ring-offset-2">
                            <img :src="authStore.user?.avatar_url || iconUser" />
                        </div>
                    </div>
                    <div>
                        <div class="font-bold text-lg text-primary">{{ authStore.user?.full_name || 'User' }}</div>
                        <div class="text-xs opacity-50">CoAgent Studio</div>
                    </div>
               </div>
          </li>
          
          <li v-if="authStore.isAdmin"><router-link to="/dashboard" active-class="active">Dashboard</router-link></li>
          <li v-if="authStore.isAdmin"><router-link to="/admin/users" active-class="active">User Management</router-link></li>
          <li v-if="authStore.isAdmin"><router-link to="/admin/database" active-class="active">Database</router-link></li>
          <li><router-link to="/courses" active-class="active">My Courses</router-link></li>
          <li><router-link to="/analytics" active-class="active">Analytics</router-link></li>
          
          <div class="divider"></div>
          
          <li><a @click="openProfileModal">Settings</a></li>
        </div>
      </ul>
    
    </div>
  </div>
</template>

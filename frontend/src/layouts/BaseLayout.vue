<script setup lang="ts">
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import iconUser from '../assets/iconUser.png'
import api from '../api'

const authStore = useAuthStore()
const route = useRoute()
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

const handleAvatarUpload = async (event: Event) => {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files[0]) {
        const file = input.files[0];
        // Validate size ( < 2MB )
        if (file.size > 2 * 1024 * 1024) {
            alert("File size exceeds 2MB limit.");
            return;
        }
        
        // Validate Type
        if (!['image/jpeg', 'image/png', 'image/jpg'].includes(file.type)) {
            alert("Only JPG and PNG files are allowed.");
            return;
        }

        const formData = new FormData();
        formData.append('file', file);

        editLoading.value = true;
        try {
            const res = await api.post('/users/me/avatar', formData, {
                headers: {
                    'Content-Type': 'multipart/form-data'
                }
            });
            editForm.value.avatar_url = res.data.avatar_url; // Update preview
            // Also update store immediately? 
            if (authStore.user) {
                authStore.user.avatar_url = res.data.avatar_url;
            }
        } catch (e) {
            console.error(e);
            alert("Failed to upload avatar");
        } finally {
            editLoading.value = false;
        }
    }
}
const updateProfile = async () => {
    editLoading.value = true
    try {
        const res = await api.put('/users/me', {
            full_name: editForm.value.full_name,
            // avatar_url: editForm.value.avatar_url // Already updated by upload, but sending it again ensures sync
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
  <div class="drawer lg:drawer-open" :class="{ 'border-4 border-error': authStore.isImpersonating }">
    <input id="my-drawer-2" type="checkbox" class="drawer-toggle" />
    
    <!-- Impersonation Banner -->
    <div v-if="authStore.isImpersonating" class="fixed bottom-6 right-6 z-50 animate-bounce">
        <button @click="authStore.stopImpersonating()" class="btn btn-error shadow-lg gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path><polyline points="16 17 21 12 16 7"></polyline><line x1="21" y1="12" x2="9" y2="12"></line></svg>
            Exit Impersonation
        </button>
    </div>

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
      <main class="flex-1 overflow-y-auto" :class="{ 'p-6': !route.name?.toString().includes('room'), 'overflow-y-hidden': route.name?.toString().includes('room') }">
        <router-view v-slot="{ Component }">
           <transition name="fade" mode="out-in">
             <component :is="Component" />
           </transition>
        </router-view>
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
                  <label class="label"><span class="label-text">Avatar Image</span></label>
                  <input type="file" @change="handleAvatarUpload" accept="image/png, image/jpeg" class="file-input file-input-bordered w-full" />
                   <label class="label"><span class="label-text-alt">Max size 2MB (PNG/JPG)</span></label>
                </div>
                
                <div class="divider text-xs">OR</div>

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
          <li><router-link to="/courses" active-class="active">My Courses</router-link></li>
          <li><router-link to="/analytics" active-class="active">Analytics</router-link></li>
          
          <template v-if="authStore.isAdmin">
            <div class="divider text-xs opacity-50 uppercase tracking-widest">Admin Tools</div>
            <li><router-link to="/admin/database" active-class="active">Database</router-link></li>
            <li><router-link to="/admin/system-agents" active-class="active">System Agents</router-link></li>
          </template>

          <div class="divider"></div>
          
          <li><a @click="openProfileModal">Settings</a></li>
        </div>
      </ul>
    
    </div>
  </div>
</template>

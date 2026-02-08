<template>
  <div class="user-keys-view max-w-4xl mx-auto py-8 px-4">
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-2xl font-bold text-gray-800">My API Keys</h1>
      <button 
        @click="showAddModal = true"
        class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg flex items-center gap-2 transition-colors"
      >
        <span>+ Add Key</span>
      </button>
    </div>

    <!-- Key List -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
      <div v-if="loading" class="p-8 text-center text-gray-500">
        Loading keys...
      </div>
      
      <div v-else-if="keys.length === 0" class="p-12 text-center">
        <div class="text-gray-400 mb-2 text-4xl">🔑</div>
        <h3 class="text-lg font-medium text-gray-900">No API Keys Found</h3>
        <p class="text-gray-500 mt-1">Add your OpenAI or Gemini keys to use them in your agents.</p>
        <button 
          @click="showAddModal = true"
          class="mt-4 text-blue-600 hover:text-blue-800 font-medium"
        >
          Add your first key
        </button>
      </div>

      <table v-else class="w-full text-left border-collapse">
        <thead class="bg-gray-50 border-b border-gray-100">
          <tr>
            <th class="py-3 px-4 font-semibold text-gray-600 text-sm">Alias</th>
            <th class="py-3 px-4 font-semibold text-gray-600 text-sm">Provider</th>
            <th class="py-3 px-4 font-semibold text-gray-600 text-sm">Key Preview</th>
            <th class="py-3 px-4 font-semibold text-gray-600 text-sm">Created</th>
            <th class="py-3 px-4 font-semibold text-gray-600 text-sm text-right">Actions</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100">
          <tr v-for="key in keys" :key="key.id" class="hover:bg-gray-50 transition-colors">
            <td class="py-3 px-4 text-gray-900 font-medium">{{ key.alias }}</td>
            <td class="py-3 px-4">
              <span 
                class="px-2 py-1 rounded-full text-xs font-medium capitalize"
                :class="{
                  'bg-green-100 text-green-700': key.provider === 'openai',
                  'bg-blue-100 text-blue-700': key.provider === 'gemini',
                  'bg-gray-100 text-gray-600': !['openai', 'gemini'].includes(key.provider)
                }"
              >
                {{ key.provider }}
              </span>
            </td>
            <td class="py-3 px-4 font-mono text-sm text-gray-500">{{ key.masked_key }}</td>
            <td class="py-3 px-4 text-sm text-gray-500">
              {{ new Date(key.created_at).toLocaleDateString() }}
            </td>
            <td class="py-3 px-4 text-right">
              <button 
                @click="deleteKey(key.id)"
                class="text-red-500 hover:text-red-700 p-1 rounded hover:bg-red-50"
                title="Delete Key"
              >
                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                  <path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd" />
                </svg>
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Add Modal -->
    <div v-if="showAddModal" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
      <div class="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
        <h2 class="text-xl font-bold mb-4 text-gray-800">Add New API Key</h2>
        
        <form @submit.prevent="submitKey">
          <div class="space-y-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Provider</label>
              <select 
                v-model="newKey.provider"
                class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
              >
                <option value="openai">OpenAI</option>
                <option value="gemini">Google Gemini</option>
              </select>
            </div>
            
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Alias (Name)</label>
              <input 
                v-model="newKey.alias" 
                type="text" 
                placeholder="e.g. Personal OpenAI Key"
                required
                class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 outline-none"
              />
            </div>
            
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">API Key</label>
              <input 
                v-model="newKey.api_key" 
                type="password" 
                placeholder="sk-..."
                required
                class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 outline-none"
              />
              <p class="text-xs text-gray-500 mt-1">
                Keys are encrypted at rest. We never display the full key back to you.
              </p>
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Description (Optional)</label>
              <textarea 
                v-model="newKey.description" 
                rows="2"
                class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 outline-none"
              ></textarea>
            </div>
          </div>

          <div class="flex justify-end gap-3 mt-6">
            <button 
              type="button" 
              @click="showAddModal = false"
              class="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button 
              type="submit" 
              class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg disabled:opacity-50 transition-colors"
              :disabled="submitting"
            >
              {{ submitting ? 'Adding...' : 'Save Key' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { userKeyService, type UserAPIKey } from '../services/userKeyService';

const keys = ref<UserAPIKey[]>([]);
const loading = ref(true);
const showAddModal = ref(false);
const submitting = ref(false);

const newKey = ref({
  provider: 'gemini', // Default
  alias: '',
  api_key: '',
  description: ''
});

onMounted(async () => {
  await fetchKeys();
});

async function fetchKeys() {
  loading.value = true;
  try {
    keys.value = await userKeyService.listKeys();
  } catch (e) {
    console.error("Failed to fetch keys", e);
    // You might want to show a toast/notification here
  } finally {
    loading.value = false;
  }
}

async function submitKey() {
  if (!newKey.value.alias || !newKey.value.api_key) return;
  
  submitting.value = true;
  try {
    await userKeyService.addKey({
      provider: newKey.value.provider,
      alias: newKey.value.alias,
      api_key: newKey.value.api_key,
      description: newKey.value.description
    });
    
    // Reset and Refresh
    showAddModal.value = false;
    newKey.value = { provider: 'gemini', alias: '', api_key: '', description: '' };
    await fetchKeys();
    
  } catch (e) {
    console.error("Failed to add key", e);
    alert('Failed to add key. Alias must be unique.');
  } finally {
    submitting.value = false;
  }
}

async function deleteKey(id: string) {
  if (!confirm('Are you sure you want to delete this key? This action cannot be undone.')) return;
  
  try {
    await userKeyService.deleteKey(id);
    await fetchKeys();
  } catch (e) {
    console.error("Failed to delete key", e);
  }
}
</script>

<style scoped>
/* Scoped styles if needed, mostly using Tailwind classes */
</style>

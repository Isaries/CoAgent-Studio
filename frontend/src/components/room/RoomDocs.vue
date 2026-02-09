<script setup lang="ts">
import { ref, computed } from 'vue'
import { useWorkspaceStore } from '@/stores/workspace'
import { useAuthStore } from '@/stores/auth'
import DocEditor from '../workspace/DocEditor.vue'
import { formatTime, isAgent } from '@/utils/roomHelpers'

const workspaceStore = useWorkspaceStore()
const authStore = useAuthStore()

const selectedDocId = ref<string | null>(null)

const selectedDoc = computed(() =>
  workspaceStore.documents.find(d => d.id === selectedDocId.value)
)

async function createNewDoc() {
  const title = prompt("Document Title:")
  if (title) {
    const doc = await workspaceStore.createDoc(title)
    if (doc) selectedDocId.value = doc.id
  }
}

function handleArtifactUpdate(id: string, content: any) {
  workspaceStore.updateArtifact(id, { content })
}
</script>

<template>
  <div class="flex-1 overflow-hidden bg-base-200/50 p-4 flex gap-4 relative">
    <div v-if="workspaceStore.loading" class="absolute inset-0 flex items-center justify-center bg-base-100/50 z-50">
      <span class="loading loading-spinner loading-lg"></span>
    </div>

    <!-- Doc List -->
    <div class="w-72 bg-base-100 rounded-box shadow-sm flex flex-col border border-base-200">

      <div class="p-4 border-b border-base-200 flex justify-between items-center bg-base-50 rounded-t-box">
         <h3 class="font-bold text-sm uppercase tracking-wide opacity-70">Documents</h3>
         <button @click="createNewDoc" class="btn btn-xs btn-primary gap-1">
           <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
           New
         </button>
      </div>
      <div class="flex-1 overflow-y-auto p-2 space-y-1">
         <div
           v-for="doc in workspaceStore.documents"
           :key="doc.id"
           @click="selectedDocId = doc.id"
           class="group p-3 rounded-lg cursor-pointer hover:bg-base-200 transition-all border border-transparent hover:border-base-300"
           :class="{ 'bg-primary/5 border-primary/20': selectedDocId === doc.id }"
         >
           <div class="flex items-start gap-3">
             <div class="mt-1 p-1.5 rounded bg-base-200 group-hover:bg-primary/10 text-primary-content group-hover:text-primary transition-colors">
               <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>
             </div>
             <div class="flex-1 min-w-0">
               <div class="font-medium text-sm truncate" :class="{ 'text-primary': selectedDocId === doc.id }">
                 {{ doc.title }}
               </div>
               <div class="text-xs text-base-content/50 mt-0.5 flex items-center gap-1">
                  <span v-if="isAgent(doc.last_modified_by, authStore.user?.id)" class="text-primary font-xs flex items-center gap-0.5">
                    <svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a10 10 0 1 0 10 10H12V2z"></path><path d="M12 2a10 10 0 0 1 10 10"></path><path d="M12 2v10"></path></svg>
                    AI
                  </span>
                  <span v-if="isAgent(doc.last_modified_by, authStore.user?.id)">•</span>
                  <span>v{{ doc.version }}</span>
                  <span>•</span>
                  <span>{{ formatTime(doc.updated_at) }}</span>
               </div>
             </div>
           </div>
         </div>
         <div v-if="workspaceStore.documents.length === 0" class="flex flex-col items-center justify-center h-40 text-base-content/40">
           <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" stroke-linecap="round" stroke-linejoin="round" class="mb-2 opacity-50"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline></svg>
           <span class="text-sm">No documents yet</span>
         </div>
      </div>
    </div>

    <!-- Doc Editor -->
    <div class="flex-1 bg-base-100 rounded-box shadow-sm border border-base-200 overflow-hidden relative">
      <DocEditor
        v-if="selectedDoc"
        :artifact="selectedDoc"
        :key="selectedDoc.id"
        class="h-full"
        @update="(c) => handleArtifactUpdate(selectedDoc!.id, c)"
      />
      <div v-else class="absolute inset-0 flex flex-col items-center justify-center text-base-content/30 gap-4">
        <div class="w-16 h-16 rounded-full bg-base-200 flex items-center justify-center">
          <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>
        </div>
        <p>Select a document to start editing</p>
      </div>
    </div>
  </div>
</template>

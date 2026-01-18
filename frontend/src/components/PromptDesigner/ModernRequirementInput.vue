<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  requirement: string
  context: string
  refineCurrent: boolean
  canEdit: boolean
  loading: boolean
}

const props = defineProps<Props>()
const emit = defineEmits(['update:requirement', 'update:context', 'update:refineCurrent', 'generate'])

const requirementModel = computed({
  get: () => props.requirement,
  set: (val) => emit('update:requirement', val)
})

const contextModel = computed({
  get: () => props.context,
  set: (val) => emit('update:context', val)
})

const refineCurrentModel = computed({
  get: () => props.refineCurrent,
  set: (val) => emit('update:refineCurrent', val)
})
</script>

<template>
  <div class="flex flex-col h-full gap-6 p-1">
      
      <!-- Header / Instruction -->
      <div>
        <h3 class="text-sm font-bold text-base-content opacity-90 mb-1">Your Requirement</h3>
        <p class="text-xs text-base-content opacity-50">Describe the agent's persona, goals, and constraints.</p>
      </div>

      <!-- Main Input Area -->
      <div class="flex-1 relative group">
        <textarea
          v-model="requirementModel"
          class="textarea textarea-bordered w-full h-full resize-none p-4 text-sm leading-relaxed
                 bg-base-200/30 focus:bg-base-200/50 transition-all border-base-300 focus:border-primary/50 outline-none
                 shadow-inner rounded-xl"
          placeholder="E.g. 'Create a friendly Python tutor who explains concepts using cooking analogies. It should be encouraging but correct errors gently...'"
        ></textarea>
        
        <!-- Decoration Corner -->
        <div class="absolute bottom-3 right-3 opacity-20 group-focus-within:opacity-100 transition-opacity">
           <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-primary"><path d="M12 19l7-7 3 3-7 7-3-3z"></path><path d="M18 13l-1.5-7.5L2 2l3.5 14.5L13 18l5-5z"></path><path d="M2 2l7.586 7.586"></path><circle cx="11" cy="11" r="2"></circle></svg>
        </div>
      </div>

      <!-- Settings & Context -->
      <div class="space-y-4 bg-base-200/30 p-4 rounded-xl border border-base-300/30">
        <div class="form-control">
          <label class="label text-[10px] font-bold uppercase tracking-wider opacity-60">Context / Background</label>
          <input v-model="contextModel" type="text" placeholder="e.g. 'Intro to CS 101 Course'" class="input input-sm input-bordered w-full bg-base-100/50" />
        </div>

        <div class="flex items-center justify-between pt-2">
            <label class="cursor-pointer flex items-center gap-2 group">
              <input type="checkbox" v-model="refineCurrentModel" class="checkbox checkbox-xs checkbox-primary" :disabled="!canEdit" />
              <span class="text-xs font-medium group-hover:text-primary transition-colors" :class="{'opacity-50': !canEdit}">Refine Mode</span>
            </label>
        </div>
      </div>

      <!-- Action Button -->
      <button 
        @click="$emit('generate')" 
        class="btn btn-primary w-full shadow-lg shadow-primary/20 hover:shadow-primary/40 transition-all duration-300 border-none bg-gradient-to-r from-primary to-secondary text-white font-bold tracking-wide"
        :disabled="loading"
        :class="loading ? 'animate-pulse' : ''"
      >
        <span v-if="loading" class="loading loading-spinner loading-sm"></span>
        <span v-else class="flex items-center gap-2">
           <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path><circle cx="12" cy="12" r="3"></circle></svg>
           {{ refineCurrentModel ? 'Refine Agent' : 'Design Agent' }}
        </span>
      </button>

  </div>
</template>

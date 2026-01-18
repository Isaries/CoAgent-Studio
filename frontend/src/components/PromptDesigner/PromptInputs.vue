<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  requirement: string
  context: string
  refineCurrent: boolean
  canEdit: boolean // e.g. if we have a prompt to refine
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
  <div class="flex flex-col gap-4 h-full">
     <div class="form-control flex-1 min-h-0">
       <label class="label text-xs font-bold uppercase tracking-wider opacity-70">Your Requirement</label>
       <textarea
         v-model="requirementModel"
         class="textarea textarea-bordered w-full h-full resize-none focus:outline-none bg-base-100 text-base"
         placeholder="Describe the agent you want to build. e.g. 'A friendly python tutor who uses pizza analogies'..."
       ></textarea>
     </div>
     
     <div class="flex flex-col gap-3">
        <div class="form-control">
          <label class="label text-xs font-bold uppercase tracking-wider opacity-70">Context</label>
          <input v-model="contextModel" type="text" placeholder="e.g. Intro to Python Course" class="input input-bordered w-full" />
        </div>

        <div class="flex items-center justify-between">
           <label class="label cursor-pointer gap-2 p-0">
             <input type="checkbox" v-model="refineCurrentModel" class="checkbox checkbox-sm checkbox-primary" :disabled="!canEdit" />
             <span class="label-text text-sm font-medium">Refine Current Prompt</span>
           </label>
        </div>
        
        <button @click="$emit('generate')" class="btn btn-secondary w-full" :disabled="loading">
          <span v-if="loading" class="loading loading-spinner loading-sm"></span>
          {{ loading ? 'Generating...' : 'Auto-Generate Prompt' }}
        </button>
     </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import ResizableSplitPane from '../../../components/common/ResizableSplitPane.vue'
import ModernSandboxHeader from '../../../components/PromptDesigner/ModernSandboxHeader.vue'
import PromptEditor from '../../../components/PromptDesigner/PromptEditor.vue'
import SimulationPanel from '../../../components/PromptDesigner/SimulationPanel.vue'
import type { SandboxState } from '../../../composables/useAgentSandbox'
import type { AgentConfig } from '../../../types/agent'

interface Props {
  sandbox: SandboxState
  designConfig: AgentConfig | null
  requirement: string
  context: string
  refineCurrent: boolean
  loading: boolean
  isSimulating: boolean
  simulationOutput: string
}

const props = defineProps<Props>()

const emit = defineEmits<{
  (e: 'update:requirement', val: string): void
  (e: 'update:context', val: string): void
  (e: 'update:refineCurrent', val: boolean): void
  (e: 'update:systemPrompt', val: string): void
  (e: 'update:sandbox', val: SandboxState): void
  (e: 'applySandbox'): void
  (e: 'generate'): void
  (e: 'clearOutput'): void
}>()

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

const systemPromptModel = computed({
  get: () => props.designConfig?.system_prompt || '',
  set: (val) => emit('update:systemPrompt', val)
})
</script>

<template>
  <div class="flex-1 overflow-hidden relative">
    <ResizableSplitPane :initial-left-width="500" :min-left-width="300" :min-right-width="400">
      
      <!-- Left Pane: DESIGN AGENT CONFIG -->
      <template #left>
          <div class="flex flex-col h-full bg-[#141414] relative">
             <div class="absolute top-0 left-0 w-full h-[200px] bg-gradient-to-b from-purple-500/5 to-transparent pointer-events-none"></div>

             <!-- Header Label -->
             <div class="px-5 py-3 border-b border-white/5 bg-[#141414] flex items-center justify-between relative z-20 flex-shrink-0">
                <span class="text-xs font-bold text-gray-400">DESIGN AGENT SYSTEM PROMPT</span>
                <div class="flex items-center gap-2">
                   <span class="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" v-if="!sandbox.enabled" title="Live"></span>
                   <span class="w-1.5 h-1.5 rounded-full bg-yellow-500 animate-pulse" v-else title="Sandbox Mode"></span>
                </div>
             </div>

             <div class="flex-1 flex flex-col overflow-hidden relative z-10">
                <!-- Sandbox Config -->
                <div v-if="sandbox.enabled" class="p-4 border-b border-white/5 bg-[#161616]">
                    <ModernSandboxHeader 
                      :model-value="sandbox" 
                      @apply="$emit('applySandbox')"
                      @update:modelValue="val => $emit('update:sandbox', Object.assign({}, sandbox, val))"
                    />
                </div>

                <!-- The Prompt Editor -->
                <PromptEditor 
                   v-model="systemPromptModel"
                   class="flex-1 border-none rounded-none w-full h-full text-sm font-mono"
                />
             </div>
          </div>
      </template>
      
      <!-- Right Pane: SIMULATION PLAYGROUND -->
      <template #right>
          <div class="flex flex-col h-full bg-[#1e1e1e] relative">
             <SimulationPanel
               v-model:requirement="requirementModel"
               v-model:context="contextModel"
               v-model:refine-current="refineCurrentModel"
               :loading="loading || isSimulating"
               :simulation-output="simulationOutput"
               @generate="$emit('generate')"
               @clearOutput="$emit('clearOutput')"
             />
          </div>
      </template>

    </ResizableSplitPane>
  </div>
</template>

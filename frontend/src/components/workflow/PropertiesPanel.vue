<script setup lang="ts">
/**
 * Properties Panel – appears on the right side of the canvas.
 * Shows config details for the selected node or edge.
 */
import { computed } from 'vue'

const props = defineProps<{
  selectedElement: any | null
  elementType: 'node' | 'edge' | null
  agents: Array<{ id: string; name: string; type: string; system_prompt?: string }>
}>()

const emit = defineEmits<{
  (e: 'update:node', id: string, data: Record<string, any>): void
  (e: 'update:edge', id: string, data: Record<string, any>): void
  (e: 'delete', id: string): void
  (e: 'close'): void
}>()

const edgeTypes = [
  { value: 'forward', label: '📤 Forward (傳遞)', desc: 'Pass data downstream' },
  { value: 'evaluate', label: '✅ Evaluate (審核)', desc: 'Target approves or rejects' },
  { value: 'summarize', label: '📝 Summarize (摘要)', desc: 'Target summarises inputs' },
  { value: 'critique', label: '💬 Critique (評論)', desc: 'Target provides feedback' },
  { value: 'trigger', label: '⚡ Trigger (觸發)', desc: 'Completion triggers target' },
]

const selectedAgent = computed(() => {
  if (props.elementType !== 'node' || !props.selectedElement) return null
  const agentId = props.selectedElement.data?.agentId
  return props.agents.find(a => a.id === agentId) || null
})
</script>

<template>
  <div
    v-if="selectedElement"
    class="w-80 bg-base-100 border-l border-base-300 p-4 overflow-y-auto flex flex-col gap-4"
  >
    <!-- Header -->
    <div class="flex items-center justify-between">
      <h3 class="font-bold text-lg">
        {{ elementType === 'node' ? '🔲 Node' : '🔗 Edge' }} Properties
      </h3>
      <button class="btn btn-ghost btn-xs btn-circle" @click="emit('close')">✕</button>
    </div>

    <div class="divider my-0" />

    <!-- ─── Node Properties ──────────────────────────── -->
    <template v-if="elementType === 'node' && selectedElement">
      <div class="form-control">
        <label class="label"><span class="label-text font-bold">Node ID</span></label>
        <input class="input input-bordered input-sm" :value="selectedElement.id" disabled />
      </div>

      <div class="form-control">
        <label class="label"><span class="label-text font-bold">Type</span></label>
        <input class="input input-bordered input-sm" :value="selectedElement.type" disabled />
      </div>

      <div class="form-control">
        <label class="label"><span class="label-text font-bold">Label</span></label>
        <input
          class="input input-bordered input-sm"
          :value="selectedElement.data?.label || ''"
          @input="emit('update:node', selectedElement.id, { label: ($event.target as HTMLInputElement).value })"
        />
      </div>

      <!-- Agent-specific: show system prompt preview -->
      <template v-if="selectedElement.type === 'agent'">
        <div class="form-control">
          <label class="label"><span class="label-text font-bold">Linked Agent</span></label>
          <select
            class="select select-bordered select-sm"
            :value="selectedElement.data?.agentId || ''"
            @change="emit('update:node', selectedElement.id, {
              agentId: ($event.target as HTMLSelectElement).value,
              label: agents.find(a => a.id === ($event.target as HTMLSelectElement).value)?.name || 'Agent',
            })"
          >
            <option value="">-- Select Agent --</option>
            <option v-for="agent in agents" :key="agent.id" :value="agent.id">
              {{ agent.name }} ({{ agent.type }})
            </option>
          </select>
        </div>

        <div v-if="selectedAgent" class="bg-base-200 rounded-lg p-3 text-xs">
          <div class="font-bold mb-1 opacity-70">System Prompt Preview</div>
          <div class="whitespace-pre-wrap opacity-80 max-h-32 overflow-y-auto">
            {{ selectedAgent.system_prompt?.substring(0, 300) || '(empty)' }}
            <span v-if="(selectedAgent.system_prompt?.length || 0) > 300">...</span>
          </div>
        </div>

        <div class="form-control">
          <label class="label"><span class="label-text font-bold">Output Behavior</span></label>
          <select
            class="select select-bordered select-sm"
            :value="selectedElement.data?.config?.output_behavior || 'proposal'"
            @change="emit('update:node', selectedElement.id, {
              config: { ...selectedElement.data?.config, output_behavior: ($event.target as HTMLSelectElement).value }
            })"
          >
            <option value="proposal">Proposal (草稿輸出)</option>
            <option value="evaluation">Evaluation (審核判定)</option>
          </select>
        </div>
      </template>

      <!-- Router-specific -->
      <template v-if="selectedElement.type === 'router'">
        <div class="form-control">
          <label class="label"><span class="label-text font-bold">Condition Type</span></label>
          <select class="select select-bordered select-sm"
            :value="selectedElement.data?.config?.condition || 'is_approved'"
            @change="emit('update:node', selectedElement.id, {
              config: { ...selectedElement.data?.config, condition: ($event.target as HTMLSelectElement).value }
            })"
          >
            <option value="is_approved">Is Approved? (審核通過?)</option>
            <option value="cycle_limit">Cycle Limit (迴圈上限)</option>
          </select>
        </div>
      </template>
    </template>

    <!-- ─── Edge Properties ──────────────────────────── -->
    <template v-if="elementType === 'edge' && selectedElement">
      <div class="form-control">
        <label class="label"><span class="label-text font-bold">Edge ID</span></label>
        <input class="input input-bordered input-sm" :value="selectedElement.id" disabled />
      </div>

      <div class="form-control">
        <label class="label"><span class="label-text font-bold">Relationship Type (關係類型)</span></label>
        <div class="flex flex-col gap-1">
          <label
            v-for="et in edgeTypes"
            :key="et.value"
            class="flex items-center gap-2 p-2 rounded-lg cursor-pointer hover:bg-base-200 transition-colors"
            :class="{ 'bg-primary/10 border border-primary/30': selectedElement.data?.type === et.value }"
          >
            <input
              type="radio"
              name="edge-type"
              class="radio radio-primary radio-xs"
              :value="et.value"
              :checked="(selectedElement.data?.type || selectedElement.type) === et.value"
              @change="emit('update:edge', selectedElement.id, { type: et.value })"
            />
            <div>
              <div class="text-sm font-medium">{{ et.label }}</div>
              <div class="text-xs opacity-60">{{ et.desc }}</div>
            </div>
          </label>
        </div>
      </div>

      <!-- Condition label (for router outgoing edges) -->
      <div class="form-control">
        <label class="label"><span class="label-text font-bold">Condition Label</span></label>
        <input
          class="input input-bordered input-sm"
          placeholder="e.g. approved, rejected, default"
          :value="selectedElement.data?.condition || ''"
          @input="emit('update:edge', selectedElement.id, { condition: ($event.target as HTMLInputElement).value })"
        />
        <label class="label"><span class="label-text-alt opacity-50">Used by Router nodes for branching</span></label>
      </div>
    </template>

    <!-- Delete Button -->
    <div class="mt-auto pt-4 border-t border-base-300">
      <button
        class="btn btn-error btn-sm btn-outline w-full"
        @click="emit('delete', selectedElement.id)"
      >
        Delete {{ elementType === 'node' ? 'Node' : 'Edge' }}
      </button>
    </div>
  </div>
</template>

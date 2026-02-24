<script setup lang="ts">
/**
 * WorkflowEditor – The main visual canvas for designing multi-agent workflows.
 *
 * Layout:
 *   [Left: Node Palette] [Center: Vue Flow Canvas] [Right: Properties Panel]
 *
 * Features:
 *   - Drag & drop agent / logic nodes onto the canvas
 *   - Auto-save graph topology to backend
 *   - Live tracing via WebSocket workflow_trace events
 */
import { ref, computed, onMounted, watch, markRaw } from 'vue'
import { VueFlow, useVueFlow, MarkerType } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import '@vue-flow/controls/dist/style.css'

import AgentNode from './AgentNode.vue'
import LogicNode from './LogicNode.vue'
import PropertiesPanel from './PropertiesPanel.vue'

import { workflowService } from '../../services/workflowService'
import { roomService } from '../../services/roomService'
import { useToastStore } from '../../stores/toast'

const props = defineProps<{
  roomId?: string
  workflowId?: string
}>()

const toast = useToastStore()

// ─── Vue Flow ───────────────────────────────────────────────
const { addNodes, addEdges, removeNodes, removeEdges, onNodeClick, onEdgeClick, onConnect, project } = useVueFlow()

const nodes = ref<any[]>([])
const edges = ref<any[]>([])

// Custom node type mappings (cast to any to work around Vue Flow's strict NodeTypesObject typing)
const nodeTypes: any = {
  agent: markRaw(AgentNode),
  start: markRaw(LogicNode),
  end: markRaw(LogicNode),
  router: markRaw(LogicNode),
  merge: markRaw(LogicNode),
  action: markRaw(LogicNode),
  tool: markRaw(LogicNode),
}

// ─── Properties Panel ───────────────────────────────────────
const selectedElement = ref<any>(null)
const selectedElementType = ref<'node' | 'edge' | null>(null)

onNodeClick(({ node }) => {
  selectedElement.value = node
  selectedElementType.value = 'node'
})

onEdgeClick(({ edge }) => {
  selectedElement.value = edge
  selectedElementType.value = 'edge'
})

const closePanel = () => {
  selectedElement.value = null
  selectedElementType.value = null
}

// ─── Room Agents (for the palette and properties panel) ─────
const roomAgents = ref<any[]>([])

const fetchRoomAgents = async () => {
  try {
    if (props.workflowId) {
      // Studio mode: fetch all agents globally
      const { agentService } = await import('../../services/agentService')
      // Use global agent list (get all available agents)
      const res = await agentService.getSystemAgents()
      roomAgents.value = res.data
    } else if (props.roomId) {
      // Legacy mode: fetch agents assigned to this room
      const res = await roomService.getRoomAgents(props.roomId)
      roomAgents.value = res.data
    }
  } catch (e) {
    console.error('Failed to fetch agents', e)
  }
}

// ─── Node Palette (drag & drop) ─────────────────────────────
const paletteItems = computed(() => {
  const agentItems = roomAgents.value.map(a => ({
    nodeType: 'agent',
    label: a.name,
    agentId: a.id,
    agentType: a.type,
  }))

  const logicItems = [
    { nodeType: 'start', label: 'START' },
    { nodeType: 'end', label: 'END' },
    { nodeType: 'router', label: 'CONDITION' },
    { nodeType: 'merge', label: 'MERGE' },
    { nodeType: 'action', label: 'BROADCAST' },
  ]

  return { agents: agentItems, logic: logicItems }
})

let dragData: any = null

const onDragStart = (event: DragEvent, item: any) => {
  dragData = item
  event.dataTransfer!.effectAllowed = 'move'
}

const onDragOver = (event: DragEvent) => {
  event.preventDefault()
  event.dataTransfer!.dropEffect = 'move'
}

const onDrop = (event: DragEvent) => {
  if (!dragData) return

  const canvasEl = document.querySelector('.vue-flow') as HTMLElement
  if (!canvasEl) return

  const bounds = canvasEl.getBoundingClientRect()
  const position = project({
    x: event.clientX - bounds.left,
    y: event.clientY - bounds.top,
  })

  const newId = `node-${Date.now()}`
  const newNode: any = {
    id: newId,
    type: dragData.nodeType,
    position: { x: position.x, y: position.y },
    data: {
      label: dragData.label || dragData.nodeType.toUpperCase(),
      agentId: dragData.agentId || null,
      agentType: dragData.agentType || null,
      config: {},
    },
  }

  addNodes([newNode])
  dragData = null
}

// ─── Edge creation ──────────────────────────────────────────
onConnect((connection) => {
  const edgeId = `edge-${Date.now()}`
  addEdges([{
    id: edgeId,
    source: connection.source,
    target: connection.target,
    type: 'smoothstep',
    animated: false,
    data: { type: 'forward' },
    markerEnd: MarkerType.ArrowClosed,
    label: 'forward',
  }])
})

// ─── Properties panel callbacks ─────────────────────────────
const onUpdateNode = (id: string, data: Record<string, any>) => {
  const node = nodes.value.find(n => n.id === id)
  if (node) {
    node.data = { ...node.data, ...data }
  }
}

const onUpdateEdge = (id: string, data: Record<string, any>) => {
  const edge = edges.value.find(e => e.id === id)
  if (edge) {
    if (data.type) {
      edge.data = { ...edge.data, type: data.type }
      edge.label = data.type
    }
    if (data.condition !== undefined) {
      edge.data = { ...edge.data, condition: data.condition }
    }
  }
}

const onDeleteElement = (id: string) => {
  if (selectedElementType.value === 'node') {
    removeNodes([id])
  } else {
    removeEdges([id])
  }
  closePanel()
}

// ─── Save / Load ────────────────────────────────────────────
const isSaving = ref(false)
const isLoading = ref(true)
const workflowName = ref('Default Workflow')

const loadWorkflow = async () => {
  isLoading.value = true
  try {
    let res: any
    if (props.workflowId) {
      res = await workflowService.getWorkflowById(props.workflowId)
    } else if (props.roomId) {
      res = await workflowService.getWorkflow(props.roomId)
    }
    if (res?.data) {
      workflowName.value = res.data.name || 'Default Workflow'
      const graph = res.data.graph_data
      if (graph?.nodes?.length) {
        nodes.value = graph.nodes.map((n: any) => ({
          id: n.id,
          type: n.type || 'agent',
          position: n.position || { x: 0, y: 0 },
          data: n.config || { label: n.id },
        }))
      }
      if (graph?.edges?.length) {
        edges.value = graph.edges.map((e: any) => ({
          id: e.id,
          source: e.source,
          target: e.target,
          type: 'smoothstep',
          animated: false,
          data: { type: e.type || 'forward', condition: e.condition },
          label: e.type || 'forward',
          markerEnd: MarkerType.ArrowClosed,
        }))
      }
    }
  } catch (e) {
    console.error(e)
  } finally {
    isLoading.value = false
  }
}

const saveWorkflow = async () => {
  isSaving.value = true
  try {
    const graphData = {
      nodes: nodes.value.map(n => ({
        id: n.id,
        type: n.type,
        position: n.position,
        config: {
          ...n.data,
          agent_id: n.data?.agentId || undefined,
        },
      })),
      edges: edges.value.map(e => ({
        id: e.id,
        source: e.source,
        target: e.target,
        type: e.data?.type || 'forward',
        condition: e.data?.condition || undefined,
      })),
    }

    if (props.workflowId) {
      await workflowService.updateWorkflow(props.workflowId, {
        name: workflowName.value,
        graph_data: graphData,
      })
    } else if (props.roomId) {
      await workflowService.saveWorkflow(props.roomId, {
        name: workflowName.value,
        graph_data: graphData,
      })
    }
    toast.success('Workflow saved! ✓')
  } catch (e) {
    console.error(e)
    toast.error('Failed to save workflow')
  } finally {
    isSaving.value = false
  }
}

// ─── Live Tracing ───────────────────────────────────────────
const activeNodeId = ref<string | null>(null)

// Watch for active node changes and update node data
watch(activeNodeId, (newId) => {
  nodes.value.forEach(n => {
    n.data = { ...n.data, isActive: n.id === newId }
  })
})

// Expose for parent to set via WebSocket
defineExpose({ activeNodeId })

// ─── Init ───────────────────────────────────────────────────
onMounted(async () => {
  await fetchRoomAgents()
  await loadWorkflow()
})
</script>

<template>
  <div class="workflow-editor flex h-[calc(100vh-120px)] bg-base-200 rounded-xl overflow-hidden border border-base-300">
    <!-- ─── Left: Node Palette ─────────────────────────── -->
    <div class="w-56 bg-base-100 border-r border-base-300 p-3 flex flex-col gap-3 overflow-y-auto shrink-0">
      <div class="flex items-center justify-between">
        <h3 class="font-bold text-sm uppercase tracking-wider opacity-60">Nodes</h3>
      </div>

      <!-- Agent Nodes -->
      <div class="text-xs font-bold opacity-40 uppercase tracking-wider mt-2">Agents</div>
      <div
        v-for="item in paletteItems.agents"
        :key="item.agentId"
        class="p-2 rounded-lg border border-base-300 bg-base-100 cursor-grab hover:border-primary hover:bg-primary/5 transition-all text-sm flex items-center gap-2"
        draggable="true"
        @dragstart="onDragStart($event, item)"
      >
        <div class="w-6 h-6 rounded-full bg-primary/20 flex items-center justify-center text-xs">🤖</div>
        <div>
          <div class="font-medium text-xs">{{ item.label }}</div>
          <div class="text-[10px] opacity-50">{{ item.agentType }}</div>
        </div>
      </div>
      <div v-if="!paletteItems.agents.length" class="text-xs opacity-40 text-center py-2">
        No agents assigned
      </div>

      <!-- Logic Nodes -->
      <div class="text-xs font-bold opacity-40 uppercase tracking-wider mt-3">Logic</div>
      <div
        v-for="item in paletteItems.logic"
        :key="item.nodeType"
        class="p-2 rounded-lg border border-base-300 bg-base-100 cursor-grab hover:border-warning hover:bg-warning/5 transition-all text-sm flex items-center gap-2"
        draggable="true"
        @dragstart="onDragStart($event, item)"
      >
        <span class="text-base">
          {{ item.nodeType === 'start' ? '▶' : item.nodeType === 'end' ? '⏹' : item.nodeType === 'router' ? '⑂' : item.nodeType === 'merge' ? '⤵' : '⚡' }}
        </span>
        <span class="font-medium text-xs">{{ item.label }}</span>
      </div>
    </div>

    <!-- ─── Center: Canvas ─────────────────────────────── -->
    <div class="flex-1 relative" @dragover="onDragOver" @drop="onDrop">
      <!-- Toolbar -->
      <div class="absolute top-3 left-3 z-10 flex items-center gap-2">
        <input
          v-model="workflowName"
          class="input input-bordered input-sm bg-base-100/90 backdrop-blur font-bold"
          placeholder="Workflow Name"
        />
        <button
          class="btn btn-primary btn-sm"
          :class="{ 'loading': isSaving }"
          :disabled="isSaving"
          @click="saveWorkflow"
        >
          {{ isSaving ? 'Saving...' : '💾 Save' }}
        </button>
      </div>

      <!-- Loading -->
      <div v-if="isLoading" class="absolute inset-0 flex items-center justify-center bg-base-200/80 z-20">
        <span class="loading loading-spinner loading-lg text-primary"></span>
      </div>

      <!-- Vue Flow Canvas -->
      <VueFlow
        v-model:nodes="nodes"
        v-model:edges="edges"
        :node-types="nodeTypes"
        :default-edge-options="{ type: 'smoothstep', animated: false, markerEnd: MarkerType.ArrowClosed }"
        :fit-view-on-init="true"
        :snap-to-grid="true"
        :snap-grid="[16, 16]"
        class="h-full"
        @click="closePanel"
      >
        <Background variant="dots" :gap="16" />
        <Controls />
      </VueFlow>
    </div>

    <!-- ─── Right: Properties Panel ────────────────────── -->
    <PropertiesPanel
      :selected-element="selectedElement"
      :element-type="selectedElementType"
      :agents="roomAgents"
      @update:node="onUpdateNode"
      @update:edge="onUpdateEdge"
      @delete="onDeleteElement"
      @close="closePanel"
    />
  </div>
</template>

<style scoped>
.workflow-editor {
  font-family: inherit;
}

/* Override Vue Flow defaults for dark mode compatibility */
:deep(.vue-flow__background) {
  background-color: oklch(var(--b2));
}
:deep(.vue-flow__edge-path) {
  stroke: oklch(var(--bc) / 0.3);
  stroke-width: 2;
}
:deep(.vue-flow__edge.selected .vue-flow__edge-path) {
  stroke: oklch(var(--p));
  stroke-width: 3;
}
:deep(.vue-flow__controls) {
  background: oklch(var(--b1));
  border: 1px solid oklch(var(--bc) / 0.1);
  border-radius: 0.75rem;
  box-shadow: 0 4px 6px -1px oklch(0 0 0 / 0.1);
}
:deep(.vue-flow__controls-button) {
  background: transparent;
  border: none;
  color: oklch(var(--bc));
}
:deep(.vue-flow__controls-button:hover) {
  background: oklch(var(--p) / 0.1);
}
</style>

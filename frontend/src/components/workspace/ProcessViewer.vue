<script setup lang="ts">
import { ref, watch } from 'vue'
import { VueFlow, useVueFlow, type Node, type Edge } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import type { Artifact, ProcessContent } from '@/types/artifact'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import '@vue-flow/controls/dist/style.css'

const props = defineProps<{
  artifact: Artifact,
  editable?: boolean
}>()

const emit = defineEmits<{
  (e: 'update', content: ProcessContent): void
}>()

// Convert Artifact content to Vue Flow format
// We need to map our ProcessNode to Vue Flow Node
const initialContent = props.artifact.content as ProcessContent
const nodes = ref<Node[]>(initialContent.nodes?.map(n => ({...n, data: n.data || {}})) || [])
const edges = ref<Edge[]>(initialContent.edges?.map(e => ({...e})) || [])

const { onNodeDragStop, onConnect, addEdges } = useVueFlow()

// Handle node drag stop - save position
onNodeDragStop((e) => {
  // Update internal state
  const targetNode = nodes.value.find(n => n.id === e.node.id)
  if (targetNode) {
    targetNode.position = e.node.position
  }
  emitUpdate()
})

onConnect((params) => {
  if (!props.editable) return
  addEdges([params])
  emitUpdate()
})

function emitUpdate() {
  emit('update', {
    nodes: nodes.value.map(n => ({
      id: n.id,
      position: n.position,
      label: n.label as string, // Vue Flow uses 'label' or 'data.label'
      type: n.type,
      data: n.data
    })),
    edges: edges.value.map(e => ({
      id: e.id,
      source: e.source,
      target: e.target,
      label: e.label as string
    }))
  })
}

// Watch for external updates
// Watch for external updates
watch(() => props.artifact.content, (newContent) => {
  const content = newContent as ProcessContent
  
  // Deep compare to avoid unnecessary re-renders or loops
  // We compare the incoming content with our local state
  const currentNodesJson = JSON.stringify(nodes.value.map(n => ({
      id: n.id,
      type: n.type,
      position: n.position,
      data: n.data,
      label: n.label
  })))
  const newNodesJson = JSON.stringify(content.nodes || [])
  
  if (currentNodesJson !== newNodesJson) {
      nodes.value = (content.nodes || []).map(n => ({...n, data: n.data || {}}))
  }

  const currentEdgesJson = JSON.stringify(edges.value)
  const newEdgesJson = JSON.stringify(content.edges || [])

  if (currentEdgesJson !== newEdgesJson) {
      edges.value = (content.edges || []).map(e => ({...e}))
  }
}, { deep: true })

function addNode() {
  const id = `node-${nodes.value.length + 1}`
  const newNode: Node = {
    id,
    label: `Node ${nodes.value.length + 1}`,
    position: { x: Math.random() * 400, y: Math.random() * 400 },
    type: 'default' // or 'input', 'output'
  }
  nodes.value.push(newNode)
  emitUpdate()
}

</script>

<template>
  <div class="h-full w-full border border-base-200 rounded-box bg-base-100 flex flex-col">
    <!-- Toolbar -->
    <div v-if="editable" class="p-2 border-b border-base-200 flex gap-2">
      <button @click="addNode" class="btn btn-sm btn-primary">Add Node</button>
      <div class="text-xs text-base-content/50 self-center ml-auto">
        {{ nodes.length }} nodes, {{ edges.length }} edges
      </div>
    </div>

    <!-- Graph -->
    <div class="flex-1 w-full h-full">
      <VueFlow
        v-model:nodes="nodes"
        v-model:edges="edges"
        :fit-view-on-init="true"
        :nodes-draggable="editable"
        :nodes-connectable="editable"
        class="process-flow"
      >
        <Background />
        <Controls />
      </VueFlow>
    </div>
  </div>
</template>

<style>
/* Vue Flow custom styles if needed */
.process-flow {
  background: var(--b1);
}
</style>

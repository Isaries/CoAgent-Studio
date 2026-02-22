<script setup lang="ts">
/**
 * RoomGraphView — Interactive knowledge graph visualization.
 *
 * Uses a canvas-based force-directed layout to render the room's
 * entity graph. Nodes are color-coded by type.
 */
import { ref, onMounted, onUnmounted, watch, computed } from 'vue'
import { graphService } from '../../services/graphService'
import type { GraphData, GraphNode } from '../../types/graph'
import { NODE_COLORS } from '../../types/graph'

const props = defineProps<{
  roomId: string
}>()

const graphData = ref<GraphData | null>(null)
const loading = ref(false)
const error = ref('')
const selectedNode = ref<GraphNode | null>(null)
const filterType = ref<string>('ALL')
const searchQuery = ref('')

// Canvas refs
const canvasRef = ref<HTMLCanvasElement | null>(null)
let animationId: number | null = null

// Simulation state
interface SimNode extends GraphNode {
  x: number
  y: number
  vx: number
  vy: number
  radius: number
}
let simNodes: SimNode[] = []
let simEdges: { source: SimNode; target: SimNode; relation: string; evidence: string }[] = []

// Entity types for filter dropdown
const entityTypes = computed(() => {
  if (!graphData.value) return ['ALL']
  const types = new Set(graphData.value.nodes.map(n => n.type))
  return ['ALL', ...Array.from(types).sort()]
})

// Filtered nodes
const filteredNodes = computed(() => {
  if (!graphData.value) return []
  let nodes = graphData.value.nodes
  if (filterType.value !== 'ALL') {
    nodes = nodes.filter(n => n.type === filterType.value)
  }
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    nodes = nodes.filter(n => n.name.toLowerCase().includes(q) || n.description.toLowerCase().includes(q))
  }
  return nodes
})

// Related edges for selected node
const relatedEdges = computed(() => {
  if (!selectedNode.value || !graphData.value) return []
  const name = selectedNode.value.name
  return graphData.value.edges.filter(e => e.source === name || e.target === name)
})

async function loadGraph() {
  loading.value = true
  error.value = ''
  try {
    graphData.value = await graphService.getGraph(props.roomId)
    initSimulation()
  } catch (e: any) {
    error.value = e?.response?.data?.detail || 'Failed to load graph'
  } finally {
    loading.value = false
  }
}

function initSimulation() {
  if (!graphData.value || !canvasRef.value) return

  const canvas = canvasRef.value
  const width = canvas.clientWidth
  const height = canvas.clientHeight
  canvas.width = width
  canvas.height = height

  // Create simulation nodes with random positions
  simNodes = graphData.value.nodes.map(n => ({
    ...n,
    x: Math.random() * width,
    y: Math.random() * height,
    vx: 0,
    vy: 0,
    radius: 8,
  }))

  // Map edges to simulation nodes
  const nodeMap = new Map(simNodes.map(n => [n.name, n]))
  simEdges = graphData.value.edges
    .map(e => {
      const source = nodeMap.get(e.source)
      const target = nodeMap.get(e.target)
      if (source && target) {
        return { source, target, relation: e.relation, evidence: e.evidence }
      }
      return null
    })
    .filter((e): e is NonNullable<typeof e> => e !== null)

  startAnimation()
}

function startAnimation() {
  if (animationId) cancelAnimationFrame(animationId)

  function tick() {
    simulateForces()
    render()
    animationId = requestAnimationFrame(tick)
  }
  tick()
}

function simulateForces() {
  if (!canvasRef.value) return
  const width = canvasRef.value.width
  const height = canvasRef.value.height
  const centerX = width / 2
  const centerY = height / 2

  // Center gravity
  for (const node of simNodes) {
    node.vx += (centerX - node.x) * 0.0005
    node.vy += (centerY - node.y) * 0.0005
  }

  // Repulsion between nodes
  for (let i = 0; i < simNodes.length; i++) {
    for (let j = i + 1; j < simNodes.length; j++) {
      const a = simNodes[i]!
      const b = simNodes[j]!
      let dx = b.x - a.x
      let dy = b.y - a.y
      const dist = Math.max(Math.sqrt(dx * dx + dy * dy), 1)
      const force = 800 / (dist * dist)
      const fx = (dx / dist) * force
      const fy = (dy / dist) * force
      a.vx -= fx
      a.vy -= fy
      b.vx += fx
      b.vy += fy
    }
  }

  // Attraction along edges
  for (const edge of simEdges) {
    const dx = edge.target.x - edge.source.x
    const dy = edge.target.y - edge.source.y
    const dist = Math.sqrt(dx * dx + dy * dy)
    const force = (dist - 120) * 0.005
    const fx = (dx / dist) * force
    const fy = (dy / dist) * force
    edge.source.vx += fx
    edge.source.vy += fy
    edge.target.vx -= fx
    edge.target.vy -= fy
  }

  // Apply velocity + damping
  for (const node of simNodes) {
    node.vx *= 0.9
    node.vy *= 0.9
    node.x += node.vx
    node.y += node.vy
    // Bounds
    node.x = Math.max(20, Math.min(width - 20, node.x))
    node.y = Math.max(20, Math.min(height - 20, node.y))
  }
}

function render() {
  if (!canvasRef.value) return
  const ctx = canvasRef.value.getContext('2d')
  if (!ctx) return

  const width = canvasRef.value.width
  const height = canvasRef.value.height

  // Clear
  ctx.fillStyle = '#0f172a'
  ctx.fillRect(0, 0, width, height)

  // Draw edges
  ctx.strokeStyle = 'rgba(148, 163, 184, 0.3)'
  ctx.lineWidth = 1
  for (const edge of simEdges) {
    ctx.beginPath()
    ctx.moveTo(edge.source.x, edge.source.y)
    ctx.lineTo(edge.target.x, edge.target.y)
    ctx.stroke()

    // Edge label
    const mx = (edge.source.x + edge.target.x) / 2
    const my = (edge.source.y + edge.target.y) / 2
    ctx.fillStyle = 'rgba(148, 163, 184, 0.5)'
    ctx.font = '9px Inter, sans-serif'
    ctx.textAlign = 'center'
    ctx.fillText(edge.relation, mx, my - 4)
  }

  // Visible names set for filtering
  const visibleNames = new Set(filteredNodes.value.map(n => n.name))

  // Draw nodes
  for (const node of simNodes) {
    const visible = visibleNames.has(node.name)
    const isSelected = selectedNode.value?.name === node.name
    const color: string = NODE_COLORS[node.type] ?? NODE_COLORS.DEFAULT ?? '#6B7280'
    const radius = isSelected ? 14 : node.radius

    ctx.globalAlpha = visible ? 1 : 0.15

    // Glow for selected
    if (isSelected) {
      ctx.beginPath()
      ctx.arc(node.x, node.y, radius + 6, 0, Math.PI * 2)
      ctx.fillStyle = color + '33'
      ctx.fill()
    }

    // Node circle
    ctx.beginPath()
    ctx.arc(node.x, node.y, radius, 0, Math.PI * 2)
    ctx.fillStyle = color
    ctx.fill()
    ctx.strokeStyle = isSelected ? '#fff' : 'rgba(255,255,255,0.3)'
    ctx.lineWidth = isSelected ? 2 : 1
    ctx.stroke()

    // Label
    ctx.fillStyle = '#e2e8f0'
    ctx.font = `${isSelected ? 'bold ' : ''}11px Inter, sans-serif`
    ctx.textAlign = 'center'
    ctx.fillText(node.name, node.x, node.y + radius + 14)
  }

  ctx.globalAlpha = 1
}

function handleCanvasClick(e: MouseEvent) {
  if (!canvasRef.value) return
  const rect = canvasRef.value.getBoundingClientRect()
  const x = e.clientX - rect.left
  const y = e.clientY - rect.top

  // Find closest node
  let closest: SimNode | null = null
  let minDist = Infinity
  for (const node of simNodes) {
    const dist = Math.sqrt((node.x - x) ** 2 + (node.y - y) ** 2)
    if (dist < 20 && dist < minDist) {
      minDist = dist
      closest = node
    }
  }

  selectedNode.value = closest
}

onMounted(() => {
  loadGraph()
})

onUnmounted(() => {
  if (animationId) cancelAnimationFrame(animationId)
})

watch(() => props.roomId, () => {
  loadGraph()
})
</script>

<template>
  <div class="flex h-full bg-slate-900 text-slate-200">
    <!-- Graph Canvas -->
    <div class="flex-1 flex flex-col">
      <!-- Toolbar -->
      <div class="flex items-center gap-3 p-3 border-b border-slate-700 bg-slate-800/50">
        <h3 class="text-sm font-semibold text-slate-300">🧠 Knowledge Graph</h3>

        <input
          v-model="searchQuery"
          type="text"
          placeholder="Search entities..."
          class="input input-sm input-bordered bg-slate-700 text-slate-200 w-48"
        />

        <select
          v-model="filterType"
          class="select select-sm select-bordered bg-slate-700 text-slate-200"
        >
          <option v-for="t in entityTypes" :key="t" :value="t">{{ t }}</option>
        </select>

        <div class="ml-auto text-xs text-slate-400" v-if="graphData">
          {{ graphData.node_count }} nodes · {{ graphData.edge_count }} edges
        </div>
      </div>

      <!-- Canvas -->
      <div class="flex-1 relative">
        <div v-if="loading" class="absolute inset-0 flex items-center justify-center bg-slate-900/80 z-10">
          <span class="loading loading-spinner loading-lg text-primary"></span>
        </div>
        <div v-else-if="error" class="absolute inset-0 flex items-center justify-center">
          <div class="text-center">
            <p class="text-red-400 mb-2">{{ error }}</p>
            <button class="btn btn-sm btn-outline" @click="loadGraph">Retry</button>
          </div>
        </div>
        <div v-else-if="graphData && graphData.node_count === 0" class="absolute inset-0 flex items-center justify-center">
          <div class="text-center text-slate-400">
            <p class="text-lg mb-2">No graph data yet</p>
            <p class="text-sm">Use the Analytics panel to build the knowledge graph first.</p>
          </div>
        </div>
        <canvas
          ref="canvasRef"
          class="w-full h-full cursor-crosshair"
          @click="handleCanvasClick"
        ></canvas>
      </div>
    </div>

    <!-- Detail Sidebar -->
    <div
      v-if="selectedNode"
      class="w-80 border-l border-slate-700 bg-slate-800/80 overflow-y-auto"
    >
      <div class="p-4">
        <div class="flex items-center justify-between mb-3">
          <h4 class="font-bold text-base">{{ selectedNode.name }}</h4>
          <button class="btn btn-ghost btn-xs" @click="selectedNode = null">✕</button>
        </div>

        <div class="badge badge-sm mb-3" :style="{ background: NODE_COLORS[selectedNode.type] || NODE_COLORS.DEFAULT }">
          {{ selectedNode.type }}
        </div>

        <p class="text-sm text-slate-300 mb-4">{{ selectedNode.description }}</p>

        <div v-if="selectedNode.community_id != null" class="text-xs text-slate-400 mb-4">
          Community #{{ selectedNode.community_id }}
        </div>

        <!-- Related Edges -->
        <div v-if="relatedEdges.length > 0">
          <h5 class="text-xs font-semibold text-slate-400 uppercase mb-2">Relationships</h5>
          <div
            v-for="(edge, i) in relatedEdges"
            :key="i"
            class="mb-2 p-2 rounded bg-slate-700/50 text-xs"
          >
            <div class="font-medium text-slate-200">
              {{ edge.source }} → <span class="text-primary">{{ edge.relation }}</span> → {{ edge.target }}
            </div>
            <div class="text-slate-400 mt-1">{{ edge.evidence }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

import { shallowRef } from 'vue'
import type { KnowledgeNode, NetworkLine } from '../types/visuals'
import { SYMBOLS_POOL } from '../types/visuals'

export function useKnowledgeEffect() {
  const knowledgeNodes = shallowRef<KnowledgeNode[]>([])
  const networkLines = shallowRef<NetworkLine[]>([])
  let uiAnimFrame = 0

  const generateKnowledgeBurst = (xPercent: number, yPercent: number) => {
    const burstCount = 6 + Math.floor(Math.random() * 4) // 6-10 items
    const nodes: KnowledgeNode[] = []

    // Create Nodes (Symbols)
    for (let i = 0; i < burstCount; i++) {
      const angle = Math.random() * Math.PI * 2
      const speed = 0.1 + Math.random() * 0.15
      nodes.push({
        id: Date.now() + i + Math.random(),
        x: xPercent + (Math.random() - 0.5) * 1.5,
        y: yPercent + (Math.random() - 0.5) * 1.5,
        text: SYMBOLS_POOL[Math.floor(Math.random() * SYMBOLS_POOL.length)] || '∑',
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed - 0.1, // Float upward
        opacity: 1,
        scale: 0.8 + Math.random() * 0.7
      })
    }

    // Optimization: avoid pushing one by one if using shallowRef, replace array
    const newNodes = [...knowledgeNodes.value, ...nodes]

    // Connect new nodes to each other
    const newLines: NetworkLine[] = []
    for (let i = 0; i < nodes.length; i++) {
      const nI = nodes[i]
      for (let j = i + 1; j < nodes.length; j++) {
        const nJ = nodes[j]
        if (nI && nJ && Math.random() > 0.5) {
          newLines.push({
            id: `${nI.id}-${nJ.id}`,
            from: nI.id,
            to: nJ.id,
            opacity: 0.6
          })
        }
      }
    }

    knowledgeNodes.value = newNodes
    networkLines.value = [...networkLines.value, ...newLines]
  }

  let isAnimating = false

  const animateUI = () => {
    if (isAnimating) return // Prevent multiple loops
    isAnimating = true

    const loop = () => {
      const nodes = knowledgeNodes.value
      const lines = networkLines.value

      // Update Nodes
      for (let i = 0; i < nodes.length; i++) {
        const node = nodes[i]
        if (node && node.opacity > 0) {
          node.x += node.vx
          node.y += node.vy
          node.opacity -= 0.006
          node.vy -= 0.002
        }
      }

      // Update Lines
      for (let i = 0; i < lines.length; i++) {
        const line = lines[i]
        if (!line) continue

        const n1 = nodes.find((n) => n.id === line.from)
        const n2 = nodes.find((n) => n.id === line.to)
        if (n1 && n2 && n1.opacity > 0 && n2.opacity > 0) {
          line.opacity = Math.min(n1.opacity, n2.opacity) * 0.5
        } else {
          line.opacity = 0
        }
      }

      // Cleanup (Batch removal)
      if (nodes.some((n) => n.opacity <= 0)) {
        knowledgeNodes.value = nodes.filter((n) => n.opacity > 0)
        networkLines.value = lines.filter((l) => l.opacity > 0)
      } else {
        knowledgeNodes.value = [...nodes]
      }

      if (knowledgeNodes.value.length > 0) {
        uiAnimFrame = requestAnimationFrame(loop)
      } else {
        isAnimating = false
      }
    }

    loop()
  }

  const cleanupEffect = () => {
    cancelAnimationFrame(uiAnimFrame)
    knowledgeNodes.value = []
    networkLines.value = []
    isAnimating = false
  }

  // Helper
  const getNodeById = (id: number) => knowledgeNodes.value.find((n) => n.id === id)

  return {
    knowledgeNodes,
    networkLines,
    generateKnowledgeBurst,
    animateUI,
    cleanupEffect,
    getNodeById
  }
}

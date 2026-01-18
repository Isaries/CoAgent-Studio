<script setup lang="ts">
import { ref, onUnmounted } from 'vue'

const props = withDefaults(defineProps<{
  initialLeftWidth?: number
  minLeftWidth?: number
  minRightWidth?: number
}>(), {
  initialLeftWidth: 500, // px
  minLeftWidth: 300,
  minRightWidth: 400
})

const containerRef = ref<HTMLElement | null>(null)
const leftWidth = ref(props.initialLeftWidth)
const isDragging = ref(false)

const startDrag = () => {
  isDragging.value = true
  document.body.style.cursor = 'col-resize'
  document.body.style.userSelect = 'none'
  window.addEventListener('mousemove', onDrag)
  window.addEventListener('mouseup', stopDrag)
}

const onDrag = (e: MouseEvent) => {
  if (!isDragging.value || !containerRef.value) return
  
  const containerRect = containerRef.value.getBoundingClientRect()
  const newWidth = e.clientX - containerRect.left
  
  // Apply Constraints
  const maxLeftWidth = containerRect.width - props.minRightWidth
  
  if (newWidth >= props.minLeftWidth && newWidth <= maxLeftWidth) {
    leftWidth.value = newWidth
  }
}

const stopDrag = () => {
  isDragging.value = false
  document.body.style.cursor = ''
  document.body.style.userSelect = ''
  window.removeEventListener('mousemove', onDrag)
  window.removeEventListener('mouseup', stopDrag)
}

onUnmounted(() => {
  window.removeEventListener('mousemove', onDrag)
  window.removeEventListener('mouseup', stopDrag)
})
</script>

<template>
  <div ref="containerRef" class="flex h-full w-full overflow-hidden relative">
    
    <!-- Left Pane -->
    <div :style="{ width: leftWidth + 'px' }" class="flex-shrink-0 h-full relative z-10">
      <slot name="left"></slot>
      
      <!-- Drag Overlay only when dragging to prevent iframe stealing (if any) -->
      <div v-if="isDragging" class="absolute inset-0 z-50 bg-transparent"></div>
    </div>

    <!-- Resizer Handle -->
    <div 
      class="w-[4px] hover:w-[6px] group cursor-col-resize relative z-20 flex-shrink-0 bg-base-300 hover:bg-primary/50 transition-all duration-200 border-l border-white/5 active:bg-primary"
      @mousedown.prevent="startDrag"
    >
       <!-- Handle visual indicator -->
       <div class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[2px] h-8 bg-white/20 rounded-full group-hover:bg-white/50 transition-colors"></div>
    </div>

    <!-- Right Pane -->
    <div class="flex-1 h-full min-w-0 relative z-0">
      <slot name="right"></slot>
         <!-- Drag Overlay only when dragging -->
         <div v-if="isDragging" class="absolute inset-0 z-50 bg-transparent"></div>
    </div>

  </div>
</template>

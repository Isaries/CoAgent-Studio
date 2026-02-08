<script setup lang="ts">
/**
 * KanbanBoard - Main Kanban board component for workspace.
 */
import { ref, onMounted, watch } from 'vue'
import { useWorkspaceStore } from '@/stores/workspace'
import KanbanColumn from './KanbanColumn.vue'
import type { TaskContent } from '@/types/artifact'

const props = defineProps<{
  roomId: string
}>()

const store = useWorkspaceStore()

// New task modal
const showAddModal = ref(false)
const newTaskTitle = ref('')
const addingTask = ref(false)

// Edit task modal
const showEditModal = ref(false)
const editingTaskId = ref<string | null>(null)
const editingTitle = ref('')

onMounted(() => {
  store.loadArtifacts(props.roomId)
})

watch(() => props.roomId, (newId) => {
  if (newId) {
    store.loadArtifacts(newId)
  }
})

async function handleDrop({ taskId, newStatus }: { taskId: string; newStatus: string }) {
  await store.moveTask(taskId, newStatus as TaskContent['status'])
}

async function handleAddTask() {
  if (!newTaskTitle.value.trim()) return
  
  addingTask.value = true
  await store.createTask(newTaskTitle.value.trim())
  newTaskTitle.value = ''
  showAddModal.value = false
  addingTask.value = false
}

function openEditModal(taskId: string) {
  const task = store.artifacts.find(a => a.id === taskId)
  if (task) {
    editingTaskId.value = taskId
    editingTitle.value = task.title
    showEditModal.value = true
  }
}

async function handleEditTask() {
  if (!editingTaskId.value || !editingTitle.value.trim()) return
  
  await store.updateTask(editingTaskId.value, { title: editingTitle.value.trim() })
  showEditModal.value = false
  editingTaskId.value = null
  editingTitle.value = ''
}

async function handleDeleteTask(taskId: string) {
  if (confirm('確定要刪除此任務嗎？')) {
    await store.deleteTask(taskId)
  }
}
</script>

<template>
  <div class="flex flex-col h-full">
    <!-- Header -->
    <div class="flex items-center justify-between p-4 border-b border-base-200">
      <h2 class="text-lg font-semibold flex items-center gap-2">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2" />
        </svg>
        看板
      </h2>
      <button 
        class="btn btn-primary btn-sm"
        @click="showAddModal = true"
      >
        + 新增任務
      </button>
    </div>

    <!-- Loading -->
    <div v-if="store.loading" class="flex items-center justify-center flex-1">
      <span class="loading loading-spinner loading-lg"></span>
    </div>

    <!-- Error -->
    <div v-else-if="store.error" class="alert alert-error m-4">
      {{ store.error }}
    </div>

    <!-- Board -->
    <div v-else class="flex gap-4 p-4 overflow-x-auto flex-1">
      <KanbanColumn
        v-for="column in store.kanbanColumns"
        :key="column.id"
        :column="column"
        @drop="handleDrop"
        @edit="openEditModal"
        @delete="handleDeleteTask"
        @add="showAddModal = true"
      />
    </div>

    <!-- Add Task Modal -->
    <dialog :class="{ 'modal modal-open': showAddModal, 'modal': !showAddModal }">
      <div class="modal-box">
        <h3 class="font-bold text-lg mb-4">新增任務</h3>
        <input 
          v-model="newTaskTitle"
          type="text"
          placeholder="任務標題"
          class="input input-bordered w-full"
          @keyup.enter="handleAddTask"
        />
        <div class="modal-action">
          <button class="btn btn-ghost" @click="showAddModal = false">取消</button>
          <button 
            class="btn btn-primary"
            :disabled="!newTaskTitle.trim() || addingTask"
            @click="handleAddTask"
          >
            <span v-if="addingTask" class="loading loading-spinner loading-sm"></span>
            新增
          </button>
        </div>
      </div>
      <form method="dialog" class="modal-backdrop" @click="showAddModal = false">
        <button>close</button>
      </form>
    </dialog>

    <!-- Edit Task Modal -->
    <dialog :class="{ 'modal modal-open': showEditModal, 'modal': !showEditModal }">
      <div class="modal-box">
        <h3 class="font-bold text-lg mb-4">編輯任務</h3>
        <input 
          v-model="editingTitle"
          type="text"
          placeholder="任務標題"
          class="input input-bordered w-full"
          @keyup.enter="handleEditTask"
        />
        <div class="modal-action">
          <button class="btn btn-ghost" @click="showEditModal = false">取消</button>
          <button 
            class="btn btn-primary"
            :disabled="!editingTitle.trim()"
            @click="handleEditTask"
          >
            儲存
          </button>
        </div>
      </div>
      <form method="dialog" class="modal-backdrop" @click="showEditModal = false">
        <button>close</button>
      </form>
    </dialog>
  </div>
</template>

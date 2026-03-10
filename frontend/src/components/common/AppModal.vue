<script setup lang="ts">
import { ref, watch, onMounted, onBeforeUnmount } from 'vue'

export type ModalSize = 'sm' | 'md' | 'lg' | 'xl'

const props = withDefaults(
  defineProps<{
    modelValue: boolean
    title?: string
    size?: ModalSize
    closable?: boolean
    /** Extra CSS classes for modal-box (e.g. 'overflow-visible') */
    boxClass?: string
  }>(),
  {
    size: 'md',
    closable: true
  }
)

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'close'): void
}>()

const dialogRef = ref<HTMLDialogElement | null>(null)

const sizeClass: Record<ModalSize, string> = {
  sm: 'max-w-sm',
  md: 'max-w-lg',
  lg: 'max-w-2xl',
  xl: 'max-w-4xl'
}

function closeModal() {
  if (!props.closable) return
  emit('update:modelValue', false)
  emit('close')
}

function handleBackdropClick() {
  closeModal()
}

function handleCancel(event: Event) {
  // The cancel event fires when Escape is pressed on an open <dialog>
  if (!props.closable) {
    event.preventDefault()
    return
  }
  emit('update:modelValue', false)
  emit('close')
}

watch(
  () => props.modelValue,
  (open) => {
    const dialog = dialogRef.value
    if (!dialog) return

    if (open) {
      if (!dialog.open) {
        dialog.showModal()
      }
    } else {
      if (dialog.open) {
        dialog.close()
      }
    }
  }
)

onMounted(() => {
  // Sync initial state
  if (props.modelValue && dialogRef.value && !dialogRef.value.open) {
    dialogRef.value.showModal()
  }
})

onBeforeUnmount(() => {
  // Clean up: close dialog if still open when component unmounts
  if (dialogRef.value?.open) {
    dialogRef.value.close()
  }
})

defineExpose({
  /** Direct access to the dialog element if needed */
  dialogRef
})
</script>

<template>
  <dialog
    ref="dialogRef"
    class="modal"
    @cancel="handleCancel"
  >
    <div class="modal-box" :class="[sizeClass[size], boxClass]">
      <!-- Close button (top-right) -->
      <button
        v-if="closable"
        class="btn btn-sm btn-circle btn-ghost absolute right-3 top-3"
        @click="closeModal"
        aria-label="Close"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          class="h-5 w-5"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          stroke-width="2"
        >
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>

      <!-- Title -->
      <h3 v-if="title" class="font-bold text-lg pr-8">{{ title }}</h3>

      <!-- Default slot: modal content -->
      <slot />

      <!-- Footer/actions slot -->
      <div v-if="$slots.actions" class="modal-action">
        <slot name="actions" />
      </div>
    </div>

    <!-- Backdrop click to close -->
    <form method="dialog" class="modal-backdrop">
      <button @click="handleBackdropClick">close</button>
    </form>
  </dialog>
</template>

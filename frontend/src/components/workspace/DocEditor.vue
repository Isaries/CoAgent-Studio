<script setup lang="ts">
import { useEditor, EditorContent } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'
import Placeholder from '@tiptap/extension-placeholder'
import { watch, onBeforeUnmount, ref } from 'vue'
import type { Artifact, DocContent } from '@/types/artifact'

const props = defineProps<{
  artifact: Artifact,
  editable?: boolean
}>()

const emit = defineEmits<{
  (e: 'update', content: DocContent): void
  (e: 'save'): void
}>()

const isSaving = ref(false)
const lastSavedContent = ref('')

const editor = useEditor({
  content: (props.artifact.content as DocContent).content || {},
  editable: props.editable ?? true,
  extensions: [
    StarterKit,
    Placeholder.configure({
      placeholder: 'Write something amazing...',
    }),
  ],
  onUpdate: ({ editor }) => {
    // Debounced save could go here, or just emit update
    const json = editor.getJSON()
    // Simple change detection
    if (JSON.stringify(json) !== lastSavedContent.value) {
       emit('update', { type: 'doc', content: json as any })
    }
  },
})

const remoteChangePending = ref(false)
const pendingContent = ref<any>(null)

// Watch for external changes (e.g. real-time updates from other users)
watch(() => props.artifact.content, (newContent) => {
  const newJSON = (newContent as DocContent).content
  const currentJSON = editor.value?.getJSON()

  // Compare
  if (JSON.stringify(currentJSON) !== JSON.stringify(newJSON)) {
    if (editor.value && !editor.value.isFocused) {
      // Safe to update if not focused
      editor.value.commands.setContent(newJSON || {})
    } else {
      // User is editing, flag it
      remoteChangePending.value = true
      pendingContent.value = newJSON
    }
  }
}, { deep: true })

function applyRemoteContent() {
  if (editor.value && pendingContent.value) {
    // We could try to preserve cursor, but setContent usually resets it.
    // Ideally we merge, but for now just load valid state.
    editor.value.commands.setContent(pendingContent.value || {})
    remoteChangePending.value = false
    pendingContent.value = null
  }
}

onBeforeUnmount(() => {
  editor.value?.destroy()
})
</script>

<template>
  <div class="flex flex-col h-full bg-base-100 rounded-box shadow-sm overflow-hidden border border-base-200">
    <!-- Toolbar -->
    <div v-if="editor" class="flex items-center gap-1 p-2 border-b border-base-200 bg-base-200/30 overflow-x-auto">
      <button 
        @click="editor.chain().focus().toggleBold().run()"
        :class="{ 'is-active': editor.isActive('bold') }"
        class="btn btn-sm btn-ghost btn-square"
        title="Bold"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 4h8a4 4 0 0 1 4 4 4 4 0 0 1-4 4H6z"></path><path d="M6 12h9a4 4 0 0 1 4 4 4 4 0 0 1-4 4H6z"></path></svg>
      </button>
      <button 
        @click="editor.chain().focus().toggleItalic().run()"
        :class="{ 'is-active': editor.isActive('italic') }"
        class="btn btn-sm btn-ghost btn-square"
        title="Italic"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="19" y1="4" x2="10" y2="4"></line><line x1="14" y1="20" x2="5" y2="20"></line><line x1="15" y1="4" x2="9" y2="20"></line></svg>
      </button>
      <button 
        @click="editor.chain().focus().toggleStrike().run()"
        :class="{ 'is-active': editor.isActive('strike') }"
        class="btn btn-sm btn-ghost btn-square"
        title="Strike"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.3 19c.266-1.12.23-2.61-.4-4.1-.73-1.74-2.5-1.9-4.9-1.9H6v4h6c1.1 0 1.967.1 2.567.3.6.2 1.033.7 1.3 1.5.067.2.133.433.2.7"></path><path d="M14 5c.667.667 1 1.667 1 3 0 2-1 3.5-3 3.5H6V5h8z"></path><line x1="4" y1="12" x2="20" y2="12"></line></svg>
      </button>
      
      <div class="divider divider-horizontal mx-1"></div>

      <button 
        @click="editor.chain().focus().toggleHeading({ level: 1 }).run()"
        :class="{ 'is-active': editor.isActive('heading', { level: 1 }) }"
        class="btn btn-sm btn-ghost btn-square font-bold"
        title="H1"
      >
        H1
      </button>
      <button 
        @click="editor.chain().focus().toggleHeading({ level: 2 }).run()"
        :class="{ 'is-active': editor.isActive('heading', { level: 2 }) }"
        class="btn btn-sm btn-ghost btn-square font-bold"
        title="H2"
      >
        H2
      </button>

      <div class="divider divider-horizontal mx-1"></div>

      <button 
        @click="editor.chain().focus().toggleBulletList().run()"
        :class="{ 'is-active': editor.isActive('bulletList') }"
        class="btn btn-sm btn-ghost btn-square"
        title="Bullet List"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="8" y1="6" x2="21" y2="6"></line><line x1="8" y1="12" x2="21" y2="12"></line><line x1="8" y1="18" x2="21" y2="18"></line><line x1="3" y1="6" x2="3.01" y2="6"></line><line x1="3" y1="12" x2="3.01" y2="12"></line><line x1="3" y1="18" x2="3.01" y2="18"></line></svg>
      </button>
      <button 
        @click="editor.chain().focus().toggleOrderedList().run()"
        :class="{ 'is-active': editor.isActive('orderedList') }"
        class="btn btn-sm btn-ghost btn-square"
        title="Ordered List"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="10" y1="6" x2="21" y2="6"></line><line x1="10" y1="12" x2="21" y2="12"></line><line x1="10" y1="18" x2="21" y2="18"></line><path d="M4 6h1v4"></path><path d="M4 10h2"></path><path d="M6 18H4c0-1 2-2 2-3s-1-1.5-2-1"></path></svg>
      </button>
    </div>

    <!-- Editor Content -->
    <editor-content :editor="editor" class="flex-1 overflow-y-auto p-4 prose prose-sm max-w-none focus:outline-none" />
    
    <!-- Status Bar -->
    <div class="flex items-center justify-between px-4 py-2 text-xs text-base-content/50 border-t border-base-200">
       <span class="flex gap-2">
         {{ editor?.storage.characterCount.characters() }} characters
         <span v-if="remoteChangePending" class="text-warning font-bold cursor-pointer hover:underline" @click="applyRemoteContent">
           ⚠ Remote changes detected. Click to load.
         </span>
       </span>
       <span v-if="isSaving">Saving...</span>
       <span v-else>All changes saved</span>
    </div>
  </div>
</template>

<style lang="scss">
/* Basic editor styles */
.ProseMirror {
  outline: none;
  min-height: 100%;
  
  p.is-editor-empty:first-child::before {
    color: #adb5bd;
    content: attr(data-placeholder);
    float: left;
    height: 0;
    pointer-events: none;
  }
}

.is-active {
  background-color: oklch(var(--p) / 0.1);
  color: oklch(var(--p));
}
</style>

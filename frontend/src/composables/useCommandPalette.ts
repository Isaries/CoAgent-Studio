import { ref, computed, watch, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api'

export interface PaletteItem {
  id: string
  label: string
  category: string
  action: () => void
}

// ─── Singleton state (shared across all callers) ────────────────────────────
const isOpen = ref(false)
const query = ref('')
const selectedIndex = ref(0)
const apiResults = ref<PaletteItem[]>([])
let watcherRegistered = false
// ────────────────────────────────────────────────────────────────────────────

export function useCommandPalette() {
  const router = useRouter()
  let debounceTimer: ReturnType<typeof setTimeout> | null = null

  const staticPages: PaletteItem[] = [
    { id: 'home', label: 'Home', category: 'Pages', action: () => router.push('/') },
    { id: 'spaces', label: 'My Spaces', category: 'Pages', action: () => router.push('/spaces') },
    { id: 'agents', label: 'Agent Lab', category: 'Pages', action: () => router.push('/agents') },
    {
      id: 'my-agents',
      label: 'My Agents',
      category: 'Pages',
      action: () => router.push('/my-agents')
    },
    {
      id: 'workflows',
      label: 'Workflows',
      category: 'Pages',
      action: () => router.push('/platform/workflows')
    },
    {
      id: 'triggers',
      label: 'Triggers',
      category: 'Pages',
      action: () => router.push('/platform/triggers')
    },
    {
      id: 'knowledge',
      label: 'Knowledge Engine',
      category: 'Pages',
      action: () => router.push('/platform/knowledge')
    },
    {
      id: 'api-keys',
      label: 'My API Keys',
      category: 'Pages',
      action: () => router.push('/my-keys')
    },
    {
      id: 'analytics',
      label: 'Analytics',
      category: 'Pages',
      action: () => router.push('/analytics')
    },
    {
      id: 'dashboard',
      label: 'Dashboard',
      category: 'Pages',
      action: () => router.push('/dashboard')
    }
  ]

  const results = computed<PaletteItem[]>(() => {
    const q = query.value.toLowerCase().trim()
    if (!q) return staticPages.slice(0, 8)
    const filtered = staticPages.filter((p) => p.label.toLowerCase().includes(q))
    return [...filtered, ...apiResults.value].slice(0, 12)
  })

  const searchApi = async (q: string) => {
    if (!q.trim()) {
      apiResults.value = []
      return
    }
    try {
      const res = await api.get('/spaces/')
      apiResults.value = (res.data || [])
        .filter((s: any) => s.title.toLowerCase().includes(q.toLowerCase()))
        .slice(0, 5)
        .map((s: any) => ({
          id: `space-${s.id}`,
          label: s.title,
          category: 'Spaces',
          action: () => router.push(`/spaces/${s.id}`)
        }))
    } catch {
      apiResults.value = []
    }
  }

  if (!watcherRegistered) {
    watch(query, (val) => {
      selectedIndex.value = 0
      if (debounceTimer) clearTimeout(debounceTimer)
      debounceTimer = setTimeout(() => searchApi(val), 300)
    })
    watcherRegistered = true
  }

  onUnmounted(() => {
    if (debounceTimer) clearTimeout(debounceTimer)
  })

  const execute = (item: PaletteItem) => {
    item.action()
    close()
  }

  const open = () => {
    isOpen.value = true
    query.value = ''
    selectedIndex.value = 0
    apiResults.value = []
  }

  const close = () => {
    isOpen.value = false
    query.value = ''
  }

  const moveUp = () => {
    if (selectedIndex.value > 0) selectedIndex.value--
  }

  const moveDown = () => {
    if (selectedIndex.value < results.value.length - 1) selectedIndex.value++
  }

  const executeSelected = () => {
    const item = results.value[selectedIndex.value]
    if (item) execute(item)
  }

  return {
    isOpen,
    query,
    selectedIndex,
    results,
    open,
    close,
    execute,
    moveUp,
    moveDown,
    executeSelected
  }
}

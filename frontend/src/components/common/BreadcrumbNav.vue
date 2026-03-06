<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, type RouteLocationMatched } from 'vue-router'
const route = useRoute()

interface Crumb {
  label: string
  path: string
  isLast: boolean
}

const crumbs = computed<Crumb[]>(() => {
  const matched = route.matched.filter((r) => r.meta?.breadcrumb)
  return matched.map((record: RouteLocationMatched, idx: number) => {
    const bc = record.meta.breadcrumb
    const label = typeof bc === 'function' ? bc(route) : String(bc)
    return {
      label,
      path: record.path.replace(/:\w+/g, (param) => {
        const key = param.slice(1)
        return String(route.params[key] || param)
      }),
      isLast: idx === matched.length - 1
    }
  })
})
</script>

<template>
  <div v-if="crumbs.length > 0" class="text-sm breadcrumbs px-0 py-2">
    <ul>
      <li v-for="crumb in crumbs" :key="crumb.path">
        <router-link
          v-if="!crumb.isLast"
          :to="crumb.path"
          class="text-base-content/60 hover:text-base-content"
        >
          {{ crumb.label }}
        </router-link>
        <span v-else class="text-base-content font-medium" aria-current="page">
          {{ crumb.label }}
        </span>
      </li>
    </ul>
  </div>
</template>

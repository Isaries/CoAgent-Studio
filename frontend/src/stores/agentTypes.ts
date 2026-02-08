import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { agentTypesService } from '../services/agentTypesService'
import type { AgentTypeMetadata } from '../types/agentTypes'
import { AgentCategory } from '../types/enums'

export const useAgentTypesStore = defineStore('agentTypes', () => {
    // State
    const types = ref<AgentTypeMetadata[]>([])
    const loading = ref(false)
    const error = ref<string | null>(null)
    const lastFetched = ref<Date | null>(null)

    // Getters
    const instructorTypes = computed(() =>
        types.value.filter(t => t.category === AgentCategory.INSTRUCTOR || t.category === 'instructor')
    )

    const participantTypes = computed(() =>
        types.value.filter(t => t.category === AgentCategory.PARTICIPANT || t.category === 'participant')
    )

    const utilityTypes = computed(() =>
        types.value.filter(t => t.category === AgentCategory.UTILITY || t.category === 'utility')
    )

    const externalTypes = computed(() =>
        types.value.filter(t => t.category === AgentCategory.EXTERNAL || t.category === 'external')
    )

    const systemTypes = computed(() =>
        types.value.filter(t => t.is_system)
    )

    const customTypes = computed(() =>
        types.value.filter(t => !t.is_system)
    )

    const getTypeByName = (typeName: string) =>
        types.value.find(t => t.type_name === typeName)

    // Actions
    async function fetchTypes(force = false) {
        // Cache for 5 minutes
        if (!force && lastFetched.value && (Date.now() - lastFetched.value.getTime()) < 300000) {
            return types.value
        }

        loading.value = true
        error.value = null

        try {
            const response = await agentTypesService.list()
            types.value = response.data
            lastFetched.value = new Date()
            return types.value
        } catch (e) {
            error.value = e instanceof Error ? e.message : 'Failed to fetch agent types'
            throw e
        } finally {
            loading.value = false
        }
    }

    async function createType(data: Omit<AgentTypeMetadata, 'id' | 'is_system'>) {
        loading.value = true
        try {
            const response = await agentTypesService.create(data)
            types.value.push(response.data)
            return response.data
        } finally {
            loading.value = false
        }
    }

    async function deleteType(typeName: string) {
        loading.value = true
        try {
            await agentTypesService.delete(typeName)
            types.value = types.value.filter(t => t.type_name !== typeName)
        } finally {
            loading.value = false
        }
    }

    function clearCache() {
        lastFetched.value = null
    }

    return {
        // State
        types,
        loading,
        error,
        // Getters
        instructorTypes,
        participantTypes,
        utilityTypes,
        externalTypes,
        systemTypes,
        customTypes,
        getTypeByName,
        // Actions
        fetchTypes,
        createType,
        deleteType,
        clearCache
    }
})

import { ref } from 'vue'
import { agentService } from '../services/agentService'
import type { AgentConfigVersion } from '../types/agent'
import { useToastStore } from '../stores/toast'

export function useVersionControl(configId: string | undefined) {
    const versions = ref<AgentConfigVersion[]>([])
    const loadingVersions = ref(false)
    const showVersions = ref(false)
    const toast = useToastStore()

    const fetchVersions = async (overrideConfigId?: string) => {
        const id = overrideConfigId || configId
        if (!id) return

        loadingVersions.value = true
        try {
            const res = await agentService.getVersions(id)
            versions.value = res.data
        } catch (e: any) {
            console.error('Failed to fetch versions', e)
            toast.error('Failed to load version history')
        } finally {
            loadingVersions.value = false
        }
    }

    const createVersion = async (name: string, overrideConfigId?: string) => {
        const id = overrideConfigId || configId
        if (!id) return false

        try {
            await agentService.createVersion(id, { version_label: name })
            toast.success('Version saved')
            await fetchVersions(id)
            return true
        } catch (e: any) {
            toast.error('Failed to create version: ' + (e.response?.data?.detail || e.message))
            return false
        }
    }

    const restoreVersion = async (versionId: string, overrideConfigId?: string) => {
        const id = overrideConfigId || configId
        if (!id) return null

        try {
            const res = await agentService.restoreVersion(id, versionId)
            toast.success('Version restored')
            // Refresh versions list to show new restore point if any
            await fetchVersions(id)
            return res.data // Return the restored config
        } catch (e: any) {
            toast.error('Failed to restore version: ' + (e.response?.data?.detail || e.message))
            return null
        }
    }

    const toggleVersions = () => {
        showVersions.value = !showVersions.value
        if (showVersions.value && versions.value.length === 0) {
            fetchVersions()
        }
    }

    return {
        versions,
        loadingVersions,
        showVersions,
        toggleVersions,
        fetchVersions,
        createVersion,
        restoreVersion
    }
}

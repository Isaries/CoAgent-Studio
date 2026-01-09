<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '../api'
import { useToastStore } from '../stores/toast'
import { useConfirm } from '../composables/useConfirm'

// Config State
const loading = ref(false)
const toast = useToastStore()
const { confirm } = useConfirm()

const configs = ref({
    design: { prompt: '', apiKey: '', provider: 'gemini' },
    analytics: { prompt: '', apiKey: '', provider: 'gemini' }
})
// ... (lines 10-38 is fetchSettings, kept same logic reference but need to be careful with replacment range)
// Actually I should just prepend/append logic or pick a safe block.
// Let's replace the top block to init confirm, then append the handler function before onMounted.

const fetchSettings = async () => {
    loading.value = true
    try {
        const res = await api.get('/agents/system')
        const data = res.data
        
        const design = data.find((c: any) => c.type === 'design')
        if (design) {
            configs.value.design.prompt = design.system_prompt
            configs.value.design.provider = design.model_provider
        }

        const analytics = data.find((c: any) => c.type === 'analytics')
        if (analytics) {
            configs.value.analytics.prompt = analytics.system_prompt
            configs.value.analytics.provider = analytics.model_provider
        }
    } catch (e) {
        console.error("Failed to fetch system settings", e)
    } finally {
        loading.value = false
    }
}

const saveAgent = async (type: 'design' | 'analytics') => {
    const config = configs.value[type]
    try {
        await api.put(`/agents/system/${type}`, {
            system_prompt: config.prompt,
            api_key: config.apiKey,
            model_provider: config.provider,
            settings: {}
        })
        toast.success(`${type.toUpperCase()} Agent settings saved!`)
    } catch (e) {
        console.error(e)
        toast.error('Error saving settings')
    }
}

const handleClearApiKey = async (type: 'design' | 'analytics') => {
    if (!await confirm("Clear API Key", "Are you sure? This will remove the key immediately.")) return
    configs.value[type].apiKey = ''
    await saveAgent(type)
}

onMounted(() => {
    fetchSettings()
})
</script>

<template>
  <div class="p-6 max-w-4xl mx-auto">
    <div class="mb-8">
        <h1 class="text-3xl font-bold">System Agent Settings</h1>
        <p class="text-gray-500 text-sm mt-1">Configure global default behaviors for utility agents.</p>
    </div>

    <div v-if="loading" class="flex justify-center p-12">
        <span class="loading loading-spinner loading-lg text-primary"></span>
    </div>

    <div v-else class="grid grid-cols-1 gap-8">
        <!-- Design Agent -->
        <div class="card bg-base-100 shadow-xl border border-base-300">
            <div class="card-body">
                <div class="flex justify-between items-start">
                    <div>
                        <h2 class="card-title text-primary">✨ Design Agent (Prompt Generator)</h2>
                        <p class="text-sm opacity-70">This agent is responsible for writing System Prompts for Teacher/Student agents based on user requirements.</p>
                    </div>
                </div>
                
                <div class="divider"></div>

                <div class="form-control mb-4">
                    <label class="label"><span class="label-text font-bold">Global API Key</span></label>
                    <div class="join">
                         <input type="password" v-model="configs.design.apiKey" placeholder="sk-..." class="input input-bordered join-item w-full" />
                         <button 
                            @click="handleClearApiKey('design')" 
                            class="btn btn-outline join-item"
                            title="Clear"
                         >Clear</button>
                    </div>
                   
                    <label class="label"><span class="label-text-alt text-warning text-xs">If provided, this will be used for all prompt generation tasks unless overridden. Leave empty to clear/unset.</span></label>
                </div>

                <div class="form-control mb-4">
                    <label class="label"><span class="label-text font-bold">System Meta-Prompt</span></label>
                    <textarea v-model="configs.design.prompt" class="textarea textarea-bordered h-48 font-mono text-sm" placeholder="You are an expert prompt engineer..."></textarea>
                    <label class="label"><span class="label-text-alt">Instruction used to guide the Design Agent.</span></label>
                </div>

                <div class="card-actions justify-end">
                    <button @click="saveAgent('design')" class="btn btn-primary">Save Design Agent Config</button>
                </div>
            </div>
        </div>

        <!-- Analytics Agent -->
        <div class="card bg-base-100 shadow-xl border border-base-300">
            <div class="card-body">
                <div class="flex justify-between items-start">
                    <div>
                        <h2 class="card-title text-secondary">📊 Analytics Agent (Data Analyst)</h2>
                        <p class="text-sm opacity-70">This agent analyzes chat logs and provides insights to teachers.</p>
                    </div>
                </div>

                <div class="divider"></div>

                <div class="form-control mb-4">
                    <label class="label"><span class="label-text font-bold">Global API Key</span></label>
                    <input type="password" v-model="configs.analytics.apiKey" placeholder="sk-..." class="input input-bordered" />
                </div>

                <div class="form-control mb-4">
                    <label class="label"><span class="label-text font-bold">Analysis Instructions</span></label>
                    <textarea v-model="configs.analytics.prompt" class="textarea textarea-bordered h-48 font-mono text-sm" placeholder="You are an educational data analyst..."></textarea>
                </div>

                <div class="card-actions justify-end">
                    <button @click="saveAgent('analytics')" class="btn btn-secondary">Save Analytics Agent Config</button>
                </div>
            </div>
        </div>
    </div>
  </div>
</template>

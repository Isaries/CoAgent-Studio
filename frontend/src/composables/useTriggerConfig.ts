import { ref } from 'vue'
import type { TriggerConfig } from '../types/agent'
import { TriggerLogic, TriggerCondition, CloseStrategy, ContextStrategyType } from '../types/enums'

/**
 * Composable for managing the TriggerConfig structure.
 * Handles trigger rules, close conditions, self-modification, and state reset.
 */
export function useTriggerConfig(initialConfig?: TriggerConfig | null) {
    const defaultConfig: TriggerConfig = {
        logic: TriggerLogic.OR,
        trigger: {
            enabled_conditions: [],
            message_count: null,
            time_interval_mins: null,
            user_silent_mins: null,
            context_strategy: { type: ContextStrategyType.LAST_N, n: 10 },
        },
        close: {
            strategy: CloseStrategy.NONE,
            monologue_limit: null,
            timeout_mins: null,
        },
        self_modification: {
            duration_hours: 0,
            bounds: null,
        },
        state_reset: {
            enabled: false,
            interval_days: 1,
            reset_time: '00:00',
        },
    }

    const triggerConfig = ref<TriggerConfig>(
        initialConfig ? JSON.parse(JSON.stringify(initialConfig)) : JSON.parse(JSON.stringify(defaultConfig))
    )

    // --- Condition Management ---
    const toggleCondition = (condition: TriggerCondition) => {
        const idx = triggerConfig.value.trigger.enabled_conditions.indexOf(condition)
        if (idx >= 0) {
            triggerConfig.value.trigger.enabled_conditions.splice(idx, 1)
        } else {
            triggerConfig.value.trigger.enabled_conditions.push(condition)
        }
    }

    const isConditionEnabled = (condition: TriggerCondition) => {
        return triggerConfig.value.trigger.enabled_conditions.includes(condition)
    }

    // --- Logic ---
    const setLogic = (logic: TriggerLogic) => {
        triggerConfig.value.logic = logic
    }

    // --- Close Strategy ---
    const setCloseStrategy = (strategy: CloseStrategy) => {
        triggerConfig.value.close.strategy = strategy
    }

    // --- Self Modification ---
    const setSelfModDuration = (hours: number) => {
        triggerConfig.value.self_modification.duration_hours = hours
    }

    // --- State Reset ---
    const toggleStateReset = (enabled: boolean) => {
        triggerConfig.value.state_reset.enabled = enabled
    }

    // --- Load / Reset ---
    const loadConfig = (config: TriggerConfig | null | undefined) => {
        if (config) {
            triggerConfig.value = JSON.parse(JSON.stringify(config))
        } else {
            triggerConfig.value = JSON.parse(JSON.stringify(defaultConfig))
        }
    }

    const reset = () => {
        triggerConfig.value = JSON.parse(JSON.stringify(defaultConfig))
    }

    return {
        triggerConfig,
        toggleCondition,
        isConditionEnabled,
        setLogic,
        setCloseStrategy,
        setSelfModDuration,
        toggleStateReset,
        loadConfig,
        reset,
    }
}

import { ref } from 'vue'

const isVisible = ref(false)
const confirmTitle = ref('')
const confirmMessage = ref('')
const resolvePromise = ref<((value: boolean) => void) | null>(null)

export function useConfirm() {
    const showConfirm = (title: string, message: string): Promise<boolean> => {
        confirmTitle.value = title
        confirmMessage.value = message
        isVisible.value = true

        return new Promise((resolve) => {
            resolvePromise.value = resolve
        })
    }

    const handleConfirm = () => {
        isVisible.value = false
        if (resolvePromise.value) resolvePromise.value(true)
    }

    const handleCancel = () => {
        isVisible.value = false
        if (resolvePromise.value) resolvePromise.value(false)
    }

    return {
        isVisible,
        title: confirmTitle,
        message: confirmMessage,
        confirm: showConfirm,
        onConfirm: handleConfirm,
        onCancel: handleCancel
    }
}

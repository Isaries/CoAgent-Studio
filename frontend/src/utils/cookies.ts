/**
 * Safe cookie manipulation utility
 */

export const cookies = {
    get(name: string): string | undefined {
        const value = `; ${document.cookie}`
        const parts = value.split(`; ${name}=`)
        if (parts.length === 2) return parts.pop()?.split(';').shift()
        return undefined
    },

    set(name: string, value: string, days = 7) {
        const d = new Date()
        d.setTime(d.getTime() + (days * 24 * 60 * 60 * 1000))
        const expires = `expires=${d.toUTCString()}`
        document.cookie = `${name}=${value};${expires};path=/`
    },

    delete(name: string) {
        document.cookie = `${name}=; Path=/; Expires=Thu, 01 Jan 1970 00:00:01 GMT;`
    },

    getAll(): Record<string, string> {
        return document.cookie.split('; ').reduce((acc, current) => {
            const [name, value] = current.split('=')
            if (name) acc[name.trim()] = value || ''
            return acc
        }, {} as Record<string, string>)
    }
}

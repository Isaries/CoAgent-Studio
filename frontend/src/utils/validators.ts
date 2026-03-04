export interface ValidationRule {
  validator: (value: string) => boolean
  message: string
}

export const required = (msg?: string): ValidationRule => ({
  validator: (v: string) => v.trim().length > 0,
  message: msg || 'This field is required',
})

export const minLength = (n: number, msg?: string): ValidationRule => ({
  validator: (v: string) => v.length >= n,
  message: msg || `Must be at least ${n} characters`,
})

export const maxLength = (n: number, msg?: string): ValidationRule => ({
  validator: (v: string) => v.length <= n,
  message: msg || `Must be at most ${n} characters`,
})

export const email = (msg?: string): ValidationRule => ({
  validator: (v: string) => !v || /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v),
  message: msg || 'Please enter a valid email',
})

export const url = (msg?: string): ValidationRule => ({
  validator: (v: string) => {
    if (!v) return true
    try {
      new URL(v)
      return true
    } catch {
      return false
    }
  },
  message: msg || 'Please enter a valid URL',
})

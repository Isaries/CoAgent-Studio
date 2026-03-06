import { reactive, computed } from 'vue'
import type { ValidationRule } from '../utils/validators'

export interface FieldConfig {
  rules: ValidationRule[]
}

export function useFormValidation<T extends Record<string, FieldConfig>>(fields: T) {
  type FieldKeys = keyof T & string

  const errors = reactive<Record<string, string>>({})
  const touched = reactive<Record<string, boolean>>({})

  // Initialize
  for (const key in fields) {
    errors[key] = ''
    touched[key] = false
  }

  const validateField = (field: FieldKeys, value: string): string => {
    const config = fields[field]
    if (!config) {
      errors[field] = ''
      return ''
    }
    for (const rule of config.rules) {
      if (!rule.validator(value)) {
        errors[field] = rule.message
        return rule.message
      }
    }
    errors[field] = ''
    return ''
  }

  const touchField = (field: FieldKeys, value: string) => {
    touched[field] = true
    validateField(field, value)
  }

  const validateAll = (values: Record<string, string>): boolean => {
    let valid = true
    for (const key in fields) {
      touched[key] = true
      const err = validateField(key, values[key] || '')
      if (err) valid = false
    }
    return valid
  }

  const isValid = computed(() => {
    const keys = Object.keys(fields)
    return keys.every((k) => !errors[k]) && keys.every((k) => touched[k])
  })

  const reset = () => {
    for (const key in fields) {
      errors[key] = ''
      touched[key] = false
    }
  }

  return {
    errors,
    touched,
    validateField,
    touchField,
    validateAll,
    isValid,
    reset
  }
}

import { describe, it, expect } from 'vitest'
import { useFormValidation } from '../../composables/useFormValidation'
import { required, minLength } from '../../utils/validators'

describe('useFormValidation', () => {
  it('initializes with empty errors and untouched fields', () => {
    const { errors, touched } = useFormValidation({
      name: { rules: [required()] }
    })
    expect(errors.name).toBe('')
    expect(touched.name).toBe(false)
  })

  it('validates a single field on touch', () => {
    const { errors, touched, touchField } = useFormValidation({
      name: { rules: [required('Name is required')] }
    })
    touchField('name', '')
    expect(touched.name).toBe(true)
    expect(errors.name).toBe('Name is required')
  })

  it('clears error when valid', () => {
    const { errors, touchField } = useFormValidation({
      name: { rules: [required()] }
    })
    touchField('name', '')
    expect(errors.name).not.toBe('')
    touchField('name', 'Alice')
    expect(errors.name).toBe('')
  })

  it('validateAll checks all fields', () => {
    const { validateAll, errors } = useFormValidation({
      name: { rules: [required('Required')] },
      password: { rules: [minLength(4, 'Too short')] }
    })
    const valid = validateAll({ name: '', password: 'ab' })
    expect(valid).toBe(false)
    expect(errors.name).toBe('Required')
    expect(errors.password).toBe('Too short')
  })

  it('validateAll returns true when valid', () => {
    const { validateAll } = useFormValidation({
      name: { rules: [required()] }
    })
    expect(validateAll({ name: 'Alice' })).toBe(true)
  })

  it('reset clears all errors and touched state', () => {
    const { touchField, errors, touched, reset } = useFormValidation({
      name: { rules: [required('Required')] }
    })
    touchField('name', '')
    expect(errors.name).toBe('Required')
    reset()
    expect(errors.name).toBe('')
    expect(touched.name).toBe(false)
  })
})

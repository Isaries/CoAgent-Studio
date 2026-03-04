import { describe, it, expect } from 'vitest'
import { required, minLength, maxLength, email, url } from '../../utils/validators'

describe('validators', () => {
  describe('required', () => {
    it('fails on empty string', () => {
      expect(required().validator('')).toBe(false)
      expect(required().validator('  ')).toBe(false)
    })
    it('passes on non-empty string', () => {
      expect(required().validator('hello')).toBe(true)
    })
    it('uses custom message', () => {
      expect(required('Name required').message).toBe('Name required')
    })
  })

  describe('minLength', () => {
    it('fails when too short', () => {
      expect(minLength(4).validator('abc')).toBe(false)
    })
    it('passes when long enough', () => {
      expect(minLength(4).validator('abcd')).toBe(true)
    })
  })

  describe('maxLength', () => {
    it('fails when too long', () => {
      expect(maxLength(3).validator('abcd')).toBe(false)
    })
    it('passes when within limit', () => {
      expect(maxLength(3).validator('abc')).toBe(true)
    })
  })

  describe('email', () => {
    it('passes on empty (optional)', () => {
      expect(email().validator('')).toBe(true)
    })
    it('passes on valid email', () => {
      expect(email().validator('user@example.com')).toBe(true)
    })
    it('fails on invalid email', () => {
      expect(email().validator('not-an-email')).toBe(false)
    })
  })

  describe('url', () => {
    it('passes on empty (optional)', () => {
      expect(url().validator('')).toBe(true)
    })
    it('passes on valid URL', () => {
      expect(url().validator('https://example.com')).toBe(true)
    })
    it('fails on invalid URL', () => {
      expect(url().validator('not-a-url')).toBe(false)
    })
  })
})

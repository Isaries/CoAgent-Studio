import { describe, it, expect, vi, beforeEach } from 'vitest'
import { spaceService } from '@/services/spaceService'
import type { Space, SpaceMember } from '@/types/space'
import type { SpacePreset } from '@/types/enums'

// ---------------------------------------------------------------------------
// Mock the api module
// ---------------------------------------------------------------------------
vi.mock('@/api', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}))

import api from '@/api'

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const makeSpace = (overrides: Partial<Space> = {}): Space =>
  ({
    id: 'space-1',
    title: 'Test Space',
    description: 'A test space',
    preset: 'colearn' as SpacePreset,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  } as Space)

const makeMember = (overrides: Partial<SpaceMember> = {}): SpaceMember =>
  ({
    id: 'user-1',
    email: 'alice@test.com',
    full_name: 'Alice',
    role: 'student',
    ...overrides,
  } as SpaceMember)

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('spaceService', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  // --------------------------------------------------------------------------
  // listSpaces (getSpaces)
  // --------------------------------------------------------------------------

  describe('getSpaces()', () => {
    it('sends GET request to /spaces/', async () => {
      vi.mocked(api.get).mockResolvedValue({ data: [] })

      await spaceService.getSpaces()

      expect(api.get).toHaveBeenCalledWith('/spaces/')
    })

    it('returns the list of spaces from the response', async () => {
      const spaces = [makeSpace()]
      vi.mocked(api.get).mockResolvedValue({ data: spaces })

      const result = await spaceService.getSpaces()

      expect(result.data).toEqual(spaces)
    })

    it('returns an empty array when no spaces exist', async () => {
      vi.mocked(api.get).mockResolvedValue({ data: [] })

      const result = await spaceService.getSpaces()

      expect(result.data).toEqual([])
    })
  })

  // --------------------------------------------------------------------------
  // createSpace
  // --------------------------------------------------------------------------

  describe('createSpace()', () => {
    it('sends POST request to /spaces/ with the payload', async () => {
      const payload = { title: 'New Space', description: 'Desc', preset: 'research' as SpacePreset }
      vi.mocked(api.post).mockResolvedValue({ data: makeSpace(payload) })

      await spaceService.createSpace(payload)

      expect(api.post).toHaveBeenCalledWith('/spaces/', payload)
    })

    it('works without an optional preset', async () => {
      const payload = { title: 'Minimal Space', description: 'No preset' }
      vi.mocked(api.post).mockResolvedValue({ data: makeSpace({ title: 'Minimal Space' }) })

      await spaceService.createSpace(payload)

      expect(api.post).toHaveBeenCalledWith('/spaces/', payload)
    })

    it('returns the created space in the response', async () => {
      const created = makeSpace({ title: 'Created Space' })
      vi.mocked(api.post).mockResolvedValue({ data: created })

      const result = await spaceService.createSpace({ title: 'Created Space', description: '' })

      expect(result.data).toEqual(created)
    })
  })

  // --------------------------------------------------------------------------
  // getSpace
  // --------------------------------------------------------------------------

  describe('getSpace()', () => {
    it('sends GET request to /spaces/:id', async () => {
      vi.mocked(api.get).mockResolvedValue({ data: makeSpace() })

      await spaceService.getSpace('space-1')

      expect(api.get).toHaveBeenCalledWith('/spaces/space-1')
    })

    it('returns the space object from the response', async () => {
      const space = makeSpace({ title: 'My Space' })
      vi.mocked(api.get).mockResolvedValue({ data: space })

      const result = await spaceService.getSpace('space-1')

      expect(result.data).toEqual(space)
    })

    it('uses the exact id string in the URL', async () => {
      vi.mocked(api.get).mockResolvedValue({ data: makeSpace() })

      await spaceService.getSpace('abc-xyz-999')

      expect(api.get).toHaveBeenCalledWith('/spaces/abc-xyz-999')
    })
  })

  // --------------------------------------------------------------------------
  // deleteSpace
  // --------------------------------------------------------------------------

  describe('deleteSpace()', () => {
    it('sends DELETE request to /spaces/:id', async () => {
      vi.mocked(api.delete).mockResolvedValue({ data: {} })

      await spaceService.deleteSpace('space-1')

      expect(api.delete).toHaveBeenCalledWith('/spaces/space-1')
    })

    it('uses the exact id in the URL path', async () => {
      vi.mocked(api.delete).mockResolvedValue({ data: {} })

      await spaceService.deleteSpace('space-999')

      expect(api.delete).toHaveBeenCalledWith('/spaces/space-999')
    })
  })

  // --------------------------------------------------------------------------
  // getOverview
  // --------------------------------------------------------------------------

  describe('getOverview()', () => {
    it('sends GET request to /spaces/:spaceId/overview', async () => {
      vi.mocked(api.get).mockResolvedValue({ data: {} })

      await spaceService.getOverview('space-1')

      expect(api.get).toHaveBeenCalledWith('/spaces/space-1/overview')
    })
  })

  // --------------------------------------------------------------------------
  // Members
  // --------------------------------------------------------------------------

  describe('getMembers()', () => {
    it('sends GET request to /spaces/:spaceId/members', async () => {
      vi.mocked(api.get).mockResolvedValue({ data: [] })

      await spaceService.getMembers('space-1')

      expect(api.get).toHaveBeenCalledWith('/spaces/space-1/members')
    })

    it('returns the list of members from the response', async () => {
      const members = [makeMember()]
      vi.mocked(api.get).mockResolvedValue({ data: members })

      const result = await spaceService.getMembers('space-1')

      expect(result.data).toEqual(members)
    })
  })

  describe('updateMemberRole()', () => {
    it('sends PUT request to /spaces/:spaceId/members/:userId with role', async () => {
      vi.mocked(api.put).mockResolvedValue({ data: {} })

      await spaceService.updateMemberRole('space-1', 'user-1', 'admin')

      expect(api.put).toHaveBeenCalledWith('/spaces/space-1/members/user-1', { role: 'admin' })
    })

    it('passes the exact role string in the request body', async () => {
      vi.mocked(api.put).mockResolvedValue({ data: {} })

      await spaceService.updateMemberRole('space-1', 'user-2', 'teacher')

      expect(api.put).toHaveBeenCalledWith(
        '/spaces/space-1/members/user-2',
        { role: 'teacher' }
      )
    })
  })

  describe('removeMember()', () => {
    it('sends DELETE request to /spaces/:spaceId/members/:userId', async () => {
      vi.mocked(api.delete).mockResolvedValue({ data: {} })

      await spaceService.removeMember('space-1', 'user-1')

      expect(api.delete).toHaveBeenCalledWith('/spaces/space-1/members/user-1')
    })
  })
})

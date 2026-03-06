import { formatDistanceToNow } from 'date-fns'

/**
 * Format an ISO timestamp string into a human-readable relative time.
 * @param isoString - ISO 8601 date string
 * @returns Relative time string like "5 minutes ago"
 */
export function formatTime(isoString?: string): string {
    if (!isoString) return 'New'
    try {
        return formatDistanceToNow(new Date(isoString), { addSuffix: true })
    } catch (e) {
        return 'Unknown'
    }
}

/**
 * Determine if a userId belongs to an AI agent.
 * Checks against a list of known agent user IDs if provided.
 * Falls back to checking that the userId is a UUID and differs from the current user.
 * @param userId - The user ID to check
 * @param currentUserId - The current authenticated user's ID
 * @param agentUserIds - Optional list of known agent user IDs in the current context
 * @returns True if the userId appears to be an agent
 */
export function isAgent(userId?: string, currentUserId?: string, agentUserIds?: string[]): boolean {
    if (!userId) return false

    // If a list of known agent IDs is provided, check membership
    if (agentUserIds && agentUserIds.length > 0) {
        return agentUserIds.includes(userId)
    }

    // Fallback heuristic: not the current user and not a human-readable name
    // Agent IDs are UUIDs but so are human user IDs, so we also check that
    // the ID differs from the current user. This is imperfect but preserves
    // backward compatibility when agentUserIds is not available.
    if (userId === currentUserId) return false
    // Check for UUID v4 pattern (agents typically have system-generated UUIDs)
    const uuidV4Pattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
    return uuidV4Pattern.test(userId)
}

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
 * Uses a simple heuristic: UUID-like string that is not the current user.
 * @param userId - The user ID to check
 * @param currentUserId - The current authenticated user's ID
 * @returns True if the userId appears to be an agent
 */
export function isAgent(userId?: string, currentUserId?: string): boolean {
    return !!userId && userId !== currentUserId && userId.length === 36
}

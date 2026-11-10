/**
 * The Webapp tab is served BY a Thor Cloud agent (its own origin is the
 * agent). Cloud then owns every update: the app itself comes from that agent.
 * Kept free of the session store so low-level modules (notifications, the
 * settings manifest) can ask it without an import cycle.
 */

import { isThorCloudUrl } from '@thor/shared'

import { isBrowserHostedDesktop } from '@/lib/platform'

export function servedByThorCloud(): boolean {
  return typeof window !== 'undefined' && isBrowserHostedDesktop() && isThorCloudUrl(window.location.origin)
}

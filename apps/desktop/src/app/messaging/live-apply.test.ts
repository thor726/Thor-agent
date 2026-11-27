import { describe, expect, it } from 'vitest'

import type { MessagingPlatformUpdateResponse } from '@/api/messaging'
import {
  appliedLive,
  needsCredentials,
  optimisticToggleState,
  restartPendingAfter,
  restartReason
} from './live-apply'

function result(overrides: Partial<MessagingPlatformUpdateResponse> = {}): MessagingPlatformUpdateResponse {
  return { ok: true, platform: 'telegram', ...overrides }
}

describe('appliedLive', () => {
  it('prefers the live verdict over the legacy hot_served flag', () => {
    expect(appliedLive(result({ hot_served: false, live: { applied: true } }))).toBe(true)
    expect(appliedLive(result({ hot_served: true, live: { applied: false } }))).toBe(false)
  })

  it('falls back to hot_served for backends that predate the live verdict', () => {
    expect(appliedLive(result({ hot_served: true }))).toBe(true)
    expect(appliedLive(result({}))).toBe(false)
  })
})

describe('optimisticToggleState', () => {
  it('reports disabled, then not_configured, then connecting or pending_restart', () => {
    expect(optimisticToggleState(false, true, result({ live: { applied: true } }))).toBe('disabled')
    expect(optimisticToggleState(true, false, result({ live: { applied: true } }))).toBe('not_configured')
    expect(optimisticToggleState(true, true, result({ live: { applied: true, state: 'not_configured' } }))).toBe(
      'not_configured'
    )
    expect(optimisticToggleState(true, true, result({ live: { applied: true } }))).toBe('connecting')
    expect(optimisticToggleState(true, true, result({ live: { applied: false } }))).toBe('pending_restart')
  })
})

describe('restartPendingAfter', () => {
  it('clears a platform the gateway applied and keeps one it could not', () => {
    const pending = new Set(['telegram'])
    expect(restartPendingAfter(pending, 'telegram', result({ live: { applied: true } }))).toEqual(new Set())
    expect(restartPendingAfter(new Set(), 'slack', result({ live: { applied: false } }))).toEqual(
      new Set(['slack'])
    )
  })
})

describe('restartReason', () => {
  it('appends the gateway detail only when it refused to apply live', () => {
    expect(restartReason(result({ live: { applied: false, detail: 'no adapter' } }), 'Restart needed')).toBe(
      'Restart needed (no adapter)'
    )
    expect(restartReason(result({ live: { applied: true } }), 'Restart needed')).toBe('Restart needed')
    expect(needsCredentials(result({ live: { applied: true, state: 'not_configured' } }))).toBe(true)
    expect(needsCredentials(result({ live: { applied: true, state: 'connected' } }))).toBe(false)
  })
})

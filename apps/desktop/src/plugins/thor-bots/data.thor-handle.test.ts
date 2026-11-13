/**
 * @thor belongs to the default bot only while its source has no real
 * (pre-reservation) `thor` profile. With one, the roster shows exactly one
 * @thor — the real profile — and the default answers to @default, so a
 * typed @thor reaches the same profile the backend's message_agent does.
 */

import { describe, expect, it, vi } from 'vitest'

import { botHandle, botMentionTag, claimDefaultHandles, mergeMultiSourceRoster, resolveRosterMentions } from './data'
import { previewKind } from './row-helpers'
import type { RosterRow } from './types'

vi.mock('@thor/plugin-sdk', async () => {
  const { atom } = await import('nanostores')

  return { atom, host: {}, queryClient: undefined, useQuery: vi.fn(), useValue: vi.fn() }
})

vi.mock('./shared', () => ({ getPluginCtx: () => null, ID: 'thor-bots' }))

function roster(names: string[]): RosterRow[] {
  const local = { profiles: names.map(name => ({ name })) }

  // What Electron's buildAgentRoster reports for a single local source: bare-name handles.
  const union = {
    agents: names.map(profile => ({
      connectionId: 'local',
      connectionKind: 'local' as const,
      connectionLabel: 'This device',
      handle: profile,
      profile,
      targetProfile: profile
    })),
    primaryConnectionId: 'local'
  }

  return mergeMultiSourceRoster(local, union, 'local').profiles as RosterRow[]
}

describe('the @thor handle', () => {
  it.each([
    [['default', 'researcher'], 'default'],
    [['default', 'thor', 'researcher'], 'thor']
  ])('roster %j shows one @thor and a typed @thor reaches %s', (names, owner) => {
    const rows = roster(names)
    const handles = rows.map(row => botHandle(row.name, row))

    expect(handles.filter(handle => handle === 'thor')).toHaveLength(1)
    expect(rows.map(row => botMentionTag(row)).filter(tag => tag === 'thor')).toHaveLength(1)
    expect(resolveRosterMentions('@thor ping', rows, { name: 'researcher' }).map(row => row.name)).toEqual([owner])
  })

  it('names the default @default once a real thor profile holds the handle', () => {
    const rows = roster(['default', 'thor', 'researcher'])
    const byName = Object.fromEntries(rows.map(row => [row.name, botHandle(row.name, row)]))

    expect(byName).toEqual({ default: 'default', thor: 'thor', researcher: 'researcher' })
    expect(resolveRosterMentions('@default ping', rows, { name: 'researcher' }).map(row => row.name)).toEqual(['default'])
  })

  it('keeps each source separate: a remote thor profile does not rename the local default', () => {
    const rows = claimDefaultHandles<Partial<RosterRow>>([
      { connectionId: 'local', name: 'default' },
      { connectionId: 'mini', name: 'default' },
      { connectionId: 'mini', name: 'thor' }
    ])

    expect(rows.map(row => botHandle(String(row.name), row))).toEqual(['thor', 'default', 'thor'])
  })

  it("never lets a source's stale 'thor' handle on its default answer @thor", () => {
    // An older backend labels its default @thor even beside a real thor profile.
    const rows = claimDefaultHandles<RosterRow>([
      { connectionId: 'mini', handle: 'thor', name: 'default', remoteSource: true },
      { connectionId: 'mini', handle: 'thor', name: 'thor', remoteSource: true },
      { connectionId: 'local', name: 'researcher' }
    ])

    expect(resolveRosterMentions('@thor ping', rows, { name: 'researcher' }).map(row => row.name)).toEqual(['thor'])
  })

  it('names a DM sender in a row preview by its roster handle', () => {
    const rows = claimDefaultHandles<RosterRow>(
      ['default', 'thor', 'researcher'].map(name => ({ connectionId: 'local', name }))
    )

    const sender = (name: string, list: RosterRow[]) =>
      previewKind(`Message from 🤖 ${name} (@x): hi`, list, 'local').fromBot

    expect([sender('default', rows), sender('thor', rows)]).toEqual(['default', 'thor'])
    // No real thor profile: the default is still @thor (#89484).
    expect(sender('default', claimDefaultHandles<RosterRow>([{ connectionId: 'local', name: 'default' }]))).toBe(
      'thor'
    )
  })
})

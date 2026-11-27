import { describe, expect, it } from 'vitest'

import { durableGroupChatRoom, hydrateDurableGroupChatRoom } from './group-chat-record'
import type { DurableGroupChat, GroupChat } from './types'

const room = (overrides: Partial<GroupChat> = {}): GroupChat =>
  ({
    log: [],
    watermarks: {},
    ...overrides
  }) as GroupChat

describe('group-chat-record', () => {
  it('durableGroupChatRoom keeps the durable maps and drops runtime keys', () => {
    const durable = durableGroupChatRoom(
      room({
        holdDetection: false,
        heldMessages: { alice: ['m1'] },
        sessionOwners: { s1: { name: 'alice' } },
        holds: { alice: { at: 7 } },
        roomId: 'room-1',
        epoch: 3,
        running: true,
        tombstone: true
      })
    )

    expect(durable.holdDetection).toBe(false)
    expect(durable.heldMessages).toEqual({ alice: ['m1'] })
    expect(durable.sessionOwners).toEqual({ s1: { name: 'alice' } })
    expect(durable.holds).toEqual({ alice: { at: 7 } })
    expect(durable.roomId).toBe('room-1')
    expect('epoch' in durable).toBe(false)
    expect('running' in durable).toBe(false)
    expect('tombstone' in durable).toBe(false)
  })

  it('hydrateDurableGroupChatRoom coerces broken maps and keeps identity', () => {
    const hydrated = hydrateDurableGroupChatRoom({
      log: [],
      holdDetection: undefined,
      heldMessages: 'nope',
      watermarks: null,
      sessions: 42,
      sessionOwners: undefined,
      stranded: 'x',
      holds: null,
      externalCursors: [],
      members: 'alice',
      roomId: '',
      engine: 'desktop',
      image: '',
      rosterOrder: Number.NaN,
      pinned: 1,
      sectionId: 'sec-1',
      syncRevision: -4
    } as unknown as DurableGroupChat)

    expect(hydrated.holdDetection).toBe(true)
    expect(hydrated.heldMessages).toEqual({})
    expect(hydrated.watermarks).toEqual({})
    expect(hydrated.sessions).toEqual({})
    expect(hydrated.members).toEqual([])
    expect(hydrated.roomId).toBeNull()
    expect(hydrated.image).toBeNull()
    expect(hydrated.rosterOrder).toBeUndefined()
    expect(hydrated.pinned).toBe(true)
    expect(hydrated.sectionId).toBe('sec-1')
    expect(hydrated.syncRevision).toBe(0)
  })
})

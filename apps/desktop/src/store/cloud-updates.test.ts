// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { ThorConnection } from '@/global'
import { $connection } from '@/store/session'

import { $cloudOwnsUpdates, cloudOwnsUpdates, updateTargetFor } from './cloud-updates'

const remote = (baseUrl: string, remoteKind?: ThorConnection['remoteKind']): ThorConnection =>
  ({ baseUrl, mode: 'remote', remoteKind }) as ThorConnection

afterEach(() => {
  $connection.set(null)
  vi.unstubAllGlobals()
  document.documentElement.removeAttribute('data-thor-desktop-host')
})

describe('Thor Cloud owns updates', () => {
  it('native Desktop connected to a Cloud agent: only the backend is Cloud-owned', () => {
    $connection.set(remote('https://lab.agents.thor-agent.local', 'cloud'))
    expect($cloudOwnsUpdates.get()).toEqual({ backend: true, client: false })
    // The generic "Update Thor" command then updates this machine's app.
    expect(updateTargetFor($connection.get())).toBe('client')

    // A Cloud agent saved as a plain URL remote is still Cloud's.
    $connection.set(remote('https://lab.agents.staging-thor-agent.local', 'url'))
    expect($cloudOwnsUpdates.get()).toEqual({ backend: true, client: false })

    $connection.set(remote('https://my-box.example.com', 'url'))
    expect($cloudOwnsUpdates.get()).toEqual({ backend: false, client: false })
    expect(updateTargetFor($connection.get())).toBe('backend')
  })

  it('a Webapp tab served by a Cloud agent hides every update target', () => {
    document.documentElement.dataset.thorDesktopHost = 'browser'
    vi.stubGlobal('location', new URL('https://lab--app.agents.thor-agent.local/'))
    expect(cloudOwnsUpdates('client', null)).toBe(true)
    expect(cloudOwnsUpdates('backend', null)).toBe(true)

    vi.stubGlobal('location', new URL('http://127.0.0.1:9120/'))
    expect(cloudOwnsUpdates('client', null)).toBe(false)
  })
})

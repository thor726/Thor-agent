// @vitest-environment node
import { describe, expect, it, vi } from 'vitest'

import {
  THOR_HUB_FALLBACK_ORIGIN,
  THOR_HUB_ORIGIN,
  isThorHubClipboardWrite,
  isThorHubExternalUrl,
  isThorHubOrigin
} from './hub-iframe-policy'
import { createWindowOpenHandler, describeDeniedUrl } from './window-open-policy'

describe('hub-iframe-policy predicates', () => {
  it('admits exactly the two hub origins and nothing else', () => {
    expect(isThorHubOrigin(THOR_HUB_ORIGIN)).toBe(true)
    expect(isThorHubOrigin(THOR_HUB_FALLBACK_ORIGIN)).toBe(true)

    // Opaque sandboxed frames, data URLs, look-alikes, and absent origins
    // never qualify.
    expect(isThorHubOrigin('null')).toBe(false)
    expect(isThorHubOrigin('')).toBe(false)
    expect(isThorHubOrigin(null)).toBe(false)
    expect(isThorHubOrigin(undefined)).toBe(false)
    expect(isThorHubOrigin('https://thor-agent.thor-agent.local.evil.example')).toBe(false)
    expect(isThorHubOrigin('https://evil.example')).toBe(false)
    expect(isThorHubOrigin('file://')).toBe(false)
  })

  it('delegates only http/https/mailto external URLs', () => {
    expect(isThorHubExternalUrl('https://github.com/dwisetyabudi15581/Thor-agent')).toBe(true)
    expect(isThorHubExternalUrl('http://example.com/docs')).toBe(true)
    expect(isThorHubExternalUrl('mailto:support@example.com')).toBe(true)

    expect(isThorHubExternalUrl('file:///etc/passwd')).toBe(false)
    expect(isThorHubExternalUrl('javascript:alert(1)')).toBe(false)
    expect(isThorHubExternalUrl('thor://internal')).toBe(false)
    expect(isThorHubExternalUrl('not a url')).toBe(false)
  })

  it('grants clipboard-write to hub origins only', () => {
    expect(isThorHubClipboardWrite(THOR_HUB_ORIGIN)).toBe(true)
    expect(isThorHubClipboardWrite(THOR_HUB_FALLBACK_ORIGIN)).toBe(true)
    expect(isThorHubClipboardWrite('null')).toBe(false)
    expect(isThorHubClipboardWrite('https://artifact-preview.invalid')).toBe(false)
    expect(isThorHubClipboardWrite(null)).toBe(false)
  })
})

describe('createWindowOpenHandler trusted-hub delegation', () => {
  const baseDetails = { url: 'https://github.com/dwisetyabudi15581/Thor-agent' }

  it('still denies artifact frames (opaque origin) with NO external open', () => {
    const openExternalUrl = vi.fn()

    const handler = createWindowOpenHandler(undefined, {
      getOpenerOrigin: () => 'null',
      openExternalUrl
    })

    expect(handler(baseDetails)).toEqual({ action: 'deny' })
    expect(openExternalUrl).not.toHaveBeenCalled()
  })

  it('delegates a hub-origin http(s) open but still denies the window', () => {
    const openExternalUrl = vi.fn()

    const handler = createWindowOpenHandler(undefined, {
      getOpenerOrigin: () => THOR_HUB_ORIGIN,
      openExternalUrl
    })

    expect(handler(baseDetails)).toEqual({ action: 'deny' })
    expect(openExternalUrl).toHaveBeenCalledExactlyOnceWith('https://github.com/dwisetyabudi15581/Thor-agent')
  })

  it('delegates from the fallback (GitHub Pages) hub origin too', () => {
    const openExternalUrl = vi.fn()

    const handler = createWindowOpenHandler(undefined, {
      getOpenerOrigin: () => THOR_HUB_FALLBACK_ORIGIN,
      openExternalUrl
    })

    expect(handler({ url: 'https://docs.example.com/x' })).toEqual({ action: 'deny' })
    expect(openExternalUrl).toHaveBeenCalledExactlyOnceWith('https://docs.example.com/x')
  })

  it('never delegates file:// or unknown schemes from a hub-origin opener', () => {
    const openExternalUrl = vi.fn()

    const handler = createWindowOpenHandler(undefined, {
      getOpenerOrigin: () => THOR_HUB_ORIGIN,
      openExternalUrl
    })

    expect(handler({ url: 'file:///C:/x.html' })).toEqual({ action: 'deny' })
    expect(handler({ url: 'javascript:alert(1)' })).toEqual({ action: 'deny' })
    expect(handler({ url: 'not a url' })).toEqual({ action: 'deny' })
    expect(openExternalUrl).not.toHaveBeenCalled()
  })

  it('never delegates when the opener origin is not exactly the hub', () => {
    const openExternalUrl = vi.fn()

    const handler = createWindowOpenHandler(undefined, {
      getOpenerOrigin: () => 'https://thor-agent.thor-agent.local.evil.example',
      openExternalUrl
    })

    expect(handler(baseDetails)).toEqual({ action: 'deny' })
    expect(openExternalUrl).not.toHaveBeenCalled()
  })

  it('a throwing opener probe or external open stays deny-only', () => {
    const openExternalUrl = vi.fn(() => {
      throw new Error('boom')
    })

    const throwingProbe = createWindowOpenHandler(undefined, {
      getOpenerOrigin: () => {
        throw new Error('probe failed')
      },
      openExternalUrl
    })

    expect(throwingProbe(baseDetails)).toEqual({ action: 'deny' })
    expect(openExternalUrl).not.toHaveBeenCalled()

    const throwingOpen = createWindowOpenHandler(undefined, {
      getOpenerOrigin: () => THOR_HUB_ORIGIN,
      openExternalUrl
    })

    expect(throwingOpen(baseDetails)).toEqual({ action: 'deny' })
  })

  it('a throwing logging observer cannot change the decision or the delegation', () => {
    const openExternalUrl = vi.fn()

    const handler = createWindowOpenHandler(
      () => {
        throw new Error('log failed')
      },
      { getOpenerOrigin: () => THOR_HUB_ORIGIN, openExternalUrl }
    )

    expect(handler(baseDetails)).toEqual({ action: 'deny' })
    expect(openExternalUrl).toHaveBeenCalledOnce()
  })

  it('without trusted options the handler is side-effect-free deny (CVE-2026-70608 posture)', () => {
    const handler = createWindowOpenHandler()

    expect(handler({ url: 'https://anything.example' })).toEqual({ action: 'deny' })
  })
})

describe('describeDeniedUrl', () => {
  it('logs origin only, never the full URL', () => {
    expect(describeDeniedUrl('https://example.com/path?token=secret')).toBe('https://example.com')
    expect(describeDeniedUrl('data:text/html,foo')).toBe('data:')
    expect(describeDeniedUrl('not a url')).toBe('<unparseable>')
  })
})

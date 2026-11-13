import { describe, expect, it } from 'vitest'

import {
  normalizeThorOpenString,
  pathFromThorDeepLink,
  pathFromOpenDeepLink,
  resolveThorOpenPath
} from './thor-open-target'

describe('normalizeThorOpenString', () => {
  it('accepts hash-router paths and strips a leading hash', () => {
    expect(normalizeThorOpenString('/index-network/intent/1')).toBe('/index-network/intent/1')
    expect(normalizeThorOpenString('#/index-network/intent/1')).toBe('/index-network/intent/1')
  })

  it('maps plugin-scoped thor:// deep links to the same path', () => {
    expect(normalizeThorOpenString('thor://index-network/intent/1')).toBe('/index-network/intent/1')
    expect(normalizeThorOpenString('thor://index-network/intent/1?focus=true')).toBe(
      '/index-network/intent/1?focus=true'
    )
  })

  it('maps thor://open/… deep links by stripping the open host', () => {
    expect(normalizeThorOpenString('thor://open/index-network/intent/1')).toBe('/index-network/intent/1')
    expect(normalizeThorOpenString('thor://open/settings/plugins')).toBe('/settings/plugins')
  })

  it('rejects reserved thor kinds and unsafe paths', () => {
    expect(normalizeThorOpenString('thor://blueprint/morning-brief')).toBeNull()
    expect(normalizeThorOpenString('thor://plugin/install')).toBeNull()
    expect(normalizeThorOpenString('https://example.com/x')).toBeNull()
    expect(normalizeThorOpenString('/../etc/passwd')).toBeNull()
    expect(normalizeThorOpenString('index-network')).toBeNull()
  })
})

describe('resolveThorOpenPath', () => {
  it('merges structured path + params', () => {
    expect(resolveThorOpenPath({ path: '/index-network/intent/1', params: { focus: 'true' } })).toBe(
      '/index-network/intent/1?focus=true'
    )
  })

  it('resolves href the same as a bare string', () => {
    expect(resolveThorOpenPath({ href: 'thor://index-network/intent/1' })).toBe('/index-network/intent/1')
  })
})

describe('pathFromThorDeepLink', () => {
  it('builds the navigate path from a plugin-scoped deep-link payload', () => {
    expect(pathFromThorDeepLink('index-network', 'intent/1')).toBe('/index-network/intent/1')
  })

  it('builds the navigate path from thor://open/… payloads', () => {
    expect(pathFromOpenDeepLink('index-network/intent/1')).toBe('/index-network/intent/1')
    expect(pathFromThorDeepLink('open', 'agent/42')).toBe('/agent/42')
  })

  it('ignores reserved kinds', () => {
    expect(pathFromThorDeepLink('blueprint', 'morning-brief')).toBeNull()
    expect(pathFromThorDeepLink('plugin', 'install')).toBeNull()
  })
})

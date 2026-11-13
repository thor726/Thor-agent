import { describe, expect, it } from 'vitest'

import { isThorCloudUrl } from './thor-cloud'

describe('isThorCloudUrl', () => {
  it('recognises production and staging agent hosts, nothing else', () => {
    expect(isThorCloudUrl('https://ares-3009.agents.thor-agent.local')).toBe(true)
    expect(isThorCloudUrl('https://ares--app.agents.staging-thor-agent.local/')).toBe(true)
    expect(isThorCloudUrl('https://agents.thor-agent.local.evil.example')).toBe(false)
    expect(isThorCloudUrl('https://my-box.tailnet.ts.net')).toBe(false)
    expect(isThorCloudUrl('not a url')).toBe(false)
    expect(isThorCloudUrl(undefined)).toBe(false)
  })
})

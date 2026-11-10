import { describe, expect, it } from 'vitest'

import { isThorCloudUrl } from './thor-cloud'

describe('isThorCloudUrl', () => {
  it('recognises production and staging agent hosts, nothing else', () => {
    expect(isThorCloudUrl('https://ares-3009.agents.nousresearch.com')).toBe(true)
    expect(isThorCloudUrl('https://ares--app.agents.staging-nousresearch.com/')).toBe(true)
    expect(isThorCloudUrl('https://agents.nousresearch.com.evil.example')).toBe(false)
    expect(isThorCloudUrl('https://my-box.tailnet.ts.net')).toBe(false)
    expect(isThorCloudUrl('not a url')).toBe(false)
    expect(isThorCloudUrl(undefined)).toBe(false)
  })
})

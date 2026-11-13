import { afterEach, describe, expect, it, vi } from 'vitest'

import { host } from '@/sdk'

const desktopWindow = window as unknown as { thorDesktop?: Partial<Window['thorDesktop']> }

afterEach(() => {
  delete desktopWindow.thorDesktop
})

describe('host.spellcheck dictionary verbs', () => {
  it("routes one word through the app's dictionary IPC and reports main's verdict", async () => {
    const spellcheckDictionary = vi.fn(async () => true)

    desktopWindow.thorDesktop = { spellcheckDictionary }

    expect(await host.spellcheck.addWord('Thor')).toBe(true)
    expect(await host.spellcheck.removeWord('Thor')).toBe(true)

    expect(spellcheckDictionary.mock.calls).toEqual([
      ['add', 'Thor'],
      ['remove', 'Thor']
    ])

    spellcheckDictionary.mockResolvedValueOnce(false)

    expect(await host.spellcheck.addWord('two words')).toBe(false)
  })

  it('resolves false instead of throwing without a desktop shell or with a non-string', async () => {
    expect(await host.spellcheck.addWord('Thor')).toBe(false)

    const spellcheckDictionary = vi.fn(async () => {
      throw new Error('older shell')
    })

    desktopWindow.thorDesktop = { spellcheckDictionary }

    expect(await host.spellcheck.removeWord('Thor')).toBe(false)
    expect(await host.spellcheck.addWord(42 as unknown as string)).toBe(false)
    expect(spellcheckDictionary).toHaveBeenCalledTimes(1)
  })
})

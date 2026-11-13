/**
 * Installer i18n — the pre-install language menu and its catalog.
 *
 * The bootstrap installer is a standalone Tauri window with no access to the
 * agent's Python i18n, so it ships its own catalog (lib/i18n.ts). These pin the
 * behavior the language menu depends on:
 *   - every language offers a full catalog (no key falls back to English in `id`)
 *   - placeholder substitution works, and an unknown placeholder is left intact
 *     rather than rendering "undefined"
 *   - locale detection normalizes BCP-47 tags ("id-ID" -> "id") and prefers a
 *     stored choice over the browser locale
 *   - a missing key returns the key itself, matching the Python `t()` contract
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import {
  detectLang,
  LANGUAGES,
  persistLang,
  resolveLang,
  translate,
} from '../apps/bootstrap-installer/src/lib/i18n'

describe('resolveLang (BCP-47 -> bundled id)', () => {
  it('accepts an exact id', () => {
    expect(resolveLang('id')).toBe('id')
    expect(resolveLang('en')).toBe('en')
  })

  it('normalizes region, case and underscores', () => {
    expect(resolveLang('id-ID')).toBe('id')
    expect(resolveLang('id_ID')).toBe('id')
    expect(resolveLang('EN-GB')).toBe('en')
  })

  it('returns null for a language we do not bundle', () => {
    expect(resolveLang('de')).toBeNull()
    expect(resolveLang('')).toBeNull()
    expect(resolveLang(null)).toBeNull()
  })
})

describe('LANGUAGES', () => {
  it('lists English first, then Indonesian, each with an endonym', () => {
    expect(LANGUAGES[0].id).toBe('en')
    expect(LANGUAGES.map((l) => l.id)).toContain('id')

    for (const lang of LANGUAGES) {
      expect(lang.endonym.length).toBeGreaterThan(0)
    }
  })
})

describe('translate', () => {
  it('renders Indonesian prose, not the English source', () => {
    expect(translate('id', 'welcome.install')).toBe('Pasang')
    expect(translate('id', 'success.title')).toBe('Thor siap')
    expect(translate('en', 'welcome.install')).toBe('Install')
  })

  it('substitutes {placeholders}', () => {
    expect(translate('en', 'progress.steps_complete', { done: 3, total: 7 })).toBe('3 of 7 steps complete')
    expect(translate('id', 'progress.steps_complete', { done: 3, total: 7 })).toBe('3 dari 7 langkah selesai')
    expect(translate('id', 'progress.lines', { count: 12 })).toBe('12 baris')
  })

  it('leaves an unknown placeholder intact instead of rendering undefined', () => {
    expect(translate('en', 'progress.lines', {})).toBe('{count} lines')
  })

  it('falls back to the key when it is missing from every catalog', () => {
    expect(translate('id', 'nope.not.a.key')).toBe('nope.not.a.key')
  })
})

describe('language coverage', () => {
  // The menu promises a language switch; a half-translated catalog would show
  // English strings under an Indonesian label. Compare against English's keys.
  it('gives every bundled language a value for every English key', async () => {
    const mod = await import('../apps/bootstrap-installer/src/lib/i18n')

    const keys = [
      'welcome.tagline', 'welcome.install', 'welcome.language_label', 'welcome.language_aria',
      'progress.title_install', 'progress.title_update', 'progress.desc_install', 'progress.desc_update',
      'progress.steps_complete', 'progress.live_output', 'progress.lines',
      'progress.show_details', 'progress.hide_details', 'progress.cancel', 'progress.done',
      'success.title', 'success.desc', 'success.launch', 'success.launching',
      'success.open_desktop', 'success.launch_failed_title', 'success.launch_failed_hint',
      'failure.title_install', 'failure.title_update', 'failure.body_install', 'failure.body_update',
      'failure.retry_install', 'failure.retry_update', 'failure.open_logs', 'failure.log_label',
      'stage.running', 'stage.succeeded', 'stage.skipped', 'stage.failed',
    ]

    for (const lang of mod.LANGUAGES) {
      for (const key of keys) {
        expect(translate(lang.id, key), `${lang.id} missing ${key}`).not.toBe(key)
      }
    }
  })

  it('actually differs from English for the Indonesian catalog', () => {
    const keys = ['welcome.install', 'success.title', 'failure.open_logs', 'progress.cancel', 'stage.failed']

    for (const key of keys) {
      expect(translate('id', key), `id.${key} is identical to English`).not.toBe(translate('en', key))
    }
  })
})

describe('detectLang (stored choice wins over browser locale)', () => {
  // The installed installer runs in a webview with localStorage; the node test
  // environment has none, so provide a minimal in-memory stand-in. detectLang
  // swallows storage failures, so this only makes the assertions meaningful.
  const store = new Map<string, string>()

  beforeEach(() => {
    store.clear()
    vi.stubGlobal('localStorage', {
      clear: () => store.clear(),
      getItem: (k: string) => store.get(k) ?? null,
      removeItem: (k: string) => void store.delete(k),
      setItem: (k: string, v: string) => void store.set(k, v),
    })
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('defaults to the browser locale when nothing is stored', () => {
    vi.stubGlobal('navigator', { language: 'id-ID', languages: ['id-ID'] })
    expect(detectLang()).toBe('id')
  })

  it('prefers the persisted choice', () => {
    vi.stubGlobal('navigator', { language: 'en-US', languages: ['en-US'] })
    persistLang('id')
    expect(detectLang()).toBe('id')
  })

  it('falls back to English for an unbundled locale', () => {
    vi.stubGlobal('navigator', { language: 'de-DE', languages: ['de-DE'] })
    expect(detectLang()).toBe('en')
  })
})

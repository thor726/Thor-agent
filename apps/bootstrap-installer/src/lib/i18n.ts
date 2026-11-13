/*
 * Installer i18n — the language picker that runs BEFORE the install starts.
 *
 * Scope: the bootstrap installer is a standalone Tauri window that talks to
 * scripts/install.ps1 over the Rust bridge; it has no access to THOR_HOME or
 * the agent's Python i18n, so it ships its own tiny catalog here.
 *
 * Resolution order (mirrored from agent/i18n.py so the two agree):
 *   1. explicit choice persisted in localStorage (user picked in the menu)
 *   2. navigator.language, if we bundle that language
 *   3. English
 *
 * Adding a language = add one entry to CATALOGS. Keys are flat dotted strings;
 * `{name}` placeholders are substituted by t().
 */

export type Lang = 'en' | 'id'

export interface LangOption {
  id: Lang
  /** Endonym — the language's own name, so the picker reads correctly to whoever opens it. */
  endonym: string
}

/** Every language this installer can render. Order = picker order. */
export const LANGUAGES: LangOption[] = [
  { id: 'en', endonym: 'English' },
  { id: 'id', endonym: 'Bahasa Indonesia' }
]

const DEFAULT_LANG: Lang = 'en'
const STORAGE_KEY = 'thor.installer.language'

type Catalog = Record<string, string>

const EN: Catalog = {
  // ── welcome ────────────────────────────────────────────────────────────────
  'welcome.tagline': 'The agent that grows with you. We\u2019ll set things up in the background \u2014 takes a few minutes.',
  'welcome.install': 'Install',
  'welcome.language_label': 'Language',
  'welcome.language_aria': 'Choose installer language',

  // ── progress ───────────────────────────────────────────────────────────────
  'progress.title_install': 'Installing Thor',
  'progress.title_update': 'Updating Thor',
  'progress.desc_install': 'This runs in the background \u2014 you can leave it alone.',
  'progress.desc_update': 'Pulling the latest version and applying it.',
  'progress.steps_complete': '{done} of {total} steps complete',
  'progress.live_output': 'Live output',
  'progress.lines': '{count} lines',
  'progress.show_details': 'Show details',
  'progress.hide_details': 'Hide details',
  'progress.cancel': 'Cancel',
  'progress.done': 'Done',

  // ── success ────────────────────────────────────────────────────────────────
  'success.title': 'Thor is ready',
  'success.desc': 'Everything is set up. Open the desktop app to start.',
  'success.launch': 'Launch',
  'success.launching': 'Launching',
  'success.open_desktop': 'Open the desktop app any time with:',
  'success.launch_failed_title': 'Couldn\u2019t launch the desktop app',
  'success.launch_failed_hint': 'You can still open it from your applications menu.',

  // ── failure ────────────────────────────────────────────────────────────────
  'failure.title_install': 'Install didn\u2019t finish',
  'failure.title_update': 'Update didn\u2019t finish',
  'failure.body_install': 'Something went wrong during installation.',
  'failure.body_update': 'Something went wrong during the update.',
  'failure.retry_install': 'Retry install',
  'failure.retry_update': 'Retry update',
  'failure.open_logs': 'Open logs',
  'failure.log_label': 'Log:',

  // ── stage state labels ─────────────────────────────────────────────────────
  'stage.running': 'Running',
  'stage.succeeded': 'Done',
  'stage.skipped': 'Skipped',
  'stage.failed': 'Failed'
}

const ID: Catalog = {
  // ── welcome ────────────────────────────────────────────────────────────────
  'welcome.tagline': 'Agent yang tumbuh bersama kamu. Kami siapkan semuanya di latar belakang \u2014 hanya butuh beberapa menit.',
  'welcome.install': 'Pasang',
  'welcome.language_label': 'Bahasa',
  'welcome.language_aria': 'Pilih bahasa pemasang',

  // ── progress ───────────────────────────────────────────────────────────────
  'progress.title_install': 'Memasang Thor',
  'progress.title_update': 'Memperbarui Thor',
  'progress.desc_install': 'Proses ini berjalan di latar belakang \u2014 kamu bisa tinggalkan saja.',
  'progress.desc_update': 'Mengambil versi terbaru dan menerapkannya.',
  'progress.steps_complete': '{done} dari {total} langkah selesai',
  'progress.live_output': 'Keluaran langsung',
  'progress.lines': '{count} baris',
  'progress.show_details': 'Tampilkan rincian',
  'progress.hide_details': 'Sembunyikan rincian',
  'progress.cancel': 'Batal',
  'progress.done': 'Selesai',

  // ── success ────────────────────────────────────────────────────────────────
  'success.title': 'Thor siap',
  'success.desc': 'Semuanya sudah disiapkan. Buka aplikasi desktop untuk mulai.',
  'success.launch': 'Buka',
  'success.launching': 'Membuka',
  'success.open_desktop': 'Buka aplikasi desktop kapan saja dengan:',
  'success.launch_failed_title': 'Tidak bisa membuka aplikasi desktop',
  'success.launch_failed_hint': 'Kamu tetap bisa membukanya dari menu aplikasi.',

  // ── failure ────────────────────────────────────────────────────────────────
  'failure.title_install': 'Pemasangan tidak selesai',
  'failure.title_update': 'Pembaruan tidak selesai',
  'failure.body_install': 'Ada yang gagal saat pemasangan.',
  'failure.body_update': 'Ada yang gagal saat pembaruan.',
  'failure.retry_install': 'Coba pasang lagi',
  'failure.retry_update': 'Coba perbarui lagi',
  'failure.open_logs': 'Buka log',
  'failure.log_label': 'Log:',

  // ── stage state labels ─────────────────────────────────────────────────────
  'stage.running': 'Berjalan',
  'stage.succeeded': 'Selesai',
  'stage.skipped': 'Dilewati',
  'stage.failed': 'Gagal'
}

const CATALOGS: Record<Lang, Catalog> = { en: EN, id: ID }

/** Map any browser/BCP-47 tag onto a bundled id ("id-ID" -> "id", "en-GB" -> "en"). */
export function resolveLang(value: string | null | undefined): Lang | null {
  if (!value) {return null}
  const norm = value.trim().toLowerCase().replace('_', '-')
  const exact = LANGUAGES.find((l) => l.id === norm)

  if (exact) {return exact.id}
  const base = norm.split('-')[0]
  const hit = LANGUAGES.find((l) => l.id === base)

  return hit ? hit.id : null
}

/** Detected language: stored choice -> browser locale -> English. */
export function detectLang(): Lang {
  try {
    const stored = resolveLang(localStorage.getItem(STORAGE_KEY))

    if (stored) {return stored}
  } catch {
    /* localStorage can be unavailable in a locked-down webview */
  }

  const nav = typeof navigator !== 'undefined' ? navigator.languages?.[0] ?? navigator.language : null

  return resolveLang(nav) ?? DEFAULT_LANG
}

export function persistLang(lang: Lang): void {
  try {
    localStorage.setItem(STORAGE_KEY, lang)
  } catch {
    /* non-fatal: the picker still works for this session */
  }
}

/**
 * Translate a catalog key. Unknown keys return the key itself (same contract as
 * the agent's Python `t()`), and `{placeholder}` values are substituted from
 * `params`. A missing translation falls back to English before the bare key.
 */
export function translate(lang: Lang, key: string, params?: Record<string, string | number>): string {
  const value = CATALOGS[lang]?.[key] ?? CATALOGS[DEFAULT_LANG][key] ?? key

  if (!params) {return value}

  return value.replace(/\{(\w+)\}/g, (match, name: string) =>
    Object.prototype.hasOwnProperty.call(params, name) ? String(params[name]) : match
  )
}

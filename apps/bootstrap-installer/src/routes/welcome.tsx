import { useStore } from '@nanostores/react'
import { type CSSProperties } from 'react'

import { HackeryButton } from '../components/hackery-button'
import { LANGUAGES, translate } from '../lib/i18n'
import { $lang, setLang, startInstall } from '../store'

/*
 * Welcome screen — also the pre-install language menu.
 *
 * Mirrors the desktop's chat intro (apps/desktop/src/components/chat/intro.tsx):
 *   - THOR AGENT wordmark rendered in Collapse Bold, uppercase, tracked
 *   - mix-blend-plus-lighter so the type "glows" on the canvas
 *   - fit-text utility so the wordmark sizes itself to the column
 *
 * A compact language selector sits under the tagline. This is the first screen
 * the user sees, so it is the only place the choice can be made BEFORE install
 * touches disk. The choice persists via store.setLang, and every later screen
 * reads $lang, so switching here re-renders the whole flow.
 *
 * No install-path footer. The default install location is correct for
 * 99% of users; the rest will use the CLI installer with a -ThorHome
 * flag. Showing %LOCALAPPDATA% to grandma is developer-brain.
 */
export default function Welcome() {
  const lang = useStore($lang)
  const t = (key: string, params?: Record<string, string | number>) => translate(lang, key, params)

  return (
    <div className="thor-fade-in flex h-full flex-col items-center justify-center gap-10 px-12 py-10">
      {/* Hero — same recipe the desktop's chat/intro.tsx uses */}
      <div className="w-full max-w-2xl min-w-0 text-center">
        <p
          className="fit-text mx-auto mb-4 w-full font-['Collapse'] font-bold uppercase leading-[0.9] tracking-[0.08em] text-midground mix-blend-plus-lighter dark:text-foreground/90"
          style={
            {
              '--fit-text-line-height': '0.9',
              '--fit-text-max': '6rem',
              '--fit-text-min': '2.5rem'
            } as CSSProperties
          }
        >
          <span>
            <span>THOR AGENT</span>
          </span>
          <span aria-hidden="true">THOR AGENT</span>
        </p>

        <p className="m-0 text-center text-base leading-normal tracking-tight text-muted-foreground">
          {t('welcome.tagline')}
        </p>
      </div>

      {/* Language menu — shown before the user commits to an install. */}
      <div className="flex flex-col items-center gap-2">
        <span className="text-xs uppercase tracking-wider text-muted-foreground/70">
          {t('welcome.language_label')}
        </span>
        <div
          aria-label={t('welcome.language_aria')}
          className="flex items-center gap-1 rounded-full border border-(--stroke-thor) p-1"
          role="radiogroup"
        >
          {LANGUAGES.map((option) => {
            const active = option.id === lang

            return (
              <button
                aria-checked={active}
                className={
                  'cursor-pointer rounded-full px-3 py-1 text-sm transition-colors ' +
                  (active
                    ? 'bg-primary text-primary-foreground font-medium'
                    : 'text-muted-foreground hover:text-foreground')
                }
                key={option.id}
                onClick={() => setLang(option.id)}
                role="radio"
                type="button"
              >
                {option.endonym}
              </button>
            )
          })}
        </div>
      </div>

      <HackeryButton label={t('welcome.install')} onClick={() => void startInstall()} />
    </div>
  )
}

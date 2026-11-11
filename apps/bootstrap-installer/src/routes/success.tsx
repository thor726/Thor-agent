import { useStore } from '@nanostores/react'
import { AlertCircle } from 'lucide-react'
import { useState } from 'react'
import { type CSSProperties } from 'react'

import { HackeryButton } from '../components/hackery-button'
import { translate } from '../lib/i18n'
import { $lang, launchThorDesktop } from '../store'

/*
 * Success screen. THOR AGENT wordmark stays as the visual anchor
 * (same Collapse Bold treatment as Welcome + the desktop chat intro),
 * with a status line below.
 *
 * Launching the desktop can fail (e.g. Stage-Desktop was skipped and
 * Thor.exe doesn't exist). We catch the Tauri error and surface it
 * inline rather than silently doing nothing — the previous version
 * had `onClick={() => void launchThorDesktop()}` which swallowed
 * the rejection and left the user staring at an unresponsive button.
 */
export default function Success() {
  const [error, setError] = useState<string | null>(null)
  const [launching, setLaunching] = useState(false)
  const lang = useStore($lang)
  const t = (key: string, params?: Record<string, string | number>) => translate(lang, key, params)

  async function handleLaunch() {
    setError(null)
    setLaunching(true)

    try {
      await launchThorDesktop()
      // On success the installer exits — control never returns here.
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e)
      setError(msg)
      setLaunching(false)
    }
  }

  return (
    <div className="thor-fade-in flex h-full flex-col items-center justify-center gap-8 px-12 py-10">
      <div className="w-full max-w-2xl min-w-0 text-center">
        <p
          className="fit-text mx-auto mb-4 w-full font-['Collapse'] font-bold uppercase leading-[0.9] tracking-[0.08em] text-midground mix-blend-plus-lighter dark:text-foreground/90"
          style={
            {
              '--fit-text-line-height': '0.9',
              '--fit-text-max': '5rem',
              '--fit-text-min': '2.25rem'
            } as CSSProperties
          }
        >
          <span>
            <span>{t('success.title')}</span>
          </span>
          <span aria-hidden="true">{t('success.title')}</span>
        </p>

        <p className="m-0 text-center text-base leading-normal tracking-tight text-muted-foreground">
          {t('success.desc')} {t('success.open_desktop')}{' '}
          <code className="font-mono text-sm text-foreground/80">thor desktop</code>
        </p>
      </div>

      <HackeryButton
        disabled={launching}
        label={launching ? t('success.launching') : t('success.launch')}
        loading={launching}
        onClick={() => void handleLaunch()}
      />

      {error && (
        <div className="flex max-w-2xl items-start gap-2 text-sm" role="alert">
          <AlertCircle className="mt-0.5 shrink-0 text-destructive" size={16} />
          <div className="min-w-0">
            <div className="font-medium text-destructive">{t('success.launch_failed_title')}</div>
            <div className="mt-0.5 text-muted-foreground">{error}</div>
          </div>
        </div>
      )}
    </div>
  )
}

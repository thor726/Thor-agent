// The Thor home the desktop main process runs against, resolved once at boot.
// Resolving it here also registers it with the file-preview read guard, so the
// home's (and every profile's) credential stores are refused before any IPC
// read can be served.

import { resolveDesktopThorHome } from './data-paths'
import { directoryExists } from './fs-probes'
import { setSensitiveThorHome } from './hardening'
import { readWindowsUserEnvVar } from './windows-user-env'

export function resolveMainThorHome(home: string): string {
  const thorHome = resolveDesktopThorHome({
    home,
    directoryExists,
    readWindowsHome: (): string | null => readWindowsUserEnvVar('THOR_HOME')
  })

  setSensitiveThorHome(thorHome)

  return thorHome
}

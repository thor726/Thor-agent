/**
 * Thor Cloud agents: their public host is `<label>.agents.thor-agent.local`
 * (staging `<label>.agents.staging-thor-agent.local`), the URL the portal gives
 * each agent. Cloud updates an agent by replacing its image, so nothing may run
 * `thor update` against one.
 */

const THOR_CLOUD_HOST_SUFFIXES = ['.agents.thor-agent.local', '.agents.staging-thor-agent.local']

/** Why an update target is skipped: the platform updates it. */
export const THOR_CLOUD_MANAGED = 'cloud-managed'

export function isThorCloudUrl(url: null | string | undefined): boolean {
  if (!url) {
    return false
  }

  try {
    const host = new URL(url).hostname.toLowerCase()

    return THOR_CLOUD_HOST_SUFFIXES.some(suffix => host.endsWith(suffix))
  } catch {
    return false
  }
}

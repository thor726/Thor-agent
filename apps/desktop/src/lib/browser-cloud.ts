import type {
  DesktopCloudAgentSignInResult,
  DesktopCloudDiscoverResult,
  DesktopCloudStatus,
  ThorApiRequest
} from '@/global'
import { signInSavedConnection } from '@/lib/browser-saved-connection-oauth'
import type { BrowserSavedConnections } from '@/lib/browser-saved-connections'

type Api = <T>(request: ThorApiRequest) => Promise<T>

/**
 * Thor Cloud for the Webapp. Native Desktop lists cloud agents through its own portal browser
 * session; a browser tab has none, so the gateway serving it asks Nous Portal with its own sign-in
 * (`GET /api/cloud/agents`). Signing in to one agent is the serving gateway's saved-connection
 * OAuth, the flow Settings ▸ Gateway already runs here.
 */
export function createBrowserCloudBridge({
  api,
  relays
}: {
  api: Api
  relays: BrowserSavedConnections | null
}): Window['thorDesktop']['cloud'] {
  const status = async (): Promise<DesktopCloudStatus> => {
    const portal = await api<{ logged_in?: boolean; portal_url?: string }>({ path: '/api/portal' })

    return { portalBaseUrl: portal.portal_url || '', signedIn: Boolean(portal.logged_in) }
  }

  return {
    status,
    // The install signs in to Nous Portal from Settings ▸ Providers; a browser tab cannot run it here.
    login: async () => ({ ...(await status()), ok: false }),
    logout: async () => ({ ...(await status()), ok: false }),
    discover: (org?: string) =>
      api<DesktopCloudDiscoverResult>({
        path: `/api/cloud/agents${org ? `?org=${encodeURIComponent(org)}` : ''}`,
        timeoutMs: 30_000
      }),
    agentSignIn: async (dashboardUrl: string): Promise<DesktopCloudAgentSignInResult> => {
      if (!relays) {
        return { baseUrl: dashboardUrl, connected: false }
      }

      const label = new URL(dashboardUrl).hostname.split('.')[0] || 'Thor Cloud'
      const result = await signInSavedConnection(api, relays, dashboardUrl, { kind: 'cloud', label })

      return { baseUrl: dashboardUrl, connected: result.connected, connectionId: result.connectionId }
    }
  }
}

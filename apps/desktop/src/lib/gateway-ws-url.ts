import { resolveGatewayWsUrl } from '@thor/shared'

import type { ThorConnection } from '@/global'

export function resolveDesktopGatewayWsUrl(
  desktop: Window['thorDesktop'],
  connection: ThorConnection
): Promise<string> {
  // Only a registry-scoped descriptor may use the *For bridge (see
  // ThorConnection.registryScoped); an absent bridge fails closed rather
  // than minting the peer's URL against the local pool.
  const { connectionId, profile, registryScoped } = connection

  if (!registryScoped || !connectionId) {
    return resolveGatewayWsUrl(desktop, connection)
  }

  const mint = desktop.getGatewayWsUrlFor

  return resolveGatewayWsUrl({ getGatewayWsUrl: mint ? () => mint({ connectionId, profile }) : undefined }, connection)
}

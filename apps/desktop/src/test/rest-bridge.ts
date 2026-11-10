import { vi } from 'vitest'

import type { ThorApiRequest } from '@/global'

/** Install a fake `window.thorDesktop.api`, the preload bridge every REST helper sends through. */
export function installRestBridge(answer: (request: ThorApiRequest) => object) {
  const api = vi.fn(async (request: ThorApiRequest) => answer(request))

  Object.defineProperty(window, 'thorDesktop', { configurable: true, value: { api } })

  return api
}

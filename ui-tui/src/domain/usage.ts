import type { Usage } from '@thor/shared/gateway-events'

export { usageFromTick } from '@thor/shared/usage-tick'

export const ZERO: Usage = { calls: 0, input: 0, output: 0, total: 0 }

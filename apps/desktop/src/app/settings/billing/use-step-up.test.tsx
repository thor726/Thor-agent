import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, renderHook, waitFor } from '@testing-library/react'
import { createElement, type PropsWithChildren } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const apiMocks = vi.hoisted(() => ({
  stepUp: vi.fn()
}))

vi.mock('./api', () => ({
  useBillingApi: () => ({
    stepUp: apiMocks.stepUp
  })
}))

import { $stepUpInFlight, useStepUpFlow } from './use-step-up'

function createWrapper(client: QueryClient) {
  return function wrapper({ children }: PropsWithChildren) {
    return createElement(QueryClientProvider, { client }, children)
  }
}

beforeEach(() => {
  apiMocks.stepUp.mockReset()
})

afterEach(() => {
  vi.clearAllMocks()
})

describe('useStepUpFlow', () => {
  it('starts the step-up, cleans up, and invalidates on completion', async () => {
    let resolveStepUp: (value: unknown) => void = () => {}

    const stepUpPromise = new Promise(resolve => {
      resolveStepUp = resolve
    })

    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const invalidate = vi.spyOn(client, 'invalidateQueries')

    apiMocks.stepUp.mockReturnValue(stepUpPromise)

    const { result, unmount } = renderHook(() => useStepUpFlow(), { wrapper: createWrapper(client) })

    act(() => {
      void result.current.start()
    })

    expect(result.current.phase).toBe('waiting')

    await act(async () => {
      resolveStepUp({ data: { granted: true, ok: true }, ok: true })
      await stepUpPromise
    })

    await waitFor(() => {
      expect(invalidate).toHaveBeenCalledWith({ queryKey: ['billing', 'state'] })
      expect(invalidate).toHaveBeenCalledWith({ queryKey: ['billing', 'subscription'] })
    })
    expect(result.current.phase).toBe('idle')

    unmount()
  })

  it("one flow dismissing never resumes billing refetches during another flow's approval", async () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })

    let resolveStepUp: (value: unknown) => void = () => {}

    apiMocks.stepUp.mockReturnValue(new Promise(resolve => (resolveStepUp = resolve)))

    const owner = renderHook(() => useStepUpFlow(), { wrapper: createWrapper(client) })
    const other = renderHook(() => useStepUpFlow(), { wrapper: createWrapper(client) })

    act(() => {
      void owner.result.current.start()
    })
    expect($stepUpInFlight.get()).toBe(true)

    act(() => other.result.current.dismiss())
    expect($stepUpInFlight.get()).toBe(true)

    other.unmount()
    expect($stepUpInFlight.get()).toBe(true)

    await act(async () => resolveStepUp({ data: { granted: false, ok: true }, ok: true }))
    expect($stepUpInFlight.get()).toBe(false)
    owner.unmount()
  })
})

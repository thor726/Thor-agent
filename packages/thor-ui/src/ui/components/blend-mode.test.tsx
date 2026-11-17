import { Component, type ReactNode, useState } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { flushSync } from 'react-dom'
import { afterEach, beforeEach, expect, test } from 'vitest'

import { useSmoothControls } from '../../hooks/use-smooth-controls'

import { BlendMode } from './blend-mode'

// Regression guard for React error #310 ("Rendered more hooks than during the
// previous render") in BlendMode / useBlendMode.
//
// `useControlColor` reads a `Lens` control atom from the module-scoped
// `atomRegistry`, which is populated *lazily during render* by the first
// `useSmoothControls('Lens', …)` consumer. The original code called
// `useStore(atom)` only when that atom existed:
//
//   return (atom ? useStore(atom) : undefined) ?? fallback   // ❌ conditional
//
// So a BlendMode that first renders with the registry empty (atom undefined →
// useStore skipped) and later re-renders after a Lens consumer mounts (atom
// present → useStore runs) changed its hook count between renders and React
// threw #310. This is the production crash on portal.thor-agent.local when
// navigating Manage Subscription → Portal: the manage-subscription tree uses
// many BlendMode-backed @thor/ui components but does NOT render the
// Overlays/Lens shell, so the registry starts empty, then a theme toggle /
// overlay populates it mid-session.
//
// NOTE: this is a plain unit test (not a Storybook story) on purpose. The
// Storybook `withShell` decorator always renders <Overlays> first, which
// pre-populates the Lens registry — masking the empty→populated transition
// that triggers the bug. Here nothing imports Overlays, so the registry
// genuinely starts empty.

let container: HTMLDivElement
let root: Root
let caughtError: Error | null = null

class ErrorBoundary extends Component<{ children: ReactNode }, { error: Error | null }> {
  state: { error: Error | null } = { error: null }

  static getDerivedStateFromError(error: Error) {
    caughtError = error
    return { error }
  }

  render() {
    return this.state.error ? null : this.props.children
  }
}

// Populates the module-scoped Lens atom registry — the exact mutation that
// flips getControlAtom('Lens', 'bgColor') from undefined to a real atom.
function LensRegistrar() {
  useSmoothControls(
    'Lens',
    {
      bgColor: { value: '#0E0313' },
      fgColor: { value: '#ffffff' },
      mgColor: { value: '#e6cbff' }
    },
    { collapsed: true }
  )

  return null
}

let registerLens: (() => void) | null = null
let rerenderBlend: (() => void) | null = null

function Harness() {
  const [lensMounted, setLensMounted] = useState(false)
  const [bump, setBump] = useState(0)

  registerLens = () => setLensMounted(true)
  rerenderBlend = () => setBump(n => n + 1)

  return (
    <ErrorBoundary>
      <BlendMode
        background="mg/0.1"
        color="fg"
        data-testid="blend"
        data-bump={bump}
      >
        blend
      </BlendMode>
      {lensMounted && <LensRegistrar />}
    </ErrorBoundary>
  )
}

beforeEach(() => {
  caughtError = null
  registerLens = null
  rerenderBlend = null
  container = document.createElement('div')
  document.body.appendChild(container)
  root = createRoot(container)
})

afterEach(() => {
  flushSync(() => root.unmount())
  container.remove()
})

test('BlendMode survives the Lens registry being populated after first render', () => {
  // 1) First render: Lens registry empty → getControlAtom returns undefined.
  flushSync(() => root.render(<Harness />))
  expect(container.querySelector('[data-testid="blend"]')).not.toBeNull()
  expect(caughtError).toBeNull()

  // 2) Populate the Lens registry in its own commit.
  flushSync(() => registerLens!())

  // 3) Re-render the same BlendMode instance in a separate commit, now that
  //    the registry is populated. With the buggy conditional hook this is the
  //    #310 trigger; the ErrorBoundary would catch the thrown error.
  flushSync(() => rerenderBlend!())

  expect(caughtError).toBeNull()
  const blend = container.querySelector('[data-testid="blend"]')
  expect(blend).not.toBeNull()
  expect(blend!.getAttribute('data-bump')).toBe('1')
})

import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { HostedNotice } from './hosted-notice'

afterEach(() => {
  cleanup()
  window.location.hash = ''
})

describe('the Connectors line for a signed-out account', () => {
  it('offers a Sign in that opens ThorHub sign-in in Settings', () => {
    render(<HostedNotice phase="signedOut" />)

    expect(screen.getByText('Sign in to Thor to use managed apps.')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(window.location.hash).toBe('#/settings?tab=providers')
  })

  it('renders nothing once signed in', () => {
    const { container } = render(<HostedNotice phase="ready" />)

    expect(container.firstChild).toBeNull()
  })
})

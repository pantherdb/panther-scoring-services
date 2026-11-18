import { MantineProvider } from '@mantine/core'
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { cssVariablesResolver, theme } from '@/app/theme'
import { SubmitAlert } from '@/components/SubmitAlert'
import type { NotStarted } from '@/components/submitProblem'

function show(failure: NotStarted | null, limited = false) {
  render(
    <MantineProvider theme={theme} cssVariablesResolver={cssVariablesResolver} env="test">
      <SubmitAlert failure={failure} title="HMM scoring" limited={limited} />
    </MantineProvider>
  )
}

describe('SubmitAlert', () => {
  it.each([
    [{ problem: 'unavailable', retryAfter: null }, /hmm scoring isn.t available yet/i],
    [{ problem: 'busy', retryAfter: 30 }, /hmm scoring is busy.*about 30 seconds/i],
    [{ problem: 'unreachable', retryAfter: null }, /can.t be reached/i],
    [{ problem: 'failed', retryAfter: null }, /couldn.t be started/i],
  ] as const)('says %o in its own words', (failure, text) => {
    show(failure)

    expect(screen.getByRole('alert')).toHaveTextContent(text)
  })

  it.each([
    { problem: 'unavailable', retryAfter: null },
    { problem: 'busy', retryAfter: 30 },
    { problem: 'failed', retryAfter: null },
  ] as const)('limited, says %o as the job not started', failure => {
    show(failure, true)

    expect(screen.getByRole('alert')).toHaveTextContent(/couldn.t be started/i)
    expect(screen.getByRole('alert')).not.toHaveTextContent(/hmm scoring/i)
  })

  it('limited, still says the service cannot be reached', () => {
    show({ problem: 'unreachable', retryAfter: null }, true)

    expect(screen.getByRole('alert')).toHaveTextContent(/can.t be reached/i)
  })

  it('shows nothing without a failure', () => {
    show(null)

    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })
})

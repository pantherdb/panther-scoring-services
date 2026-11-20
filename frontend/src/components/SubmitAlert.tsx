import { Alert } from '@mantine/core'

import type { NotStarted } from './submitProblem'

type Props = {
  /** The last submit's failure, other than a 422; none to show nothing. */
  failure: NotStarted | null
  /** The service's title, as `services.ts` gives it, for the `busy` text. */
  title: string
  /**
   * Show `busy` as `failed`: the cSNP and refmap forms' requirements give every failure but a
   * 422 and no answer at all the one message.
   */
  limited?: boolean
}

/** When to try again: "in about 30 seconds", "in about 2 minutes", or "in a few minutes". */
export function tryAgainIn(seconds: number | null): string {
  if (seconds === null) return 'in a few minutes'
  if (seconds <= 1) return 'in a moment'
  if (seconds <= 90) return `in about ${seconds} seconds`
  const minutes = Math.round(seconds / 60)
  return `in about ${minutes} minutes`
}

// Why the last submit didn't open a job, in fixed text: the response could carry build
// details. The input is kept whatever the problem; every text but `failed`'s says so, and
// `failed`'s is the cSNP and refmap forms' text from before the hmmscore form.
export function SubmitAlert({ failure, title, limited = false }: Props) {
  const shown = limited && failure?.problem === 'busy' ? 'failed' : (failure?.problem ?? null)
  switch (shown) {
    case 'busy':
      return (
        <Alert title={`${title} is busy`}>
          Too many jobs are waiting, so no job was started. Try again{' '}
          {tryAgainIn(failure?.retryAfter ?? null)}. Your input is kept on this page.
        </Alert>
      )
    case 'unreachable':
      return (
        <Alert title="The scoring service can’t be reached">
          Check your connection, then try again in a moment. Your input is kept on this page.
        </Alert>
      )
    case 'failed':
      return <Alert title="The job couldn’t be started">Try again in a moment.</Alert>
    case null:
      return null
  }
}

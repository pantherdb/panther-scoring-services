import { Alert } from '@mantine/core'

import type { SubmitProblem } from './submitProblem'

type Props = {
  problem: SubmitProblem | null
  /** The service's title, as `services.ts` gives it, for the `unavailable` and `busy` texts. */
  title: string
  /** The seconds the API said to wait, from `Retry-After`; null without them. */
  retryAfter?: number | null
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
// details. Every text says the input is kept, since it is.
export function SubmitAlert({ problem, title, retryAfter = null }: Props) {
  switch (problem) {
    case 'unavailable':
      return (
        <Alert title={`${title} isn’t available yet`}>
          This site can’t run it yet, so no job was started. Your input is kept on this page.
        </Alert>
      )
    case 'busy':
      return (
        <Alert title={`${title} is busy`}>
          Too many jobs are waiting, so no job was started. Try again {tryAgainIn(retryAfter)}. Your
          input is kept on this page.
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

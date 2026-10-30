import { Alert } from '@mantine/core'

import type { SubmitProblem } from './useSubmitCsnp'

type Props = {
  problem: SubmitProblem
}

// Why the last submit didn't open a job, in fixed text: the response could carry build
// details, and the 501's wording is the UI's own.
export function SubmitAlert({ problem }: Props) {
  switch (problem) {
    case 'unavailable':
      return (
        <Alert title="cSNP scoring isn’t available yet">
          Scoring is still being moved to this website. Your input is kept on this page.
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

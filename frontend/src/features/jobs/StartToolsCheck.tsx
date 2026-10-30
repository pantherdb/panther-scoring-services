import { Alert, Button } from '@mantine/core'
import { useNavigate } from 'react-router'

import { isUnreachable } from '@/app/api/errors'

import { useStartJobMutation } from './jobsApi'

// A placeholder until the service forms exist: starts the built-in tools job,
// which reports each scoring tool's version, and opens its page.
export function StartToolsCheck() {
  const [startJob, { isLoading, isError, error }] = useStartJobMutation()
  const navigate = useNavigate()

  async function start() {
    try {
      const job = await startJob({ service: 'tools', input: {} }).unwrap()
      await navigate(`/jobs/${job.id}`)
    } catch {
      // Shown from the mutation's isError, with fixed text: the error could carry build details.
    }
  }

  return (
    <section className="flex flex-col items-start gap-2 border-t border-hairline pt-6">
      <h3 className="font-semibold">Scoring tools</h3>
      <p className="text-sm text-ink-muted">
        Run a quick job that reports the version of each tool the scoring services use.
      </p>
      <Button
        variant="default"
        onClick={() => void start()}
        loading={isLoading}
        disabled={isLoading}
      >
        Check the scoring tools
      </Button>
      {isError &&
        (isUnreachable(error) ? (
          <Alert title="The scoring service can’t be reached" className="w-full">
            Check your connection, then try again in a moment.
          </Alert>
        ) : (
          <Alert title="The check couldn’t be started" className="w-full">
            Try again in a moment.
          </Alert>
        ))}
    </section>
  )
}

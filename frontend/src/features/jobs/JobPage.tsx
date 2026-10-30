import { Alert, Button, Loader } from '@mantine/core'
import { Link, useParams } from 'react-router'

import { JobDetails } from './JobDetails'
import { isNotFound, useJob } from './useJob'

// /jobs/:id. Shows one state: not found, unavailable, loading, or the job.
export function JobPage() {
  const { id = '' } = useParams()
  const { data: job, error, isError, refetch } = useJob(id)

  if (isError && isNotFound(error)) return <JobNotFound />
  // Fixed text only: the error's status and body could carry build details.
  if (isError) return <JobUnavailable onRetry={() => void refetch()} />
  // Not isLoading: it's false while "Try again" refetches after an error.
  if (!job) return <JobLoading />
  return <JobDetails job={job} />
}

function JobNotFound() {
  return (
    <section className="flex flex-col items-start gap-4">
      <h2 className="text-lg font-semibold">Job not found</h2>
      <p className="text-ink-muted">
        There is no job at this address. The link may be wrong, or the job has expired: finished
        jobs are kept for a limited time.
      </p>
      <Button component={Link} to="/">
        Back to home
      </Button>
    </section>
  )
}

type UnavailableProps = {
  onRetry: () => void
}

function JobUnavailable({ onRetry }: UnavailableProps) {
  return (
    <section className="flex flex-col items-start gap-4">
      <h2 className="text-lg font-semibold">Job unavailable</h2>
      <Alert title="The job couldn’t be loaded" className="w-full">
        Try again in a moment.
      </Alert>
      <Button onClick={onRetry}>Try again</Button>
    </section>
  )
}

function JobLoading() {
  return (
    <div className="flex items-center gap-2 text-ink-muted">
      <Loader size="sm" />
      <p>Loading the job…</p>
    </div>
  )
}

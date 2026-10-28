import { Button } from '@mantine/core'
import { Link } from 'react-router'

export function NotFoundPage() {
  return (
    <section className="flex flex-col items-start gap-4">
      <h2 className="text-lg font-semibold">Page not found</h2>
      <p className="text-ink-muted">There is no page at this address.</p>
      <Button component={Link} to="/">
        Back to home
      </Button>
    </section>
  )
}

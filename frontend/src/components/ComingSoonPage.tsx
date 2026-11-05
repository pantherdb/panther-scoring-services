import { Button } from '@mantine/core'
import { Link } from 'react-router'

import { service, type ServiceId } from '@/app/services'

type Props = {
  id: ServiceId
}

// The page of a service that has no form yet: what it will do, and that it's coming.
export function ComingSoonPage({ id }: Props) {
  const { title, summary } = service(id)
  return (
    <section className="flex flex-col items-start gap-4">
      <div className="flex flex-wrap items-center gap-2">
        <h2 className="text-lg font-semibold">{title}</h2>
        <ComingSoonBadge />
      </div>
      <p className="text-ink-muted">{summary}</p>
      <p>This service is coming soon. It can’t be used on this site yet.</p>
      <Button component={Link} to="/">
        Back to home
      </Button>
    </section>
  )
}

// The mark on a service the API can't score yet, beside its name.
export function ComingSoonBadge() {
  return (
    <span className="rounded-full bg-primary-50 px-2 py-0.5 text-xs font-medium text-primary-800">
      Coming soon
    </span>
  )
}

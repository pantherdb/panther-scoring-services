import { Button } from '@mantine/core'
import { Link } from 'react-router'

import { SERVICES, type Service } from '@/app/services'
import { ComingSoonBadge } from '@/components/ComingSoonPage'
import { StartToolsCheck } from '@/features/jobs'

// The four services, in priority order, then the scoring tools check.
export function HomePage() {
  return (
    <div className="flex flex-col gap-8">
      <ul className="grid gap-4 sm:grid-cols-2">
        {SERVICES.map(service => (
          <li key={service.id} className="flex">
            <ServiceCard service={service} />
          </li>
        ))}
      </ul>
      <StartToolsCheck />
    </div>
  )
}

type Props = {
  service: Service
}

function ServiceCard({ service }: Props) {
  return (
    <section className="flex w-full flex-col items-start gap-2 rounded-xl bg-white p-6 shadow-sm">
      <div className="flex flex-wrap items-center gap-2">
        <h2 className="text-lg font-semibold">{service.title}</h2>
        {service.comingSoon && <ComingSoonBadge />}
      </div>
      <p className="flex-1 text-ink-muted">{service.summary}</p>
      {service.action ? (
        <Button component={Link} to={service.path} className="mt-2">
          {service.action}
        </Button>
      ) : (
        <Button component={Link} to={service.path} variant="default" className="mt-2">
          Find out more
        </Button>
      )}
    </section>
  )
}

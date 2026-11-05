import { useEffect, useRef } from 'react'
import { Link, useLocation } from 'react-router'

import { SERVICES, type Service } from '@/app/services'
import { useShownJobService } from '@/features/jobs'

// One link per service, in priority order. Links, not Mantine's Tabs, which are ARIA tabs
// for panels on one page; these change the page, and the current one has aria-current.
export function ServiceTabs() {
  const { pathname } = useLocation()
  const jobService = useShownJobService()

  function isCurrent(service: Service) {
    return pathname === service.path || jobService === service.id
  }

  return (
    <nav aria-label="Services" className="-mx-4 mt-2 overflow-x-auto px-2 sm:px-1">
      <ul className="flex gap-1 whitespace-nowrap">
        {SERVICES.map(service => (
          <li key={service.id}>
            <ServiceTab service={service} current={isCurrent(service)} />
          </li>
        ))}
      </ul>
    </nav>
  )
}

type Props = {
  service: Service
  current: boolean
}

function ServiceTab({ service, current }: Props) {
  const link = useRef<HTMLAnchorElement>(null)

  // On a phone the tabs can be wider than the screen: bring the current one into view.
  useEffect(() => {
    if (current) link.current?.scrollIntoView({ block: 'nearest', inline: 'nearest' })
  }, [current])

  return (
    <Link
      ref={link}
      to={service.path}
      aria-current={current ? 'page' : undefined}
      // The name keeps the visible label first, so voice control finds it by what it shows.
      aria-label={service.comingSoon ? `${service.label} (coming soon)` : undefined}
      className={`flex items-center gap-1.5 rounded-t-md border-b-2 px-2 py-2 text-sm hover:bg-primary-800 focus-visible:outline-2 sm:px-3 ${
        current ? 'border-white font-semibold' : 'border-transparent'
      }`}
    >
      {service.label}
      {service.comingSoon && (
        <span className="rounded-full bg-primary-900 px-1.5 text-xs font-normal">Soon</span>
      )}
    </Link>
  )
}

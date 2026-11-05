import { Link } from 'react-router'

import { ServiceTabs } from './ServiceTabs'

// The header: the application title, a link home, and the service tabs. Shared by the layout
// and the root error page, so both stay even when the layout itself fails to render.
export function AppHeader() {
  return (
    <header className="bg-primary-700 text-white">
      <div className="mx-auto w-full max-w-5xl px-4 pt-4">
        <h1 className="text-xl font-semibold">
          <Link to="/" className="rounded-sm hover:underline focus-visible:outline-2">
            PANTHER Scoring
          </Link>
        </h1>
        <ServiceTabs />
      </div>
    </header>
  )
}

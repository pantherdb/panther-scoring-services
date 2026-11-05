import { IconExternalLink } from '@tabler/icons-react'

import { apiBaseUrl } from '@/app/apiBaseUrl'
import { isApiMocked } from '@/app/mocking'

// The API's interactive docs, on the API this site calls. Not on mocked answers: there's no API
// behind them. A plain link, not the router's: the docs are served by the API, not by this app.
// In a new tab, so the page the user was on stays; noopener, so the docs can't reach back to it.
export function ApiDocsLink() {
  if (isApiMocked()) return null
  return (
    <a
      className="inline-flex items-center gap-1 text-primary-700 underline hover:no-underline"
      href={`${apiBaseUrl()}/docs`}
      target="_blank"
      rel="noopener noreferrer"
      aria-label="API docs (opens in a new tab)"
    >
      API docs
      <IconExternalLink size={14} aria-hidden="true" />
    </a>
  )
}

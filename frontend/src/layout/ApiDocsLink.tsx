import { apiBaseUrl } from '@/app/apiBaseUrl'
import { isApiMocked } from '@/app/mocking'

// The API's interactive docs, on the API this site calls. Not on mocked answers: there's no API
// behind them. A plain link, not the router's: the docs are served by the API, not by this app.
export function ApiDocsLink() {
  if (isApiMocked()) return null
  return (
    <a className="text-primary-700 underline hover:no-underline" href={`${apiBaseUrl()}/docs`}>
      API docs
    </a>
  )
}

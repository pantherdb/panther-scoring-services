import { Button } from '@mantine/core'
import { useEffect } from 'react'
import { Link, useRouteError } from 'react-router'

// What a route shows when rendering it throws: fixed text and a way home. The error itself
// can carry a stack and the bundle's URLs, so it never reaches the screen; in development
// it goes to the console.
export function ErrorPage() {
  const error = useRouteError()

  useEffect(() => {
    if (import.meta.env.DEV) console.warn('A page failed to render:', error)
  }, [error])

  return (
    <section className="flex flex-col items-start gap-4">
      <h2 className="text-lg font-semibold">Something went wrong</h2>
      <p className="text-ink-muted">
        This page couldn&apos;t be shown. Try again later, or go back to the home page.
      </p>
      <Button component={Link} to="/">
        Back to home
      </Button>
    </section>
  )
}

import { IconAlertTriangle } from '@tabler/icons-react'

// Shown on every page while the API is mocked, so a screenshot of mock data can't pass for
// a real result. A named section is a region landmark: screen readers list it with the
// header, main and footer. Sticky, so it's in every screenshot of a long page.
export function MockDataBanner() {
  return (
    <section aria-label="Mock data" className="sticky top-0 z-10 bg-ink text-white">
      <div className="mx-auto flex w-full max-w-5xl items-start gap-2 px-4 py-2 text-sm">
        <IconAlertTriangle aria-hidden size={18} className="mt-0.5 shrink-0" />
        <p>
          <strong>Mock data.</strong> Nothing on this page comes from the scoring service: every
          job, result and version is made up.
        </p>
      </div>
    </section>
  )
}

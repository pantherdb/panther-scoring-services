import { useLocation } from 'react-router'

import { service } from '@/app/services'
import { ComingSoonBadge } from '@/components/ComingSoonPage'

import { HmmscoreForm } from './HmmscoreForm'

// /hmmscore: one protein scored against PANTHER's HMM library.
export function HmmscorePage() {
  const { key } = useLocation()
  const { title, comingSoon } = service('hmmscore')
  return (
    <section className="flex flex-col gap-6">
      <div className="flex flex-col gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="text-lg font-semibold">{title}</h2>
          {comingSoon && <ComingSoonBadge />}
        </div>
        <p className="text-ink-muted">
          Scores one protein sequence against the PANTHER library of hidden Markov models, to find
          the family or subfamily it belongs to, with its E-value, bit score and alignment.
        </p>
      </div>
      {/* Until the API scores hmmscore, it answers every valid request with a 501. The flag the
          wiring turns off removes this notice too. */}
      {comingSoon && <NotAvailableNotice title={title} />}
      {/* Remounted on each visit, such as its tab clicked while it's open, so the form starts
          afresh: empty, or filled by "Edit and resubmit". */}
      <HmmscoreForm key={key} />
    </section>
  )
}

type Props = {
  title: string
}

function NotAvailableNotice({ title }: Props) {
  return (
    <p role="note" className="rounded-md bg-primary-50 px-3 py-2 text-sm text-primary-900">
      {title} isn’t available on this site yet, so a sequence submitted now won’t be scored. You can
      try the form in the meantime.
    </p>
  )
}

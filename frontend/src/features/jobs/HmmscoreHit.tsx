import { IconExternalLink } from '@tabler/icons-react'

import type { HmmscoreResult } from '@/app/api/wire'

import { AlignmentText } from './AlignmentText'

type Props = {
  result: HmmscoreResult
}

/** pantherdb.org's page for a family or subfamily, as the legacy site linked to it. */
export function familyUrl(pantherId: string) {
  return `https://www.pantherdb.org/panther/family.do?clsAccession=${encodeURIComponent(pantherId)}`
}

// An hmmscore job's result: the hit's PANTHER ID, linking to its family page, its name, and its
// E-value and bit score exactly as the API gives them, then the alignment. No threshold, label
// or relatedness mark: the legacy page's sentence about the cutoff stated it backwards.
export function HmmscoreHit({ result }: Props) {
  const { hit } = result
  if (hit === null) return <p className="italic">No hits to PANTHER for this sequence.</p>

  return (
    <section className="flex flex-col gap-4">
      <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1">
        <dt className="font-medium">PANTHER ID</dt>
        <dd>
          <a
            className="inline-flex items-center gap-1 font-mono text-primary-700 underline hover:no-underline"
            href={familyUrl(hit.panther_id)}
            target="_blank"
            rel="noopener noreferrer"
            aria-label={`${hit.panther_id} on pantherdb.org (opens in a new tab)`}
          >
            {hit.panther_id}
            <IconExternalLink size={14} aria-hidden="true" />
          </a>
        </dd>
        <dt className="font-medium">Name</dt>
        <dd className="break-words">{hit.name}</dd>
        <dt className="font-medium">E-value</dt>
        <dd className="font-mono">{hit.evalue}</dd>
        <dt className="font-medium">Bit score</dt>
        <dd className="font-mono">{hit.score}</dd>
      </dl>
      <AlignmentText alignment={hit.alignment} />
    </section>
  )
}

import { useLocation } from 'react-router'

import { RefmapForm } from './RefmapForm'

// /refmap: protein IDs mapped to PANTHER families and subfamilies, for one organism.
export function RefmapPage() {
  const { key } = useLocation()
  return (
    <section className="flex flex-col gap-6">
      <div className="flex flex-col gap-2">
        <h2 className="text-lg font-semibold">Protein ID mapping</h2>
        <p className="text-ink-muted">
          Maps each protein ID, such as a UniProt accession, to the PANTHER family or subfamily it
          belongs to in one organism’s reference proteome. You can take the mappings to an
          enrichment or overrepresentation analysis.
        </p>
      </div>
      {/* Remounted on each visit, such as its tab clicked while it's open, so the form starts
          afresh: empty, or filled by "Edit and resubmit". */}
      <RefmapForm key={key} />
    </section>
  )
}

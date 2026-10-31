import { RefmapForm } from './RefmapForm'

// /refmap: protein IDs mapped to PANTHER families and subfamilies, for one organism.
export function RefmapPage() {
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
      <RefmapForm />
    </section>
  )
}

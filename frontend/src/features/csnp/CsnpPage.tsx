import { CsnpForm } from './CsnpForm'

// /csnp: PANTHER-PSEP coding SNP scoring, one protein at a time.
export function CsnpPage() {
  return (
    <section className="flex flex-col gap-6">
      <div className="flex flex-col gap-2">
        <h2 className="text-lg font-semibold">Coding SNP impact scoring</h2>
        <p className="text-ink-muted">
          PANTHER-PSEP estimates how long the amino acid at each substituted position has been
          preserved in evolution, in millions of years, and from that the likelihood that the
          substitution has a functional impact on the protein.
        </p>
      </div>
      <CsnpForm />
    </section>
  )
}

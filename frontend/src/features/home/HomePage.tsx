import { Button } from '@mantine/core'
import { Link } from 'react-router'

import { StartToolsCheck } from '@/features/jobs'

export function HomePage() {
  return (
    <div className="flex flex-col gap-8">
      <section className="flex flex-col items-start gap-2">
        <h2 className="text-lg font-semibold">Coding SNP impact scoring</h2>
        <p className="text-ink-muted">
          Estimates how long an amino-acid position has been preserved in evolution, to predict
          whether a substitution there is likely to be damaging.
        </p>
        <Button component={Link} to="/csnp" className="mt-2">
          Score coding SNPs
        </Button>
      </section>
      <section className="flex flex-col items-start gap-2">
        <h2 className="text-lg font-semibold">Protein ID mapping</h2>
        <p className="text-ink-muted">
          Maps protein IDs, such as UniProt accessions, to their PANTHER families and subfamilies in
          one organism.
        </p>
        <Button component={Link} to="/refmap" className="mt-2">
          Map protein IDs
        </Button>
      </section>
      <StartToolsCheck />
    </div>
  )
}

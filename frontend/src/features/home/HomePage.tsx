// CI test: an unused variable, which ESLint rejects.
const unusedForCiTest = 1

export function HomePage() {
  return (
    <section className="flex flex-col gap-2">
      <h2 className="text-lg font-semibold">Coding SNP impact scoring</h2>
      <p className="text-ink-muted">
        Estimates how long an amino-acid position has been preserved in evolution, to predict
        whether a substitution there is likely to be damaging.
      </p>
    </section>
  )
}

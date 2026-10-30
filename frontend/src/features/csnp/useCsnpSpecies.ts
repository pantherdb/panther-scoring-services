import type { CsnpSpecies } from '@/app/api/wire'

import { useGetCsnpSpeciesQuery } from './speciesApi'

export type SpeciesList =
  | { status: 'loaded'; species: CsnpSpecies[]; codes: ReadonlySet<string> }
  | { status: 'loading' }
  | { status: 'failed'; retry: () => void }

/** The species sorted by name, for the selector: the API gives them in code order. */
export function byName(species: readonly CsnpSpecies[]): CsnpSpecies[] {
  return [...species].sort((a, b) => a.name.localeCompare(b.name, 'en'))
}

/**
 * The species list as the form needs it. "Loading" is any time there's no data and no
 * error, so a retry after a failure shows as loading too.
 */
export function useCsnpSpecies(): SpeciesList {
  const { data, isError, refetch } = useGetCsnpSpeciesQuery()

  if (data) {
    return {
      status: 'loaded',
      species: byName(data),
      codes: new Set(data.map(species => species.code)),
    }
  }
  if (isError) {
    return {
      status: 'failed',
      retry: () => {
        void refetch()
      },
    }
  }
  return { status: 'loading' }
}

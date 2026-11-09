import { type CodeList, codeListOf } from '@/components/codeList'

import { useGetCsnpSpeciesQuery } from './speciesApi'

/** The species list as the form needs it, sorted by name. */
export function useCsnpSpecies(): CodeList {
  const { data, isError, refetch } = useGetCsnpSpeciesQuery()
  return codeListOf({ data, isError, refetch })
}

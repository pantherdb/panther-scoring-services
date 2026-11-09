import { skipToken } from '@reduxjs/toolkit/query'

import { useGetRefmapOrganismsQuery } from '@/app/api/refmapOrganisms'

/**
 * An organism as the job page names it: "Endocarpon pusillum (ENDPU)" once the organism list
 * has loaded, as the form showed it; the code alone while it loads, if it can't be loaded, or
 * if the list doesn't have it. `null` for a job that names no organism: nothing is fetched.
 */
export function useOrganismLabel(code: string | null): string | null {
  const { data } = useGetRefmapOrganismsQuery(code === null ? skipToken : undefined)
  if (code === null) return null
  const name = data?.find(organism => organism.code === code)?.name
  return name === undefined ? code : `${name} (${code})`
}

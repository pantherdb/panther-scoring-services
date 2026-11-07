import { useGetRefmapOrganismsQuery } from '@/app/api/refmapOrganisms'

/**
 * An organism as the job page names it: "Endocarpon pusillum (ENDPU)" once the organism list
 * has loaded, as the form showed it; the code alone while it loads, if it can't be loaded, or
 * if the list doesn't have it.
 */
export function useOrganismLabel(code: string): string {
  const { data } = useGetRefmapOrganismsQuery()
  const name = data?.find(organism => organism.code === code)?.name
  return name === undefined ? code : `${name} (${code})`
}

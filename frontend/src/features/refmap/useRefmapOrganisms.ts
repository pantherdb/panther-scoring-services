import { useGetRefmapOrganismsQuery } from '@/app/api/refmapOrganisms'
import { type CodeList, codeListOf } from '@/components/codeList'

/** The organism list as the form needs it, sorted by name. */
export function useRefmapOrganisms(): CodeList {
  const { data, isError, refetch } = useGetRefmapOrganismsQuery()
  return codeListOf({ data, isError, refetch })
}

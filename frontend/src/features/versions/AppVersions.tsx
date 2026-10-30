import { useGetVersionsQuery } from './versionsApi'
import { VersionList } from './VersionList'

// The versions the service runs now, so a result can be traced to what produced it.
export function AppVersions() {
  const { data, isError } = useGetVersionsQuery()

  if (data) {
    return (
      <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
        <span className="font-semibold">Versions</span>
        <VersionList versions={data} />
      </div>
    )
  }
  // No status or error text: it could carry build details.
  if (isError) return <p>Versions are unavailable.</p>
  return <p>Loading versions…</p>
}

import type { Versions } from './versionsApi'

type Props = {
  versions: Versions
}

// The API, the engine, then each tool in the order the API reports them.
export function VersionList({ versions }: Props) {
  const entries = [
    { label: 'API', version: versions.api },
    { label: 'Engine', version: versions.engine },
    ...versions.tools.map(tool => ({ label: tool.name, version: tool.version })),
  ]

  return (
    <dl className="flex flex-wrap gap-x-4 gap-y-1">
      {entries.map(({ label, version }) => (
        <div key={label} className="flex gap-1">
          <dt className="font-medium">{label}</dt>
          <dd className={version === null ? 'italic' : undefined}>{version ?? 'not available'}</dd>
        </div>
      ))}
    </dl>
  )
}

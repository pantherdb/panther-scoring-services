import type { components } from '@/app/api/schema'

type Versions = components['schemas']['Versions']

type Props = {
  versions: Versions
}

// The API, the engine, each tool, then each service's data, in the order the API reports
// them. Shared by the footer (what the service runs now) and the job page (what a job ran
// with). A data version is the PANTHER release the API names, never one written here.
export function VersionList({ versions }: Props) {
  const entries = [
    { label: 'API', version: versions.api },
    { label: 'Engine', version: versions.engine },
    ...versions.tools.map(tool => ({ label: tool.name, version: tool.version })),
    ...versions.data.map(data => ({
      label: `${data.service} data`,
      version: `PANTHER ${data.panther}`,
    })),
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

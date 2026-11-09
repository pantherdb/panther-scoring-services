import type { components } from '@/app/api/schema'

type Versions = components['schemas']['Versions']

// The mocked GET /api/v1/versions body: the tool versions pinned in the API image,
// cSNP's frozen PANTHER 9 data and refmap's PANTHER 19. Also read by the @mock e2e
// spec, so keep this file free of runtime imports.
export const versions: Versions = {
  api: '0.1.0',
  engine: '0.1.0',
  tools: [
    { name: 'blastp', version: '2.17.0' },
    { name: 'hmmscan', version: '3.4' },
    { name: 'hmmsearch', version: '3.4' },
    { name: 'epa-ng', version: '0.3.8' },
  ],
  data: [
    { service: 'csnp', panther: '9' },
    { service: 'refmap', panther: '19' },
  ],
}

/** A job's versions, as the API gives them: the report's, with only its service's data. */
export function jobVersions(service: string): Versions {
  return { ...versions, data: versions.data.filter(data => data.service === service) }
}

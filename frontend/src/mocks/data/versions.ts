import type { components } from '@/app/api/schema'

// The mocked GET /api/v1/versions body: the tool versions pinned in the API image, and
// cSNP's frozen PANTHER 9 data. Also read by the @mock e2e spec, so keep this file free
// of runtime imports.
export const versions: components['schemas']['Versions'] = {
  api: '0.1.0',
  engine: '0.1.0',
  tools: [
    { name: 'blastp', version: '2.17.0' },
    { name: 'hmmscan', version: '3.4' },
    { name: 'hmmsearch', version: '3.4' },
    { name: 'epa-ng', version: '0.3.8' },
  ],
  data: [{ service: 'csnp', panther: '9' }],
}

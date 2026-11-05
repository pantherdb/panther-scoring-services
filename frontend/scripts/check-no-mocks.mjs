// Fails if a build in dist/ contains the API mocking library or the mock data banner, so a
// mocked build can't be published. MSW's worker and its start-up both name mockServiceWorker;
// not a bare "msw", which a minified name could be by chance. Run after `npm run build`, by the
// Pages workflow and by the Dockerfile: `npm run check:no-mocks`.
import { readdirSync, readFileSync } from 'node:fs'
import { join } from 'node:path'

const PATTERNS = [/mockServiceWorker/i, /mock data/i]
const dist = process.argv[2] ?? 'dist'

const found = readdirSync(dist, { recursive: true, withFileTypes: true })
  .filter(entry => entry.isFile())
  .map(entry => join(entry.parentPath, entry.name))
  .filter(path => {
    const text = readFileSync(path, 'latin1')
    return PATTERNS.some(pattern => pattern.test(text))
  })

if (found.length > 0) {
  console.error('The build contains the API mocking library or the mock data banner:')
  for (const path of found) console.error(`  ${path}`)
  process.exit(1)
}
console.log(`No mock data in ${dist}.`)

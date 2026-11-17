import type { components } from '../../app/api/schema'
import { jobVersions, versions } from './versions'

// Mocked job bodies, as the API sends them. Also read by the @mock e2e spec, so
// keep to type imports and relative imports.

type ToolsJob = components['schemas']['ToolsJob']
type CsnpJob = components['schemas']['CsnpJob']
type CsnpResult = components['schemas']['CsnpResult']
type RefmapJob = components['schemas']['RefmapJob']
type RefmapResult = components['schemas']['RefmapResult']
type HmmscoreJob = components['schemas']['HmmscoreJob']
type HmmscoreResult = components['schemas']['HmmscoreResult']
type JobStatus = components['schemas']['JobStatus']
type Problem = components['schemas']['Problem']

/** The tools job's result: each tool the versions mock reports. */
export const toolsResult: components['schemas']['ToolsResult'] = { tools: versions.tools }

/** A failed job's error, generic as the API makes it. */
export const jobError: Problem = {
  type: 'about:blank',
  title: 'Internal Server Error',
  status: 500,
  detail: 'The job hit an unexpected error and could not complete.',
}

/** The API's answer to an unknown, malformed or expired job id. */
export const jobNotFound: Problem = {
  type: 'about:blank',
  title: 'Not Found',
  status: 404,
  detail: 'There is no job with this id. A finished job expires after a time.',
}

// Fixed times, so the run time shown is predictable: the job runs for 1.5 s.
const CREATED_AT = '2026-10-29T12:00:00.000Z'
const STARTED_AT = '2026-10-29T12:00:00.020Z'
const FINISHED_AT = '2026-10-29T12:00:01.520Z'

// The times and error a job has in the given status, and its versions, with only its
// service's data, as the API gives them.
function jobFields(id: string, status: JobStatus, service: string) {
  const started = status !== 'queued'
  const finished = status === 'succeeded' || status === 'failed'
  return {
    id,
    status,
    created_at: CREATED_AT,
    started_at: started ? STARTED_AT : null,
    finished_at: finished ? FINISHED_AT : null,
    error: status === 'failed' ? jobError : null,
    versions: jobVersions(service),
  }
}

/** A tools job in the given status, with the fields that status has. */
export function toolsJob(id: string, status: JobStatus): ToolsJob {
  return {
    ...jobFields(id, status, 'tools'),
    service: 'tools',
    result: status === 'succeeded' ? toolsResult : null,
  }
}

/**
 * MOCK DATA, not a score. The engine produced none of it: the ages, messages and pDel
 * values are made up to exercise the results table, and PTHR00000 is no PANTHER family.
 * The substitutions are the example input's, so the mocked flow reads naturally.
 */
export const csnpResult: CsnpResult = {
  family: 'PTHR00000',
  scores: [
    { substitution: 'L46P', age: 400, message: 'probably damaging', pdel: '0.80' },
    { substitution: 'C130R', age: 300, message: 'possibly damaging', pdel: '0.50' },
    { substitution: 'R163C', age: 100, message: 'probably benign', pdel: '0.20' },
    {
      substitution: 'R176C',
      age: null,
      message: 'Not scored: Invalid substitution',
      pdel: null,
    },
  ],
}

/** A csnp job in the given status, with the mock result once it has succeeded. */
export function csnpJob(id: string, status: JobStatus): CsnpJob {
  return {
    ...jobFields(id, status, 'csnp'),
    service: 'csnp',
    result: status === 'succeeded' ? csnpResult : null,
  }
}

/**
 * The form's example, six IDs of ENDPU's own test list, mapped as the legacy `map_panther.pl`
 * mapped them (engine/tests/golden/refmap/out/test_geneList.out): three to subfamilies, two to
 * families, and one to no PANTHER ID. The mocks give these real answers for these IDs.
 */
export const EXAMPLE_MAPPINGS: Readonly<Record<string, string | null>> = {
  U1G4Q5: 'PTHR11360:SF130',
  U1GCA1: 'PTHR21058:SF0',
  U1HRR6: 'PTHR42765:SF2',
  U1GLV9: 'PTHR28011',
  U1GJ40: 'PTHR13401',
  U1HQ27: null,
}

// The PANTHER ID for one ID: the golden's for the example's IDs; otherwise made up from the
// sum of its character codes, so the same ID always gets the same answer, and about a third
// get none.
function mockPantherId(id: string): string | null {
  if (Object.hasOwn(EXAMPLE_MAPPINGS, id)) return EXAMPLE_MAPPINGS[id] ?? null
  let sum = 0
  for (let i = 0; i < id.length; i += 1) sum += id.charCodeAt(i)
  return sum % 3 === 0 ? null : `PTHR00000:SF${sum % 10}`
}

/**
 * MOCK DATA, not a mapping, except for the example's six IDs (EXAMPLE_MAPPINGS), whatever the
 * organism. For any other ID, no engine or classification file produced it: PTHR00000 is no
 * PANTHER family, and whether an ID maps is decided by its characters alone. One mapping per
 * ID, in order, repeats included, as the API returns them.
 */
export function refmapResult(ids: readonly string[], organism = 'ENDPU'): RefmapResult {
  return { organism, mappings: ids.map(id => ({ id, panther_id: mockPantherId(id) })) }
}

/** A refmap job in the given status, mapping `ids` against `organism` once it has succeeded. */
export function refmapJob(
  id: string,
  status: JobStatus,
  ids: readonly string[] = [],
  organism = 'ENDPU'
): RefmapJob {
  return {
    ...jobFields(id, status, 'refmap'),
    service: 'refmap',
    result: status === 'succeeded' ? refmapResult(ids, organism) : null,
  }
}

/** How wide each line of the mock alignment is: wider than a phone, so its box must scroll. */
export const MOCK_ALIGNMENT_WIDTH = 200

// `residues` over and over after `prefix`, cut to MOCK_ALIGNMENT_WIDTH.
function alignmentLine(prefix: string, residues: string) {
  const width = MOCK_ALIGNMENT_WIDTH
  return (prefix + residues.repeat(Math.ceil(width / residues.length))).slice(0, width)
}

// Columns in the shape of hmmsearch's domain annotation, each line MOCK_ALIGNMENT_WIDTH wide.
function mockAlignment() {
  const width = MOCK_ALIGNMENT_WIDTH
  return [
    'MOCK DATA: not an alignment. hmmsearch produced none of it.'.padEnd(width),
    '  == domain 1  score: 439.0 bits;  conditional E-value: 7e-131'.padEnd(width),
    alignmentLine('  PTHR00000:SF1    1 ', 'mkvlwaallvtflagcqakv'),
    alignmentLine('                     ', 'MKVLWAALLVTFLAGCQAKV'),
    alignmentLine('          query    1 ', 'MKVLWAALLVTFLAGCQAKV'),
    alignmentLine('                  PP ', '*'),
  ].join('\n')
}

/**
 * MOCK DATA, not a score. The engine produced none of it: PTHR00000:SF1 is no PANTHER family,
 * "MOCK FAMILY" no family's name, and the alignment says it's made up. Its lines are 200
 * characters, wider than a phone, so the page's alignment box has to scroll.
 */
export const hmmscoreResult: HmmscoreResult = {
  hit: {
    panther_id: 'PTHR00000:SF1',
    name: 'MOCK FAMILY',
    evalue: '7e-131',
    score: '439.0',
    alignment: mockAlignment(),
  },
}

/** An hmmscore job in the given status, with the mock hit once it has succeeded. */
export function hmmscoreJob(id: string, status: JobStatus): HmmscoreJob {
  return {
    ...jobFields(id, status, 'hmmscore'),
    service: 'hmmscore',
    result: status === 'succeeded' ? hmmscoreResult : null,
  }
}

import { Button } from '@mantine/core'
import { IconDownload } from '@tabler/icons-react'

import type { RefmapResult } from '@/app/api/wire'

import { MappingsTable } from './MappingsTable'
import { mappingsFileName, mappingsTsv, saveTextFile } from './mappingsFile'

type Props = {
  jobId: string
  result: RefmapResult
}

const number = new Intl.NumberFormat('en-US')

function plural(count: number, one: string, many: string) {
  return `${number.format(count)} ${count === 1 ? one : many}`
}

// A refmap job's result: how many IDs mapped, a download of every mapping, and the mappings
// a page at a time. Each PANTHER ID is shown exactly as the API gives it.
export function RefmapMappings({ jobId, result }: Props) {
  const { mappings } = result
  const mapped = mappings.reduce(
    (count, { panther_id }) => count + (panther_id === null ? 0 : 1),
    0
  )
  const unmapped = mappings.length - mapped

  function download() {
    saveTextFile(mappingsTsv(mappings), mappingsFileName(jobId), 'text/tab-separated-values')
  }

  return (
    <section className="flex flex-col gap-4">
      <div className="flex flex-col items-start gap-2">
        <p className="font-medium">
          {plural(mappings.length, 'ID', 'IDs')}: {plural(mapped, 'has', 'have')} a PANTHER ID,{' '}
          {plural(unmapped, 'has', 'have')} none.
        </p>
        <Button
          variant="default"
          leftSection={<IconDownload size={16} aria-hidden />}
          onClick={download}
          disabled={mappings.length === 0}
        >
          Download the mappings (TSV)
        </Button>
      </div>
      <MappingsTable mappings={mappings} />
    </section>
  )
}

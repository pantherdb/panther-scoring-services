import type { IdMapping } from '@/app/api/wire'

/**
 * The mappings as a tab-separated file: a header line, `id` and `panther_id`, then one line
 * per mapping, in the API's order, with an empty `panther_id` for an ID with none. IDs are
 * printable ASCII without whitespace (scoring-input), so neither column needs quoting. Lines
 * end in LF, and the file ends with one.
 */
export function mappingsTsv(mappings: readonly IdMapping[]): string {
  const lines = ['id\tpanther_id']
  for (const { id, panther_id } of mappings) lines.push(`${id}\t${panther_id ?? ''}`)
  return `${lines.join('\n')}\n`
}

/** The download's file name: the job's id, so two downloads don't overwrite each other. */
export function mappingsFileName(jobId: string): string {
  return `panther-id-mapping-${jobId}.tsv`
}

/**
 * Saves `text` as a file through the browser, built here: nothing is fetched. The object URL
 * is released once the download has started.
 */
export function saveTextFile(text: string, fileName: string, type: string) {
  const url = URL.createObjectURL(new Blob([text], { type }))
  const link = document.createElement('a')
  link.href = url
  link.download = fileName
  document.body.append(link)
  link.click()
  link.remove()
  setTimeout(() => URL.revokeObjectURL(url), 0)
}

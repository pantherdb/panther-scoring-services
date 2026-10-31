import { Button, FileButton, Textarea } from '@mantine/core'
import { useRef } from 'react'

import type { SplitIds } from './ids'

type Props = {
  value: string
  onChange: (text: string) => void
  /** A file the user chose to load into the box. */
  onFile: (file: File) => void | Promise<void>
  error: string | undefined
  /** The box's text as split, for the count. It may lag the text while a long list is typed. */
  split: SplitIds
}

const number = new Intl.NumberFormat('en-US')

function countOf({ ids, linesWithColumns }: SplitIds) {
  const count =
    ids.length === 0
      ? 'No IDs yet.'
      : `${number.format(ids.length)} ${ids.length === 1 ? 'ID' : 'IDs'} will be sent.`
  if (linesWithColumns === 0) return count
  const lines = `${number.format(linesWithColumns)} ${linesWithColumns === 1 ? 'line' : 'lines'}`
  return `${count} Only the first column was read on ${lines}: what follows a tab is left out.`
}

// The IDs: a box to paste them in, a button that loads a text file into the box, and how many
// IDs will be sent.
export function IdsField({ value, onChange, onFile, error, split }: Props) {
  // Clears the file input after each file, so choosing the same file again reads it again.
  const resetFile = useRef<() => void>(null)

  async function chosen(file: File | null) {
    if (file) await onFile(file)
    resetFile.current?.()
  }

  return (
    <div className="flex flex-col gap-2">
      <Textarea
        label="Protein IDs"
        description="Such as UniProt accessions: one per line, or separated by spaces or commas. Matched exactly as typed, so case matters. On a line with tabs, only the first column is read."
        rows={10}
        resize="vertical"
        spellCheck={false}
        autoCapitalize="off"
        classNames={{ input: 'font-mono' }}
        value={value}
        onChange={event => onChange(event.currentTarget.value)}
        error={error}
      />
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
        <FileButton
          onChange={file => void chosen(file)}
          accept=".txt,.tsv,.csv,.tab,text/plain,text/tab-separated-values,text/csv"
          resetRef={resetFile}
          inputProps={{ 'aria-label': 'Text file of protein IDs' }}
        >
          {props => (
            <Button variant="default" size="compact-sm" {...props}>
              Load IDs from a text file
            </Button>
          )}
        </FileButton>
        <p className="text-sm text-ink-muted">{countOf(split)}</p>
      </div>
    </div>
  )
}

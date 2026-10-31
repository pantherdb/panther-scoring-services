/** The IDs box's text, split into the request's list. */
export type SplitIds = {
  /** The IDs, in the order typed, each exactly as typed. */
  ids: string[]
  /** The line of the box each ID is on, counted from 1: `lines[i]` is the line of `ids[i]`. */
  lines: number[]
  /** How many lines had something after a tab, which was left out. */
  linesWithColumns: number
}

const LINE_BREAK = /\r\n|\r|\n/
// Whitespace, in JavaScript's sense, and commas. An ID can't hold whitespace (scoring-input),
// and a comma in a pasted list separates.
const SEPARATORS = /[\s,]+/

/**
 * Splits the IDs box into IDs. Each line is read up to its first tab, as the legacy service
 * read only a line's first column (REFMAP-5): the website's lists put an expression value in
 * a second, tab-separated column, which is never an ID. What's left of the line is split at
 * every run of whitespace and commas, so a line can hold several IDs, as cSNP's substitutions
 * box does. Empty pieces are dropped. IDs are kept as typed: the lookup is exact and
 * case-sensitive (REFMAP-1), so nothing is upper-cased or de-duplicated.
 */
export function splitIds(text: string): SplitIds {
  const ids: string[] = []
  const lines: number[] = []
  let linesWithColumns = 0
  const rows = text.split(LINE_BREAK)
  for (const [index, row] of rows.entries()) {
    const tab = row.indexOf('\t')
    const first = tab === -1 ? row : row.slice(0, tab)
    if (tab !== -1 && row.slice(tab + 1).trim() !== '') linesWithColumns += 1
    for (const id of first.split(SEPARATORS)) {
      if (id === '') continue
      ids.push(id)
      lines.push(index + 1)
    }
  }
  return { ids, lines, linesWithColumns }
}

/** How much of an ID a message shows. */
const SHOWN_LENGTH = 24
// Characters that would be invisible, or break the message's layout, if shown as typed.
// eslint-disable-next-line no-control-regex -- matching control characters is the point
const CONTROL = /[\u0000-\u001f\u007f-\u009f]/g

/**
 * An ID as a message shows it: as typed, cut short past SHOWN_LENGTH characters, with control
 * characters shown as U+FFFD so the user can see where they are.
 */
export function shownId(id: string): string {
  const visible = id.replace(CONTROL, '�')
  return visible.length > SHOWN_LENGTH ? `${visible.slice(0, SHOWN_LENGTH)}…` : visible
}

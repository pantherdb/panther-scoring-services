import type { DraftErrors, RefmapValues } from './draft'
import { shownId, type SplitIds } from './ids'

// The client's copy of scoring-input's refmap rules, so mistakes show before anything is
// sent. The API is the authority: it checks again, and its 422s are shown on the fields.
// If scoring-input changes a limit, change it here too. No message quotes the organism; an ID
// that breaks the rule is named, since it's the user's own text on their own screen and the
// API never echoes one.

/** IDs in one request ("a list of 1 to 100,000 identifiers"). */
export const MOST_IDS = 100_000
/** Characters per ID ("1 to 64 printable ASCII characters"). */
export const LONGEST_ID = 64

const ORGANISM = /^[A-Z0-9]{1,5}$/
// Printable ASCII, without space: "!" to "~".
const PRINTABLE = /^[!-~]+$/
// How many bad IDs one message names.
const MOST_NAMED = 10

const number = new Intl.NumberFormat('en-US')

/** Checks the organism, trimmed, as it will be sent. Only its shape: there's no list yet. */
export function checkOrganism(text: string): string[] {
  const organism = text.trim()
  if (organism === '') return ['Enter a UniProt species code, such as HUMAN.']
  if (!ORGANISM.test(organism)) {
    return ['Use a UniProt species code of 1 to 5 upper-case letters or digits, such as HUMAN.']
  }
  return []
}

function isId(id: string) {
  return id.length <= LONGEST_ID && PRINTABLE.test(id)
}

/**
 * Checks the IDs as split. A bad ID is named by its place in the list, counted from 1, its
 * line, and as typed; at most MOST_NAMED, then a count. One pass over the list, so 100,000
 * IDs take milliseconds.
 */
export function checkIds({ ids, lines }: SplitIds): string[] {
  if (ids.length === 0) return ['Enter at least one ID, such as P04217.']
  if (ids.length > MOST_IDS) {
    return [
      `Enter at most ${number.format(MOST_IDS)} IDs. This list has ${number.format(ids.length)}.`,
    ]
  }
  const named: string[] = []
  let bad = 0
  for (const [index, id] of ids.entries()) {
    if (isId(id)) continue
    bad += 1
    if (named.length < MOST_NAMED) {
      named.push(
        `${number.format(index + 1)} (${shownId(id)}, line ${number.format(lines[index] ?? 0)})`
      )
    }
  }
  if (bad === 0) return []
  const more = bad > MOST_NAMED ? `, and ${number.format(bad - MOST_NAMED)} more` : ''
  const which = bad === 1 ? 'ID' : 'IDs'
  return [
    `${which} ${named.join(', ')}${more}: each ID must be 1 to ${LONGEST_ID} printable ASCII characters, such as P04217.`,
  ]
}

/** Every field's errors; a field with none is left out. `split` is the IDs box, split. */
export function checkDraft(values: RefmapValues, split: SplitIds): DraftErrors['fields'] {
  const errors: DraftErrors['fields'] = {}
  const ids = checkIds(split)
  const organism = checkOrganism(values.organism)
  if (ids.length > 0) errors.ids = ids
  if (organism.length > 0) errors.organism = organism
  return errors
}

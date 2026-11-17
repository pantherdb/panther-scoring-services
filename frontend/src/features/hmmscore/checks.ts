import type { HMMSCORE_FIELDS } from '@/app/formFields'
import { checkSequence, HMMSCORE_SEQUENCE } from '@/components/sequence'

// The client's copy of scoring-input's hmmscore rules, so mistakes show before anything is sent.
// The rules are in components/sequence.ts, shared with cSNP's; the API checks again, and its 422s,
// such as a server's lower residue limit, are shown on the field.

export type HmmscoreField = (typeof HMMSCORE_FIELDS)[number]

/** The box's text, as typed. */
export type HmmscoreValues = Record<HmmscoreField, string>

/** The sequence's errors, if any. */
export function checkHmmscore(values: HmmscoreValues): string[] {
  return checkSequence(values.sequence, HMMSCORE_SEQUENCE)
}

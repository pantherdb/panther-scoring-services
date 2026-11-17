import { checkSequence, CSNP_SEQUENCE } from '@/components/sequence'

import { CSNP_FIELDS, type CsnpField, type CsnpValues, type DraftErrors } from './draft'
import { splitSubstitutions } from './substitutions'

// The client's copy of scoring-input's cSNP rules, so mistakes show before anything is
// sent. The API is the authority: it checks again, and its 422s are shown on the fields.
// Input limits, not scoring thresholds. If scoring-input changes one, change it here too.
// No message quotes the value it's about, except a malformed substitution: the user needs
// to see which token it is, and it's their own text on their own screen. The sequence's
// rules are shared with hmmscore, in components/sequence.ts.

/** Tokens ("a list of 1 to 1,000 tokens"). */
export const MOST_SUBSTITUTIONS = 1_000
/** Characters per token ("1 to 32 printable ASCII characters"). */
export const LONGEST_SUBSTITUTION = 32

const SPECIES = /^[A-Z0-9]{1,5}$/
// A substitution after upper-casing, the legacy CGI's own rule: residue, position, residue.
// The API rejects any other token (decided on PR #19, 2026-10-30).
const SUBSTITUTION = /^[A-Z][0-9]+[A-Z]$/
// How many malformed tokens one message names.
const MOST_NAMED = 10
// Printable ASCII, without space: "!" to "~".
const PRINTABLE = /^[!-~]+$/

const number = new Intl.NumberFormat('en-US')

/** Checks the tokens as split; a bad token is named by its place, counted from 1. */
export function checkSubstitutions(tokens: string[]): string[] {
  if (tokens.length === 0) return ['Enter at least one substitution, such as L46P.']
  if (tokens.length > MOST_SUBSTITUTIONS) {
    return [`Enter at most ${number.format(MOST_SUBSTITUTIONS)} substitutions.`]
  }
  const messages: string[] = []
  const tooLong = tokens.findIndex(token => token.length > LONGEST_SUBSTITUTION)
  if (tooLong !== -1) {
    messages.push(`Substitution ${tooLong + 1} is longer than ${LONGEST_SUBSTITUTION} characters.`)
  }
  const notPrintable = tokens.findIndex(token => !PRINTABLE.test(token))
  if (notPrintable !== -1) {
    messages.push(`Substitution ${notPrintable + 1} has a character that isn't printable ASCII.`)
  }
  // Only tokens short and printable enough to show back are checked for their form, and
  // named: the user's own text, which the API never echoes.
  const malformed = tokens
    .map((token, index) => ({ token, place: index + 1 }))
    .filter(
      ({ token }) =>
        token.length <= LONGEST_SUBSTITUTION &&
        PRINTABLE.test(token) &&
        !SUBSTITUTION.test(token.toUpperCase())
    )
  if (malformed.length > 0) {
    const named = malformed
      .slice(0, MOST_NAMED)
      .map(({ token, place }) => `${place} (${token})`)
      .join(', ')
    const more = malformed.length > MOST_NAMED ? `, and ${malformed.length - MOST_NAMED} more` : ''
    const which = malformed.length === 1 ? 'Substitution' : 'Substitutions'
    messages.push(
      `${which} ${named}${more}: use the form L46P, a residue, its position, a residue.`
    )
  }
  return messages
}

/**
 * Checks the species, trimmed, as it will be sent. `codes` is the API's species list, once it
 * has loaded: the same codes the API accepts. Without it, only the shape is checked here.
 */
export function checkSpecies(text: string, codes?: ReadonlySet<string>): string[] {
  const species = text.trim()
  if (species === '') return ['Enter a PANTHER species code, such as HUMAN.']
  if (!SPECIES.test(species)) {
    return ['Use a PANTHER species code of 1 to 5 upper-case letters or digits, such as HUMAN.']
  }
  if (codes && !codes.has(species)) return ['Choose a species from the list.']
  return []
}

/** Every field's errors; a field with none is left out. `codes` as for `checkSpecies`. */
export function checkDraft(values: CsnpValues, codes?: ReadonlySet<string>): DraftErrors['fields'] {
  const found: Record<CsnpField, string[]> = {
    sequence: checkSequence(values.sequence, CSNP_SEQUENCE),
    substitutions: checkSubstitutions(splitSubstitutions(values.substitutions)),
    species: checkSpecies(values.species, codes),
  }
  const errors: DraftErrors['fields'] = {}
  for (const field of CSNP_FIELDS) {
    if (found[field].length > 0) errors[field] = found[field]
  }
  return errors
}

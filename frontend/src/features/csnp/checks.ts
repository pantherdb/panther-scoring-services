import { CSNP_FIELDS, type CsnpField, type CsnpValues, type DraftErrors } from './draft'
import { splitSubstitutions } from './substitutions'

// The client's copy of scoring-input's cSNP rules, so mistakes show before anything is
// sent. The API is the authority: it checks again, and its 422s are shown on the fields.
// Input limits, not scoring thresholds. If scoring-input changes one, change it here too.
// No message quotes the value it's about, except a malformed substitution: the user needs
// to see which token it is, and it's their own text on their own screen.

/** Residues, after normalising ("rejected … longer than 50,000 residues"). */
export const LONGEST_SEQUENCE = 50_000
/** Characters as typed, before normalising ("longer than 1,000,000 characters"). */
export const LONGEST_RAW_SEQUENCE = 1_000_000
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
// The API's normalising steps, in its order: trim every character up to U+0020 (Java's
// trim()), then one header line at the very start, then Java's \s.
// eslint-disable-next-line no-control-regex -- matching control characters is the point: the API trims them
const TRIMMED = /^[\u0000- ]+|[\u0000- ]+$/g
const HEADER = /^>[^\n]*/
const WHITESPACE = /[ \t\n\v\f\r]+/g

const number = new Intl.NumberFormat('en-US')

export function checkSequence(text: string): string[] {
  if (text.length > LONGEST_RAW_SEQUENCE) {
    return [`The sequence is longer than ${number.format(LONGEST_RAW_SEQUENCE)} characters.`]
  }
  const trimmed = text.replace(TRIMMED, '')
  if ((trimmed.match(/>/g) ?? []).length > 1) {
    return [
      "The sequence has more than one '>', so it holds more than one sequence. Submit one protein.",
    ]
  }
  const residues = trimmed.replace(HEADER, '').replace(WHITESPACE, '')
  if (residues === '') return ['Enter a protein sequence: plain residues, or FASTA.']
  if (!PRINTABLE.test(residues)) {
    return [
      "The sequence has a character that isn't printable ASCII. Use one-letter residue codes.",
    ]
  }
  if (residues.length > LONGEST_SEQUENCE) {
    return [`The sequence has more than ${number.format(LONGEST_SEQUENCE)} residues.`]
  }
  return []
}

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

/** Checks the species box's text, trimmed, as it will be sent. */
export function checkSpecies(text: string): string[] {
  const species = text.trim()
  if (species === '') return ['Enter a PANTHER species code, such as HUMAN.']
  if (!SPECIES.test(species)) {
    return ['Use a PANTHER species code of 1 to 5 upper-case letters or digits, such as HUMAN.']
  }
  return []
}

/** Every field's errors; a field with none is left out. */
export function checkDraft(values: CsnpValues): DraftErrors['fields'] {
  const found: Record<CsnpField, string[]> = {
    sequence: checkSequence(values.sequence),
    substitutions: checkSubstitutions(splitSubstitutions(values.substitutions)),
    species: checkSpecies(values.species),
  }
  const errors: DraftErrors['fields'] = {}
  for (const field of CSNP_FIELDS) {
    if (found[field].length > 0) errors[field] = found[field]
  }
  return errors
}

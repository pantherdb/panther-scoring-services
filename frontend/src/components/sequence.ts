// The client's copy of scoring-input's rules for a protein sequence, as each service sets them,
// so mistakes show before anything is sent. The API is the authority: it checks again, and its
// 422s are shown on the field. Input limits, not scoring thresholds. If scoring-input changes
// one, change it here too. No message quotes the sequence.

/** Characters as typed, before normalising: every service's limit ("1,000,000 characters"). */
export const LONGEST_RAW_SEQUENCE = 1_000_000
/** cSNP's residues, after normalising ("longer than 50,000 residues"). */
export const CSNP_MOST_RESIDUES = 50_000
/**
 * hmmscore's residues, after normalising: the most the API's setting allows, set by the product
 * owner on 2026-11-12. A server may set fewer, and its 422 names them on the field.
 */
export const HMMSCORE_MOST_RESIDUES = 10_000

/** One service's rules for its sequence, after the normalising every service shares. */
export type SequenceRules = {
  /** The most residues. */
  mostResidues: number
  /** The whole sequence once normalised, before upper-casing. */
  characters: RegExp
  /** The message for a character `characters` doesn't allow. */
  notResidues: string
  /** The message for nothing left once the header and whitespace are removed. */
  noResidues: string
  /** Refuse a sequence with no letter, such as a lone `*`, with `noResidues`. */
  needsALetter: boolean
  /** A final `*` isn't counted as a residue, as `hmmscan` doesn't read it. */
  finalStopIsNoResidue: boolean
}

/** cSNP's rules: printable ASCII, up to 50,000 residues. */
export const CSNP_SEQUENCE: SequenceRules = {
  mostResidues: CSNP_MOST_RESIDUES,
  // Printable ASCII, without space: "!" to "~".
  characters: /^[!-~]+$/,
  notResidues:
    "The sequence has a character that isn't printable ASCII. Use one-letter residue codes.",
  noResidues: 'Enter a protein sequence: plain residues, or FASTA.',
  needsALetter: false,
  finalStopIsNoResidue: false,
}

/**
 * hmmscore's rules: the letters A to Z in either case, an ASCII class since the API refuses
 * `Ä`, and `.`, `_`, `~` and `*` anywhere, with at least one letter (add-hmmscore-job, decision
 * 3, as narrowed on #76). Every character but a final `*` is a residue.
 */
export const HMMSCORE_SEQUENCE: SequenceRules = {
  mostResidues: HMMSCORE_MOST_RESIDUES,
  characters: /^[A-Za-z._~*]+$/,
  notResidues:
    'The sequence must be one-letter residue codes, the letters A to Z, and may also hold . _ ~ and *. Remove any -, digit, other punctuation or other character.',
  noResidues: 'The sequence has no residues. Enter a protein sequence: plain residues, or FASTA.',
  needsALetter: true,
  finalStopIsNoResidue: true,
}

// The API's normalising steps, in its order: trim every character up to U+0020 (Java's
// trim()), then one header line at the very start, then Java's \s.
// eslint-disable-next-line no-control-regex -- matching control characters is the point: the API trims them
const TRIMMED = /^[\u0000- ]+|[\u0000- ]+$/g
const HEADER = /^>[^\n]*/
const WHITESPACE = /[ \t\n\v\f\r]+/g
const LETTER = /[A-Za-z]/

const number = new Intl.NumberFormat('en-US')

/** The sequence's problems under a service's rules, in the API's order: at most one. */
export function checkSequence(text: string, rules: SequenceRules): string[] {
  if (text.length > LONGEST_RAW_SEQUENCE) {
    return [`The sequence is longer than ${number.format(LONGEST_RAW_SEQUENCE)} characters.`]
  }
  const trimmed = text.replace(TRIMMED, '')
  if ((trimmed.match(/>/g) ?? []).length > 1) {
    return [
      "The sequence has more than one '>', so it holds more than one sequence. Submit one protein.",
    ]
  }
  const normalised = trimmed.replace(HEADER, '').replace(WHITESPACE, '')
  if (normalised === '') return [rules.noResidues]
  if (!rules.characters.test(normalised)) return [rules.notResidues]
  // After the characters, so a refused character gets its own message wherever it is.
  if (rules.needsALetter && !LETTER.test(normalised)) return [rules.noResidues]
  const residues =
    rules.finalStopIsNoResidue && normalised.endsWith('*')
      ? normalised.length - 1
      : normalised.length
  if (residues > rules.mostResidues) {
    return [`The sequence has more than ${number.format(rules.mostResidues)} residues.`]
  }
  return []
}

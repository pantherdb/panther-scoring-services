/**
 * The substitutions box's text as the request's list: split at every run of whitespace,
 * in the order typed, with no empty token. As the legacy website did, nothing else
 * separates tokens, so `L46P,C130R` is one. Tokens are sent as typed: the API upper-cases
 * them, and decides which can be scored.
 */
export function splitSubstitutions(text: string): string[] {
  return text.split(/\s+/).filter(token => token !== '')
}

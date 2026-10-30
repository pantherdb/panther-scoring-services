/**
 * The substitutions box's text as the request's list: split at every run of whitespace and
 * commas, in any mix, in the order typed, with no empty token. A comma can't be part of a
 * substitution, so `L46P,C130R` is two. Nothing else separates tokens: `L46P;C130R` is one,
 * which the checks reject. Tokens are sent as typed: the API upper-cases them, and decides
 * which can be scored.
 */
export function splitSubstitutions(text: string): string[] {
  return text.split(/[\s,]+/).filter(token => token !== '')
}

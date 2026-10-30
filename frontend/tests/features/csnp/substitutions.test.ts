import { describe, expect, it } from 'vitest'

import { splitSubstitutions } from '@/features/csnp/substitutions'

describe('splitSubstitutions', () => {
  it('splits at every run of spaces, tabs and new lines, in the order typed', () => {
    expect(splitSubstitutions(' L46P  C130R\tR163C\r\nR176C\n')).toEqual([
      'L46P',
      'C130R',
      'R163C',
      'R176C',
    ])
  })

  it('keeps a single token', () => {
    expect(splitSubstitutions('L46P')).toEqual(['L46P'])
  })

  it('keeps other separators, such as commas, as part of a token', () => {
    expect(splitSubstitutions('L46P,C130R')).toEqual(['L46P,C130R'])
    expect(splitSubstitutions('L46P, C130R;R163C')).toEqual(['L46P,', 'C130R;R163C'])
  })

  it('keeps tokens as typed: not upper-cased, not checked, duplicates kept', () => {
    expect(splitSubstitutions('c130r XYZ G129 c130r')).toEqual(['c130r', 'XYZ', 'G129', 'c130r'])
  })

  it.each(['', '   ', '\n\t\r\n'])('gives no token for empty or blank text (%j)', text => {
    expect(splitSubstitutions(text)).toEqual([])
  })
})

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

  it('splits at a comma', () => {
    expect(splitSubstitutions('L46P,C130R')).toEqual(['L46P', 'C130R'])
  })

  it('splits at commas and whitespace in any mix, dropping empty pieces', () => {
    expect(splitSubstitutions('L46P, C130R,,R163C\n')).toEqual(['L46P', 'C130R', 'R163C'])
  })

  it.each([
    ['repeated commas', 'L46P,,,C130R'],
    ['a trailing comma', 'L46P,C130R,'],
    ['a leading comma', ',L46P,C130R'],
    ['commas with spaces', 'L46P , C130R'],
    ['a comma and a tab', 'L46P,\tC130R'],
    ['a comma at the end of a line', 'L46P,\r\nC130R'],
  ])('splits with %s', (_name, text) => {
    expect(splitSubstitutions(text)).toEqual(['L46P', 'C130R'])
  })

  it.each([';', '|', '+', '.', '/'])('keeps other separators, such as %j, in a token', sep => {
    expect(splitSubstitutions(`L46P${sep}C130R`)).toEqual([`L46P${sep}C130R`])
  })

  it('keeps tokens as typed: not upper-cased, not checked, duplicates kept', () => {
    expect(splitSubstitutions('c130r XYZ G129 c130r')).toEqual(['c130r', 'XYZ', 'G129', 'c130r'])
  })

  it.each(['', '   ', '\n\t\r\n', ',', ' , ,, \n'])(
    'gives no token for empty or blank text (%j)',
    text => {
      expect(splitSubstitutions(text)).toEqual([])
    }
  )
})

import { describe, expect, it } from 'vitest'

import {
  checkDraft,
  checkSequence,
  checkSpecies,
  checkSubstitutions,
  LONGEST_RAW_SEQUENCE,
  LONGEST_SEQUENCE,
  LONGEST_SUBSTITUTION,
  MOST_SUBSTITUTIONS,
} from '@/features/csnp/checks'

// `residues` residues as FASTA: a header, then lines of 60.
function fasta(residues: number, header = '>sp|P02649|APOE_HUMAN Apolipoprotein E') {
  const sequence = 'MKVLWAALLV'.repeat(Math.ceil(residues / 10)).slice(0, residues)
  const lines = sequence.match(/.{1,60}/g) ?? []
  return `${header}\n${lines.join('\n')}\n`
}

function tokens(count: number) {
  return Array.from({ length: count }, (_, i) => `L${i + 1}P`)
}

describe('the limits mirror scoring-input', () => {
  it('has the API’s numbers', () => {
    expect([
      LONGEST_SEQUENCE,
      LONGEST_RAW_SEQUENCE,
      MOST_SUBSTITUTIONS,
      LONGEST_SUBSTITUTION,
    ]).toEqual([50_000, 1_000_000, 1_000, 32])
  })
})

describe('checkSequence', () => {
  it.each([
    ['plain residues', 'MKVLWAALLV'],
    ['FASTA with one header and line breaks', '>sp|P02649|APOE_HUMAN\nMKVLWAALLV\nTFLAGCQAKV\n'],
    ['lower case and spaces', '  mkvl waal\r\n'],
    ['the longest sequence, as FASTA', fasta(LONGEST_SEQUENCE)],
    ['characters BLAST may refuse, which the API leaves to the engine', 'MKV*X-L'],
  ])('accepts %s', (_name, sequence) => {
    expect(checkSequence(sequence)).toEqual([])
  })

  it.each([
    ['nothing', ''],
    ['only whitespace', ' \n\t '],
    ['only a header', '>only a header'],
    ['only a header and blank lines', '>only a header\n\n  \n'],
  ])('rejects %s: there are no residues', (_name, sequence) => {
    expect(checkSequence(sequence)).toHaveLength(1)
  })

  it('rejects two sequences', () => {
    expect(checkSequence('>one\nMKV\n>two\nMKV')).toEqual([
      expect.stringMatching(/more than one sequence/i),
    ])
  })

  it('rejects a ">" after the residues, as the API does', () => {
    expect(checkSequence('>one\nMKV>L')).toHaveLength(1)
  })

  it('rejects one residue more than the longest', () => {
    expect(checkSequence(fasta(LONGEST_SEQUENCE + 1))).toEqual([
      expect.stringMatching(/50,000 residues/),
    ])
  })

  it.each([
    ['a letter outside ASCII', 'MKVÄL'],
    ['a control character inside it', 'MKV\u0000L'],
    ['a non-breaking space', 'MKV L'],
  ])('rejects %s', (_name, sequence) => {
    expect(checkSequence(sequence)).toEqual([expect.stringMatching(/printable ASCII/)])
  })

  it('rejects more characters than the API takes before normalising', () => {
    const padded = `MKV${' '.repeat(LONGEST_RAW_SEQUENCE)}`
    expect(checkSequence(padded)).toEqual([expect.stringMatching(/1,000,000 characters/)])
    expect(checkSequence(`MKV${' '.repeat(LONGEST_RAW_SEQUENCE - 3)}`)).toEqual([])
  })

  it('never quotes the sequence', () => {
    for (const sequence of ['>QWERTY\nMKV\n>QWERTY\nMKV', 'QWERTYÄ']) {
      expect(checkSequence(sequence).join(' ')).not.toContain('QWERTY')
    }
  })
})

describe('checkSubstitutions', () => {
  it.each([
    ['one token', ['L46P']],
    ['a position past the end, which the result reports, not the form', ['G99999R']],
    ['lower case, which the API upper-cases', ['c130r', 'l46P']],
    ['the most tokens', tokens(MOST_SUBSTITUTIONS)],
    ['the longest token', [`L${'1'.repeat(LONGEST_SUBSTITUTION - 2)}P`]],
  ])('accepts %s', (_name, list) => {
    expect(checkSubstitutions(list)).toEqual([])
  })

  it.each([
    ['letters only', 'XYZ'],
    ['no second residue', 'G129'],
    ['no position', 'GR'],
    ['a pipe', 'G12|'],
    ['a stop sign', 'A10*'],
    ['a trailing comma', 'L46P,'],
    ['two joined by a comma', 'L46P,C130R'],
    ['a digit first', '4L6P'],
  ])('rejects a token that is not a substitution: %s', (_name, token) => {
    expect(checkSubstitutions(['L46P', token])).toEqual([
      expect.stringMatching(/^substitution 2 /i),
    ])
  })

  it('names every malformed token by its place and as typed, so the user can find it', () => {
    const [message] = checkSubstitutions(['L46P', 'XYZ', 'C130R', 'g129', 'A10*'])

    expect(message).toMatch(/^substitutions /i)
    expect(message).toContain('2 (XYZ)')
    expect(message).toContain('4 (g129)')
    expect(message).toContain('5 (A10*)')
    expect(message).not.toMatch(/L46P \(|C130R/)
  })

  it('names at most ten malformed tokens, and counts the rest', () => {
    const [message] = checkSubstitutions(Array.from({ length: 12 }, (_, i) => `X${i}`))

    expect(message).toContain('10 (X9)')
    expect(message).not.toContain('(X10)')
    expect(message).toMatch(/2 more/)
  })

  it('rejects no tokens', () => {
    expect(checkSubstitutions([])).toEqual([expect.stringMatching(/at least one/i)])
  })

  it('rejects one token more than the most', () => {
    expect(checkSubstitutions(tokens(MOST_SUBSTITUTIONS + 1))).toEqual([
      expect.stringMatching(/1,000/),
    ])
  })

  it('rejects a token one character longer than the longest, naming its place', () => {
    const long = 'L'.padEnd(LONGEST_SUBSTITUTION + 1, '1')
    expect(checkSubstitutions(['L46P', 'C130R', long])).toEqual([
      expect.stringMatching(/substitution 3 .*32 characters/i),
    ])
  })

  it('rejects a token with a character outside printable ASCII, naming its place', () => {
    expect(checkSubstitutions(['L46Ä'])).toEqual([
      expect.stringMatching(/substitution 1 .*printable ASCII/i),
    ])
  })

  it('never quotes a token that is too long or not printable ASCII', () => {
    const messages = checkSubstitutions(['QWERTY'.padEnd(40, 'Y'), 'QWERTYÄ']).join(' ')
    expect(messages).not.toContain('QWERTY')
  })
})

describe('checkSpecies', () => {
  it.each(['HUMAN', 'RAT', 'PLAF7', 'A', ' HUMAN ', 'HUMAN\n'])('accepts %j', species => {
    expect(checkSpecies(species)).toEqual([])
  })

  it.each(['', '  ', 'human', 'HUMAN; rm -rf /', 'HOMOSAPIENS', 'HU MAN', 'HÜMAN'])(
    'rejects %j',
    species => {
      expect(checkSpecies(species)).toHaveLength(1)
    }
  )

  it('never quotes the species', () => {
    expect(checkSpecies('qwerty').join(' ')).not.toMatch(/qwerty/i)
  })

  describe('with the species list', () => {
    const codes = new Set(['HUMAN', 'MOUSE', 'PLAF7'])

    it.each(['HUMAN', ' MOUSE ', 'PLAF7'])('accepts %j, in the list', species => {
      expect(checkSpecies(species, codes)).toEqual([])
    })

    it('rejects a code of the right shape that is not in the list, without quoting it', () => {
      const messages = checkSpecies('ZZZZZ', codes)

      expect(messages).toEqual([expect.stringMatching(/from the list/i)])
      expect(messages.join(' ')).not.toContain('ZZZZZ')
    })

    it('checks the shape first, with one message', () => {
      expect(checkSpecies('human', codes)).toEqual([expect.stringMatching(/upper-case/i)])
    })
  })
})

describe('checkDraft', () => {
  it('finds nothing wrong with a valid draft', () => {
    expect(
      checkDraft({
        sequence: fasta(LONGEST_SEQUENCE),
        substitutions: 'L46P c130r G99999R',
        species: 'PLAF7',
      })
    ).toEqual({})
  })

  it('reports each field that breaks a rule, and only those', () => {
    expect(checkDraft({ sequence: '', substitutions: ' \n', species: '' })).toEqual({
      sequence: [expect.any(String)],
      substitutions: [expect.any(String)],
      species: [expect.any(String)],
    })
    expect(checkDraft({ sequence: 'MKV', substitutions: 'L2P', species: 'human' })).toEqual({
      species: [expect.any(String)],
    })
  })

  it('checks the species against the list when it is given, and only its shape when not', () => {
    const draft = { sequence: 'MKV', substitutions: 'L2P', species: 'ZZZZZ' }

    expect(checkDraft(draft, new Set(['HUMAN']))).toEqual({ species: [expect.any(String)] })
    expect(checkDraft(draft)).toEqual({})
  })

  it('checks the substitutions as they are split', () => {
    expect(
      checkDraft({
        sequence: 'MKV',
        substitutions: tokens(MOST_SUBSTITUTIONS + 1).join('\n'),
        species: 'HUMAN',
      })
    ).toEqual({ substitutions: [expect.stringMatching(/1,000/)] })
  })
})

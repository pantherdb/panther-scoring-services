import { describe, expect, it } from 'vitest'

import {
  checkSequence,
  CSNP_MOST_RESIDUES,
  CSNP_SEQUENCE,
  HMMSCORE_MOST_RESIDUES,
  HMMSCORE_SEQUENCE,
  LONGEST_RAW_SEQUENCE,
} from '@/components/sequence'

// `residues` residues as FASTA: a header, then lines of 60.
function fasta(residues: number, header = '>sp|P02649|APOE_HUMAN Apolipoprotein E') {
  const sequence = 'MKVLWAALLV'.repeat(Math.ceil(residues / 10)).slice(0, residues)
  const lines = sequence.match(/.{1,60}/g) ?? []
  return `${header}\n${lines.join('\n')}\n`
}

describe('the limits mirror scoring-input', () => {
  it('has the API’s numbers', () => {
    expect([LONGEST_RAW_SEQUENCE, CSNP_MOST_RESIDUES, HMMSCORE_MOST_RESIDUES]).toEqual([
      1_000_000, 50_000, 10_000,
    ])
  })
})

describe('checkSequence with cSNP’s rules', () => {
  const check = (sequence: string) => checkSequence(sequence, CSNP_SEQUENCE)

  it.each([
    ['plain residues', 'MKVLWAALLV'],
    ['FASTA with one header and line breaks', '>sp|P02649|APOE_HUMAN\nMKVLWAALLV\nTFLAGCQAKV\n'],
    ['lower case and spaces', '  mkvl waal\r\n'],
    ['the longest sequence, as FASTA', fasta(CSNP_MOST_RESIDUES)],
    ['characters BLAST may refuse, which the API leaves to the engine', 'MKV*X-L'],
  ])('accepts %s', (_name, sequence) => {
    expect(check(sequence)).toEqual([])
  })

  it.each([
    ['nothing', ''],
    ['only whitespace', ' \n\t '],
    ['only a header', '>only a header'],
    ['only a header and blank lines', '>only a header\n\n  \n'],
  ])('rejects %s: there are no residues', (_name, sequence) => {
    expect(check(sequence)).toHaveLength(1)
  })

  it('rejects two sequences', () => {
    expect(check('>one\nMKV\n>two\nMKV')).toEqual([
      expect.stringMatching(/more than one sequence/i),
    ])
  })

  it('rejects a ">" after the residues, as the API does', () => {
    expect(check('>one\nMKV>L')).toHaveLength(1)
  })

  it('rejects one residue more than the longest', () => {
    expect(check(fasta(CSNP_MOST_RESIDUES + 1))).toEqual([expect.stringMatching(/50,000 residues/)])
  })

  it('counts a final "*" as a residue', () => {
    expect(check(`${'M'.repeat(CSNP_MOST_RESIDUES)}*`)).toEqual([
      expect.stringMatching(/50,000 residues/),
    ])
  })

  it.each([
    ['a letter outside ASCII', 'MKVÄL'],
    ['a control character inside it', 'MKV\u0000L'],
    ['a non-breaking space', 'MKV L'],
  ])('rejects %s', (_name, sequence) => {
    expect(check(sequence)).toEqual([expect.stringMatching(/printable ASCII/)])
  })

  it('rejects more characters than the API takes before normalising', () => {
    const padded = `MKV${' '.repeat(LONGEST_RAW_SEQUENCE)}`
    expect(check(padded)).toEqual([expect.stringMatching(/1,000,000 characters/)])
    expect(check(`MKV${' '.repeat(LONGEST_RAW_SEQUENCE - 3)}`)).toEqual([])
  })

  it('never quotes the sequence', () => {
    for (const sequence of ['>QWERTY\nMKV\n>QWERTY\nMKV', 'QWERTYÄ']) {
      expect(check(sequence).join(' ')).not.toContain('QWERTY')
    }
  })
})

describe('checkSequence with hmmscore’s rules', () => {
  const check = (sequence: string) => checkSequence(sequence, HMMSCORE_SEQUENCE)
  const letters = (count: number) => 'MKVLWAALLV'.repeat(Math.ceil(count / 10)).slice(0, count)

  it.each([
    ['plain residues', 'MKVLWAALLV'],
    ['FASTA with one header and line breaks', '>sp|P02649|APOE_HUMAN\nmkvl waal\n'],
    ['the uncommon letters and a final stop, in lower case', 'mkvbjouxz*\n'],
    ['an inner stop', 'MKV*L'],
    ['a dot', 'MKV.L'],
    ['an underscore', 'MKV_L'],
    ['a tilde', 'MKV~L'],
    ['two final stops', 'MKVL**'],
    ['a header after a blank line', '\n  >sp|P02649|APOE_HUMAN\nMKVLWAALLV\n'],
  ])('accepts %s', (_name, sequence) => {
    expect(check(sequence)).toEqual([])
  })

  it.each([
    ['nothing', ''],
    ['only a header', '>only a header'],
    ['a header and a lone stop', '>only a header\n*'],
    ['a lone stop', '*'],
    ['a dot and a tilde', '.~'],
    ['a lone underscore', '_'],
  ])('rejects %s: there are no residues', (_name, sequence) => {
    expect(check(sequence)).toEqual([expect.stringMatching(/has no residues/i)])
  })

  it('rejects two sequences', () => {
    expect(check('>one\nMKV\n>two\nMKV')).toEqual([
      expect.stringMatching(/more than one sequence/i),
    ])
  })

  it.each([
    ['a digit', 'MKV1L'],
    ['a dash', 'MKV-L'],
    ['a plus', 'MKV+L'],
    ['a ">" inside it', 'MKV>LW'],
    ['a letter outside ASCII', 'MKVÄL'],
    ['a control character inside it', 'MKV\u0000L'],
    ['a dash beside no letter', '-*'],
  ])('rejects %s, saying which characters it may hold', (_name, sequence) => {
    expect(check(sequence)).toEqual([expect.stringMatching(/letters A to Z.*\. _ ~ and \*/)])
  })

  it('accepts 10,000 residues, and rejects one more', () => {
    expect(check(letters(HMMSCORE_MOST_RESIDUES))).toEqual([])
    expect(check(letters(HMMSCORE_MOST_RESIDUES + 1))).toEqual([
      expect.stringMatching(/more than 10,000 residues/),
    ])
  })

  it('counts a dot, a tilde and an inner stop as residues', () => {
    expect(check(`${letters(HMMSCORE_MOST_RESIDUES - 3)}.*~`)).toEqual([])
    expect(check(`${letters(HMMSCORE_MOST_RESIDUES - 2)}.*~`)).toEqual([
      expect.stringMatching(/more than 10,000 residues/),
    ])
  })

  it('leaves a final stop out of the count, but not a second one', () => {
    expect(check(`${letters(HMMSCORE_MOST_RESIDUES)}*`)).toEqual([])
    expect(check(`${letters(HMMSCORE_MOST_RESIDUES)}**`)).toEqual([
      expect.stringMatching(/more than 10,000 residues/),
    ])
  })

  it('rejects more characters than the API takes before normalising', () => {
    expect(check(`M${' '.repeat(LONGEST_RAW_SEQUENCE)}`)).toEqual([
      expect.stringMatching(/1,000,000 characters/),
    ])
    expect(check(`M${' '.repeat(LONGEST_RAW_SEQUENCE - 1)}`)).toEqual([])
  })

  it('never quotes the sequence', () => {
    for (const sequence of ['>QWERTY\nMKV\n>QWERTY\nMKV', 'QWERTY1', `${letters(10_001)}QWERTY`]) {
      expect(check(sequence).join(' ')).not.toContain('QWERTY')
    }
  })
})

import { describe, expect, it } from 'vitest'

import { checkDraft, checkIds, checkOrganism, LONGEST_ID, MOST_IDS } from '@/features/refmap/checks'
import { splitIds } from '@/features/refmap/ids'

function idsOf(count: number) {
  return Array.from({ length: count }, (_, i) => `P${i}`)
}

function check(ids: string[]) {
  return checkIds({ ids, lines: ids.map((_, i) => i + 1), linesWithColumns: 0 })
}

describe('checkOrganism', () => {
  it.each(['HUMAN', 'ECOLI', '9BACT', 'A', ' MOUSE '])('accepts %j', organism => {
    expect(checkOrganism(organism)).toEqual([])
  })

  it('asks for a code when there is none', () => {
    expect(checkOrganism('  ')).toEqual([expect.stringMatching(/species code/i)])
  })

  it.each(['human', '../../etc/passwd', 'HUMAN|', 'Homo_sapiens_HUMAN', 'HOMOSAP', 'HU MAN'])(
    'refuses %j without quoting it',
    organism => {
      const messages = checkOrganism(organism)
      expect(messages).toEqual([expect.stringMatching(/1 to 5 upper-case letters or digits/)])
      expect(messages[0]).not.toContain(organism.trim())
    }
  )
})

describe('checkIds', () => {
  it('accepts one ID, and exactly the most IDs', () => {
    expect(check(['P04217'])).toEqual([])
    expect(check(idsOf(MOST_IDS))).toEqual([])
  })

  it('asks for at least one ID', () => {
    expect(check([])).toEqual([expect.stringMatching(/at least one id/i)])
  })

  it('refuses one ID more than the most, saying how many there are', () => {
    expect(check(idsOf(MOST_IDS + 1))).toEqual([
      expect.stringMatching(/at most 100,000 IDs\. This list has 100,001\./),
    ])
  })

  it('accepts IDs of 64 printable ASCII characters, in any case and with punctuation', () => {
    expect(check(['A'.repeat(LONGEST_ID), 'p04217', 'P04217-2', 'a|b;c+d', '!~'])).toEqual([])
  })

  it('names an ID that is too long by place, line and as typed, cut short', () => {
    const messages = checkIds(splitIds(`P04217\n\n${'A'.repeat(LONGEST_ID + 1)}`))

    expect(messages).toEqual([
      `ID 2 (${'A'.repeat(24)}…, line 3): each ID must be 1 to 64 printable ASCII characters, such as P04217.`,
    ])
  })

  it('names IDs that are not printable ASCII', () => {
    const messages = checkIds(splitIds('P0é4217 P04217 P0\u00004217'))

    expect(messages).toEqual([
      expect.stringMatching(/^IDs 1 \(P0é4217, line 1\), 3 \(P0�4217, line 1\):/),
    ])
  })

  it('names at most ten bad IDs, then counts the rest', () => {
    const ids = ['P04217', ...Array.from({ length: 13 }, (_, i) => `é${i}`)]

    const [message] = check(ids)

    expect(message).toMatch(
      /^IDs 2 \(é0, line 2\), 3 \(é1, line 3\), .*11 \(é9, line 11\), and 3 more:/
    )
    expect(message).not.toContain('é10')
  })

  it('checks 100,000 IDs quickly, even when every one is bad', () => {
    const good = idsOf(MOST_IDS)
    const bad = good.map(id => `${id}é`)

    const start = performance.now()
    expect(check(good)).toEqual([])
    expect(check(bad)).toEqual([expect.stringMatching(/and 99,990 more/)])
    expect(performance.now() - start).toBeLessThan(500)
  })
})

describe('checkDraft', () => {
  it('finds nothing wrong with a valid draft', () => {
    const values = { ids: 'P04217\nP01023', organism: 'HUMAN' }

    expect(checkDraft(values, splitIds(values.ids))).toEqual({})
  })

  it('puts each broken rule on its field', () => {
    const values = { ids: ' ', organism: 'human' }

    expect(checkDraft(values, splitIds(values.ids))).toEqual({
      ids: [expect.stringMatching(/at least one id/i)],
      organism: [expect.stringMatching(/upper-case/)],
    })
  })
})

import { describe, expect, it } from 'vitest'

import { shownId, splitIds } from '@/features/refmap/ids'

describe('splitIds', () => {
  it('takes one ID per line, with LF, CRLF or CR line breaks', () => {
    expect(splitIds('P04217\nP01023\r\nP02649\rP04637')).toEqual({
      ids: ['P04217', 'P01023', 'P02649', 'P04637'],
      lines: [1, 2, 3, 4],
      linesWithColumns: 0,
    })
  })

  it('splits a line at spaces and commas, in any mix, and drops empty pieces and lines', () => {
    expect(splitIds('  P04217,P01023 ,, P02649\n\n \n P04637  \n')).toEqual({
      ids: ['P04217', 'P01023', 'P02649', 'P04637'],
      lines: [1, 1, 1, 4],
      linesWithColumns: 0,
    })
  })

  it('reads only the first column of a line with tabs, as the legacy did, and counts those lines', () => {
    expect(splitIds('P04217\t1.5\nP01023\nP02649\t0.2\tnote\nP04637\t\n')).toEqual({
      ids: ['P04217', 'P01023', 'P02649', 'P04637'],
      lines: [1, 2, 3, 4],
      // P04637's tab has nothing after it, so nothing was left out.
      linesWithColumns: 2,
    })
  })

  it('reads several IDs before the first tab', () => {
    expect(splitIds('P04217 P01023\t1.5').ids).toEqual(['P04217', 'P01023'])
  })

  it('keeps IDs exactly as typed: case, repeats, isoforms, versions and punctuation', () => {
    expect(splitIds('P04217 p04217 P04217 P04217-2 NP_000005.3 a|b;c+d').ids).toEqual([
      'P04217',
      'p04217',
      'P04217',
      'P04217-2',
      'NP_000005.3',
      'a|b;c+d',
    ])
  })

  it('treats Unicode spaces and a byte-order mark as separators, and keeps other characters', () => {
    expect(splitIds('﻿P04217 P01023 P0é4217 P0\u00004217').ids).toEqual([
      'P04217',
      'P01023',
      'P0é4217',
      'P0\u00004217',
    ])
  })

  it('finds no IDs in empty or blank text', () => {
    for (const text of ['', ' ', '\n\r\n', ' , ,\t1.5']) {
      expect(splitIds(text).ids).toEqual([])
    }
  })

  it('splits 100,000 lines quickly', () => {
    const text = Array.from({ length: 100_000 }, (_, i) => `P${String(i).padStart(5, '0')}`).join(
      '\n'
    )
    const start = performance.now()

    const { ids, lines } = splitIds(text)

    expect(performance.now() - start).toBeLessThan(500)
    expect(ids).toHaveLength(100_000)
    expect(lines[99_999]).toBe(100_000)
  })
})

describe('shownId', () => {
  it('shows a short ID as typed', () => {
    expect(shownId('P0é4217')).toBe('P0é4217')
  })

  it('cuts a long ID short', () => {
    expect(shownId('A'.repeat(65))).toBe(`${'A'.repeat(24)}…`)
  })

  it('shows control characters as U+FFFD', () => {
    expect(shownId('P0\u00004217\u007f')).toBe('P0�4217�')
  })
})

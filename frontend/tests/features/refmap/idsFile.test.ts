import { describe, expect, it } from 'vitest'

import { LARGEST_FILE_BYTES, readIdsFile } from '@/features/refmap/idsFile'

describe('readIdsFile', () => {
  it("reads a text file's contents as UTF-8", async () => {
    const file = new File(['P04217\tA1BG\nP0é1023\n'], 'ids.txt', { type: 'text/plain' })

    expect(await readIdsFile(file)).toEqual({ text: 'P04217\tA1BG\nP0é1023\n' })
  })

  it('reads a file of exactly the largest size', async () => {
    const file = new File(['P'.repeat(LARGEST_FILE_BYTES)], 'ids.txt')

    const read = await readIdsFile(file)

    expect('text' in read && read.text.length).toBe(LARGEST_FILE_BYTES)
  })

  it('refuses a larger file without reading it', async () => {
    const file = new File(['P'.repeat(LARGEST_FILE_BYTES + 1)], 'ids.txt')

    expect(await readIdsFile(file)).toEqual({ refused: expect.stringMatching(/larger than 10 MB/) })
  })

  it("says when a file can't be read", async () => {
    const file = new File(['P04217'], 'ids.txt')
    file.text = () => Promise.reject(new Error('NotReadableError at C:\\Users\\me'))

    expect(await readIdsFile(file)).toEqual({ refused: expect.stringMatching(/couldn.t be read/) })
  })
})

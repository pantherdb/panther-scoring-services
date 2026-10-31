/**
 * The largest file the IDs box reads. 100,000 lines of a 64-character ID, a tab and an
 * expression value are under 8 MB; anything much larger isn't a list of IDs.
 */
export const LARGEST_FILE_BYTES = 10 * 1024 * 1024

/**
 * A text file's contents, read in the browser: nothing is uploaded. UTF-8, as the box's text
 * is sent; a byte-order mark is dropped by the decoder. A file too large, or that can't be
 * read, gives a message for the IDs field instead, in fixed text.
 */
export async function readIdsFile(file: Blob): Promise<{ text: string } | { refused: string }> {
  if (file.size > LARGEST_FILE_BYTES) {
    return { refused: 'The file is larger than 10 MB, so it wasn’t read. Choose a list of IDs.' }
  }
  try {
    return { text: await file.text() }
  } catch {
    return { refused: 'The file couldn’t be read. Try again, or paste the IDs instead.' }
  }
}

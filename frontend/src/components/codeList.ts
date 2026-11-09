// A list of codes with names, such as cSNP's species or refmap's organisms, as a form's code
// field needs it: loaded, loading, or failed with a way to try again.

/** One entry of a code list: the code a request sends, and the name a user looks for. */
export type CodeEntry = { code: string; name: string }

export type CodeList =
  | { status: 'loaded'; entries: CodeEntry[]; codes: ReadonlySet<string> }
  | { status: 'loading' }
  | { status: 'failed'; retry: () => void }

// One collator for every sort: much faster than localeCompare on each pair of 1,533 names.
const collator = new Intl.Collator('en')

/** The entries sorted by name, for a selector: the API gives them in its own order. */
export function byName<Entry extends CodeEntry>(entries: readonly Entry[]): Entry[] {
  return [...entries].sort((a, b) => collator.compare(a.name, b.name))
}

/**
 * A code list from an RTK Query result. "Loading" is any time there's no data and no error,
 * so a retry after a failure shows as loading too.
 */
export function codeListOf({
  data,
  isError,
  refetch,
}: {
  data: readonly CodeEntry[] | undefined
  isError: boolean
  refetch: () => unknown
}): CodeList {
  if (data) {
    return {
      status: 'loaded',
      entries: byName(data),
      codes: new Set(data.map(entry => entry.code)),
    }
  }
  if (isError) {
    return {
      status: 'failed',
      retry: () => {
        void refetch()
      },
    }
  }
  return { status: 'loading' }
}

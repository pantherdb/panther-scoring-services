import { Button, Loader, Select, TextInput } from '@mantine/core'

import type { CodeList } from './codeList'

/** What a code field says, in fixed text: a failure could carry build details. */
export type CodeListTexts = {
  label: string
  /** Under the selector: how to find an entry. */
  description: string
  /** In the field while the list loads. */
  loading: string
  /** In the open list when no entry matches what was typed. */
  nothingFound: string
  /** Under the box for a code, when the list couldn't be loaded. */
  failed: string
  /** The button that loads the list again. */
  retry: string
}

type Props = {
  list: CodeList
  texts: CodeListTexts
  /** The code in the draft. */
  value: string
  onChange: (code: string) => void
  error: string | undefined
  /** At most this many options are shown while typing, for a long list. */
  limit?: number
}

// A code from a list, such as a species or an organism: a searchable list of the API's entries
// once it has loaded, each by its name and code, and a box for a code if it can't be, so the
// form still works. The draft holds the code either way.
export function CodeListField({ list, texts, value, onChange, error, limit }: Props) {
  switch (list.status) {
    case 'loaded':
      return (
        <Select
          label={texts.label}
          description={texts.description}
          data={list.entries.map(({ code, name }) => ({ value: code, label: `${name} (${code})` }))}
          value={list.codes.has(value) ? value : null}
          onChange={code => onChange(code ?? '')}
          searchable
          limit={limit}
          allowDeselect={false}
          nothingFoundMessage={texts.nothingFound}
          // Fixed, not absolute: on opening, Mantine scrolls the chosen option into view before
          // the list is placed under the field. Placed absolutely, it's still at the top of the
          // page then, so the page jumped to the top and the list was hidden with the field.
          comboboxProps={{ floatingStrategy: 'fixed' }}
          spellCheck={false}
          error={error}
          className="max-w-md"
        />
      )
    case 'loading':
      return (
        <Select
          label={texts.label}
          description={texts.description}
          data={[]}
          value={null}
          placeholder={texts.loading}
          rightSection={<Loader size="xs" />}
          disabled
          error={error}
          className="max-w-md"
        />
      )
    case 'failed':
      return (
        <div className="flex flex-col items-start gap-1">
          <TextInput
            label={texts.label}
            description={texts.failed}
            value={value}
            onChange={event => onChange(event.currentTarget.value)}
            spellCheck={false}
            autoCapitalize="characters"
            error={error}
            className="w-full max-w-xs"
          />
          <Button variant="subtle" size="compact-sm" onClick={list.retry}>
            {texts.retry}
          </Button>
        </div>
      )
  }
}

import { Button, Loader, Select, TextInput } from '@mantine/core'

import type { SpeciesList } from './useCsnpSpecies'

type Props = {
  list: SpeciesList
  /** The species code in the draft. */
  value: string
  onChange: (code: string) => void
  error: string | undefined
}

const LABEL = 'Species'

// The species: a searchable list of the API's species once it has loaded, and a box for a
// code if it can't be, so the form still works. The draft holds the code either way.
export function SpeciesField({ list, value, onChange, error }: Props) {
  switch (list.status) {
    case 'loaded':
      return (
        <Select
          label={LABEL}
          description="Type part of a name or a code to find a species."
          data={list.species.map(({ code, name }) => ({ value: code, label: `${name} (${code})` }))}
          value={list.codes.has(value) ? value : null}
          onChange={code => onChange(code ?? '')}
          searchable
          allowDeselect={false}
          nothingFoundMessage="No species matches"
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
          label={LABEL}
          description="Type part of a name or a code to find a species."
          data={[]}
          value={null}
          placeholder="Loading species…"
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
            label={LABEL}
            // Fixed text: the failure could carry build details.
            description="The list of species couldn’t be loaded. Type a PANTHER species code, such as HUMAN."
            value={value}
            onChange={event => onChange(event.currentTarget.value)}
            spellCheck={false}
            autoCapitalize="characters"
            error={error}
            className="w-full max-w-xs"
          />
          <Button variant="subtle" size="compact-sm" onClick={list.retry}>
            Load the list of species again
          </Button>
        </div>
      )
  }
}

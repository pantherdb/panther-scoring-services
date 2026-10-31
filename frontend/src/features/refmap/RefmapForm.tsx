import { Alert, Button, TextInput } from '@mantine/core'
import { type FormEvent, useDeferredValue, useReducer } from 'react'

import { checkDraft } from './checks'
import { draftReducer, initialDraft } from './draft'
import { IdsField } from './IdsField'
import { splitIds } from './ids'
import { readIdsFile } from './idsFile'
import { SubmitAlert } from './SubmitAlert'
import { useSubmitRefmap } from './useSubmitRefmap'

// The refmap form: the IDs, the organism, the example, and submitting. The client checks run
// first; the API's errors then land on the same fields.
export function RefmapForm() {
  const [draft, dispatch] = useReducer(draftReducer, initialDraft)
  const { submit, isSubmitting, problem } = useSubmitRefmap(dispatch)
  const { values, errors } = draft
  // The count follows the box a render behind, so typing in a list of 100,000 IDs isn't held
  // up by splitting it on every key.
  const counted = splitIds(useDeferredValue(values.ids))

  async function loadFile(file: File) {
    const read = await readIdsFile(file)
    if ('text' in read) dispatch({ type: 'edited', field: 'ids', value: read.text })
    else dispatch({ type: 'fileRefused', message: read.refused })
  }

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const split = splitIds(values.ids)
    const found = checkDraft(values, split)
    dispatch({ type: 'checked', fields: found })
    if (Object.keys(found).length === 0) void submit(values, split)
  }

  return (
    <form noValidate onSubmit={onSubmit} className="flex flex-col gap-4">
      <div>
        <Button variant="subtle" onClick={() => dispatch({ type: 'exampleUsed' })}>
          Use an example
        </Button>
      </div>
      <IdsField
        value={values.ids}
        onChange={text => dispatch({ type: 'edited', field: 'ids', value: text })}
        onFile={loadFile}
        error={errors.fields.ids?.join(' ')}
        split={counted}
      />
      <TextInput
        label="Organism"
        description="The UniProt species code of the organism the IDs are from, such as HUMAN."
        value={values.organism}
        onChange={event =>
          dispatch({ type: 'edited', field: 'organism', value: event.currentTarget.value })
        }
        spellCheck={false}
        autoCapitalize="characters"
        error={errors.fields.organism?.join(' ')}
        className="w-full max-w-xs"
      />
      {errors.form.length > 0 && (
        <Alert title="Some of the input wasn’t accepted">
          <ul className="flex flex-col gap-1">
            {errors.form.map(message => (
              <li key={message}>{message}</li>
            ))}
          </ul>
        </Alert>
      )}
      <SubmitAlert problem={problem} />
      <div>
        <Button type="submit" loading={isSubmitting} disabled={isSubmitting}>
          Map IDs
        </Button>
      </div>
    </form>
  )
}

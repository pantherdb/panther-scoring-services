import { Alert, Button } from '@mantine/core'
import { type FormEvent, useDeferredValue, useReducer } from 'react'

import { CodeListField, type CodeListTexts } from '@/components/CodeListField'
import { FilledFromJob, useEditedInput } from '@/features/jobs'

import { checkDraft } from './checks'
import { draftReducer, startingDraft } from './draft'
import { IdsField } from './IdsField'
import { splitIds } from './ids'
import { readIdsFile } from './idsFile'
import { SubmitAlert } from './SubmitAlert'
import { useRefmapOrganisms } from './useRefmapOrganisms'
import { useSubmitRefmap } from './useSubmitRefmap'

const ORGANISM_TEXTS: CodeListTexts = {
  label: 'Organism',
  description: 'The organism the IDs are from. Type part of a name or a code to find it.',
  loading: 'Loading organisms…',
  nothingFound: 'No organism matches',
  failed:
    'The list of organisms couldn’t be loaded. Type the UniProt species code of the organism, such as ENDPU.',
  retry: 'Load the list of organisms again',
}

// Options shown at once while typing: Mantine renders every match, and there are 1,533.
const MOST_OPTIONS = 50

// The refmap form: the IDs, the organism, the example, and submitting. The client checks run
// first; the API's errors then land on the same fields.
export function RefmapForm() {
  // From "Edit and resubmit", the earlier job's input; the reducer reads it once, on mount. The
  // page remounts the form when it's opened again, so a new visit starts from its own state.
  const edited = useEditedInput('refmap')
  const [draft, dispatch] = useReducer(draftReducer, edited, startingDraft)
  const { submit, isSubmitting, problem } = useSubmitRefmap(dispatch)
  const organisms = useRefmapOrganisms()
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
    // Once the list has loaded, the organism must be one of it, as the API requires.
    const found = checkDraft(
      values,
      split,
      organisms.status === 'loaded' ? organisms.codes : undefined
    )
    dispatch({ type: 'checked', fields: found })
    if (Object.keys(found).length === 0) void submit(values, split)
  }

  return (
    <form noValidate onSubmit={onSubmit} className="flex flex-col gap-4">
      {draft.filledFromJob && <FilledFromJob />}
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
      <CodeListField
        list={organisms}
        texts={ORGANISM_TEXTS}
        value={values.organism}
        onChange={code => dispatch({ type: 'edited', field: 'organism', value: code })}
        error={errors.fields.organism?.join(' ')}
        limit={MOST_OPTIONS}
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

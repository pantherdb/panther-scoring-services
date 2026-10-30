import { Alert, Button, Textarea } from '@mantine/core'
import { type FormEvent, useReducer } from 'react'

import { checkDraft } from './checks'
import { type CsnpField, draftReducer, initialDraft } from './draft'
import { SpeciesField } from './SpeciesField'
import { SubmitAlert } from './SubmitAlert'
import { useCsnpSpecies } from './useCsnpSpecies'
import { useSubmitCsnp } from './useSubmitCsnp'

// The cSNP form: the three fields, the example, and submitting. The client checks run
// first; the API's errors then land on the same fields.
export function CsnpForm() {
  const [draft, dispatch] = useReducer(draftReducer, initialDraft)
  const { submit, isSubmitting, problem } = useSubmitCsnp(dispatch)
  const species = useCsnpSpecies()
  const { values, errors } = draft

  function edit(name: CsnpField, value: string) {
    dispatch({ type: 'edited', field: name, value })
  }

  function field(name: CsnpField) {
    return {
      value: values[name],
      onChange: (event: { currentTarget: { value: string } }) =>
        edit(name, event.currentTarget.value),
      error: errors.fields[name]?.join(' '),
    }
  }

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    // Once the list has loaded, the species must be one of it, as the API requires.
    const found = checkDraft(values, species.status === 'loaded' ? species.codes : undefined)
    dispatch({ type: 'checked', fields: found })
    if (Object.keys(found).length === 0) void submit(values)
  }

  return (
    <form noValidate onSubmit={onSubmit} className="flex flex-col gap-4">
      <div>
        <Button variant="subtle" onClick={() => dispatch({ type: 'exampleUsed' })}>
          Use an example
        </Button>
      </div>
      <Textarea
        label="Protein sequence"
        description="Plain residues, or FASTA with one header line. One protein."
        rows={8}
        resize="vertical"
        spellCheck={false}
        classNames={{ input: 'font-mono' }}
        {...field('sequence')}
      />
      <Textarea
        label="Substitutions"
        description="Such as L46P, separated by spaces, commas or new lines. Positions count from 1 in this sequence."
        rows={4}
        resize="vertical"
        spellCheck={false}
        classNames={{ input: 'font-mono' }}
        {...field('substitutions')}
      />
      <SpeciesField
        list={species}
        value={values.species}
        onChange={code => edit('species', code)}
        error={errors.fields.species?.join(' ')}
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
          Score substitutions
        </Button>
      </div>
    </form>
  )
}

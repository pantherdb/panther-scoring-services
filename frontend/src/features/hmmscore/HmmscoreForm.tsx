import { Alert, Button, Textarea } from '@mantine/core'
import { type FormEvent, useState } from 'react'

import { service } from '@/app/services'
import { APOE_SEQUENCE } from '@/components/apoe'
import { SubmitAlert } from '@/components/SubmitAlert'
import { FilledFromJob, useEditedInput } from '@/features/jobs'

import { checkHmmscore } from './checks'
import { type Rejection, useSubmitHmmscore } from './useSubmitHmmscore'

/** What's wrong with the input: the sequence's messages, and those on no field of the form. */
type Errors = { sequence: string[]; form: string[] }

const NO_ERRORS: Errors = { sequence: [], form: [] }

// The HMM scoring form: one box, the example, and submitting. One box, so the draft is plain
// state. The client checks run first; the API's errors then land on the same box.
export function HmmscoreForm() {
  // From "Edit and resubmit", the earlier job's input, read once, on mount. The page remounts the
  // form when it's opened again, so a new visit starts from its own state.
  const edited = useEditedInput('hmmscore')
  const [sequence, setSequence] = useState(edited?.sequence ?? '')
  const [filledFromJob, setFilledFromJob] = useState(edited !== undefined)
  const [errors, setErrors] = useState<Errors>(NO_ERRORS)
  const { submit, isSubmitting, failure } = useSubmitHmmscore(({ sequence, other }: Rejection) =>
    setErrors({ sequence, form: other })
  )

  function edit(text: string) {
    setSequence(text)
    setErrors(NO_ERRORS)
  }

  function fillWithExample() {
    edit(APOE_SEQUENCE)
    setFilledFromJob(false)
  }

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const found = checkHmmscore({ sequence })
    setErrors({ sequence: found, form: [] })
    if (found.length === 0) void submit({ sequence })
  }

  return (
    <form noValidate onSubmit={onSubmit} className="flex flex-col gap-4">
      {filledFromJob && <FilledFromJob />}
      <div>
        <Button variant="subtle" onClick={fillWithExample}>
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
        value={sequence}
        onChange={event => edit(event.currentTarget.value)}
        error={errors.sequence.length > 0 ? errors.sequence.join(' ') : undefined}
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
      <SubmitAlert
        problem={failure?.problem ?? null}
        title={service('hmmscore').title}
        retryAfter={failure?.retryAfter ?? null}
      />
      <div>
        <Button type="submit" loading={isSubmitting} disabled={isSubmitting}>
          Score sequence
        </Button>
      </div>
    </form>
  )
}

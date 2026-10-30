import type { CsnpInput, InputError } from '@/app/api/wire'

import { example } from './example'
import { splitSubstitutions } from './substitutions'

// The cSNP form's draft: what's in each box, and what's wrong with it. A reducer, because
// the values and errors depend on each other: editing a box clears what was said about it.

export const CSNP_FIELDS = ['sequence', 'substitutions', 'species'] as const
export type CsnpField = (typeof CSNP_FIELDS)[number]

/** Each box's text, as typed. */
export type CsnpValues = Record<CsnpField, string>

export type DraftErrors = {
  /** Each field's messages; a field with none is left out. */
  fields: Partial<Record<CsnpField, string[]>>
  /** Messages that belong to no field of the form. */
  form: string[]
}

export type Draft = { values: CsnpValues; errors: DraftErrors }

export type DraftAction =
  | { type: 'edited'; field: CsnpField; value: string }
  | { type: 'exampleUsed' }
  | { type: 'checked'; fields: DraftErrors['fields'] }
  | {
      type: 'rejected'
      fields: Partial<Record<CsnpField, InputError[]>>
      other: string[]
      /** The substitutions as sent, to name the one an error is about. */
      sent: string[]
    }

const NO_ERRORS: DraftErrors = { fields: {}, form: [] }

export const initialDraft: Draft = {
  values: { sequence: '', substitutions: '', species: 'HUMAN' },
  errors: NO_ERRORS,
}

// An API message about one substitution names it by its place, counted from 1, and by
// the token from the client's own copy of what was sent: the box holds every token, and
// the API never echoes one.
function messageOf(field: CsnpField, { msg, item }: InputError, sent: string[]) {
  if (field !== 'substitutions' || item === null) return msg
  const token = sent[item]
  return token === undefined
    ? `Substitution ${item + 1}: ${msg}`
    : `Substitution ${item + 1} (${token}): ${msg}`
}

export function draftReducer(draft: Draft, action: DraftAction): Draft {
  switch (action.type) {
    case 'edited': {
      const { [action.field]: _cleared, ...fields } = draft.errors.fields
      return {
        values: { ...draft.values, [action.field]: action.value },
        errors: { fields, form: [] },
      }
    }
    case 'exampleUsed':
      return { values: example, errors: NO_ERRORS }
    case 'checked':
      return { ...draft, errors: { fields: action.fields, form: [] } }
    case 'rejected': {
      const fields: DraftErrors['fields'] = {}
      for (const field of CSNP_FIELDS) {
        const errors = action.fields[field]
        if (errors) fields[field] = errors.map(error => messageOf(field, error, action.sent))
      }
      return { ...draft, errors: { fields, form: action.other } }
    }
  }
}

/** The request's input: the sequence as typed, the substitutions split, the species trimmed. */
export function draftInput(values: CsnpValues): CsnpInput {
  return {
    sequence: values.sequence,
    substitutions: splitSubstitutions(values.substitutions),
    species: values.species.trim(),
  }
}

import type { InputError, RefmapInput } from '@/app/api/wire'

import { example } from './example'
import { shownId, type SplitIds } from './ids'

// The refmap form's draft: what's in each box, and what's wrong with it. A reducer, as cSNP's
// is: editing a box clears what was said about it, and a file read fills a box.

export const REFMAP_FIELDS = ['ids', 'organism'] as const
export type RefmapField = (typeof REFMAP_FIELDS)[number]

/** Each box's text, as typed. */
export type RefmapValues = Record<RefmapField, string>

export type DraftErrors = {
  /** Each field's messages; a field with none is left out. */
  fields: Partial<Record<RefmapField, string[]>>
  /** Messages that belong to no field of the form. */
  form: string[]
}

export type Draft = { values: RefmapValues; errors: DraftErrors }

export type DraftAction =
  | { type: 'edited'; field: RefmapField; value: string }
  | { type: 'exampleUsed' }
  | { type: 'fileRefused'; message: string }
  | { type: 'checked'; fields: DraftErrors['fields'] }
  | {
      type: 'rejected'
      fields: Partial<Record<RefmapField, InputError[]>>
      other: string[]
      /** The IDs as sent, with their lines, to name the one an error is about. */
      sent: SplitIds
    }

const NO_ERRORS: DraftErrors = { fields: {}, form: [] }

// No organism to start with: the API has no default, so that a list is never mapped against
// an organism nobody chose.
export const initialDraft: Draft = {
  values: { ids: '', organism: '' },
  errors: NO_ERRORS,
}

const number = new Intl.NumberFormat('en-US')

// An API message about one ID names it by its place, counted from 1, its line and the ID as
// sent, from the client's own copy: the API never echoes one.
function messageOf(field: RefmapField, { msg, item }: InputError, sent: SplitIds) {
  if (field !== 'ids' || item === null) return msg
  const id = sent.ids[item]
  const line = sent.lines[item]
  const place = number.format(item + 1)
  return id === undefined || line === undefined
    ? `ID ${place}: ${msg}`
    : `ID ${place} (${shownId(id)}, line ${number.format(line)}): ${msg}`
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
    case 'fileRefused':
      return {
        ...draft,
        errors: { fields: { ...draft.errors.fields, ids: [action.message] }, form: [] },
      }
    case 'checked':
      return { ...draft, errors: { fields: action.fields, form: [] } }
    case 'rejected': {
      const fields: DraftErrors['fields'] = {}
      for (const field of REFMAP_FIELDS) {
        const errors = action.fields[field]
        if (errors) fields[field] = errors.map(error => messageOf(field, error, action.sent))
      }
      return { ...draft, errors: { fields, form: action.other } }
    }
  }
}

/** The request's input: the organism trimmed, the IDs as split. */
export function draftInput(values: RefmapValues, split: SplitIds): RefmapInput {
  return { organism: values.organism.trim(), ids: split.ids }
}

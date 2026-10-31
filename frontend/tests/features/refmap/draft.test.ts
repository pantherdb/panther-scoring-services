import { describe, expect, it } from 'vitest'

import { type Draft, draftInput, draftReducer, initialDraft } from '@/features/refmap/draft'
import { example } from '@/features/refmap/example'
import { splitIds } from '@/features/refmap/ids'

const withErrors: Draft = {
  values: { ids: 'P04217', organism: 'human' },
  errors: { fields: { ids: ['Bad ID.'], organism: ['Bad organism.'] }, form: ['Other.'] },
}

describe('the refmap draft', () => {
  it('starts with no IDs and no organism', () => {
    expect(initialDraft.values).toEqual({ ids: '', organism: '' })
    expect(initialDraft.errors).toEqual({ fields: {}, form: [] })
  })

  it("clears an edited field's errors and the form's, and keeps the other field's", () => {
    const draft = draftReducer(withErrors, { type: 'edited', field: 'organism', value: 'HUMAN' })

    expect(draft.values).toEqual({ ids: 'P04217', organism: 'HUMAN' })
    expect(draft.errors).toEqual({ fields: { ids: ['Bad ID.'] }, form: [] })
  })

  it('fills both fields with the example, and clears every error', () => {
    const draft = draftReducer(withErrors, { type: 'exampleUsed' })

    expect(draft.values).toEqual(example)
    expect(draft.values.organism).toBe('HUMAN')
    expect(splitIds(draft.values.ids).ids).toEqual([
      'P04217',
      'P01023',
      'P02649',
      'P04637',
      'P38398',
      'P00533',
    ])
    expect(draft.errors).toEqual({ fields: {}, form: [] })
  })

  it("puts a refused file's message on the IDs, and keeps the box's text", () => {
    const draft = draftReducer(withErrors, { type: 'fileRefused', message: 'Too large.' })

    expect(draft.values).toEqual(withErrors.values)
    expect(draft.errors).toEqual({
      fields: { ids: ['Too large.'], organism: ['Bad organism.'] },
      form: [],
    })
  })

  it("replaces every error with the checks' findings", () => {
    const draft = draftReducer(withErrors, { type: 'checked', fields: { organism: ['Again.'] } })

    expect(draft.errors).toEqual({ fields: { organism: ['Again.'] }, form: [] })
  })

  it("words the API's errors, naming an ID by its place, line and as sent", () => {
    const sent = splitIds('P04217\n\nP01023 P02649')

    const draft = draftReducer(initialDraft, {
      type: 'rejected',
      fields: {
        ids: [
          { msg: 'Refused.', item: 2 },
          { msg: 'Whole list.', item: null },
          { msg: 'Unknown.', item: 7 },
        ],
        organism: [{ msg: 'Bad organism.', item: null }],
      },
      other: ['Extra input.'],
      sent,
    })

    expect(draft.errors).toEqual({
      fields: {
        ids: ['ID 3 (P02649, line 3): Refused.', 'Whole list.', 'ID 8: Unknown.'],
        organism: ['Bad organism.'],
      },
      form: ['Extra input.'],
    })
  })

  it('sends the organism trimmed and the IDs as split', () => {
    const values = { ids: 'P04217, p04217\tvalue', organism: ' HUMAN ' }

    expect(draftInput(values, splitIds(values.ids))).toEqual({
      organism: 'HUMAN',
      ids: ['P04217', 'p04217'],
    })
  })
})

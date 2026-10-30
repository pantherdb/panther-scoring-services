import { describe, expect, it } from 'vitest'

import { draftInput, draftReducer, initialDraft, type Draft } from '@/features/csnp/draft'
import { example } from '@/features/csnp/example'

const withErrors: Draft = {
  values: { sequence: 'MKV', substitutions: 'L2P', species: 'human' },
  errors: {
    fields: { sequence: ['seq error'], substitutions: ['sub error'], species: ['species error'] },
    form: ['form error'],
  },
}

describe('initialDraft', () => {
  it('starts empty, with the species HUMAN and no errors', () => {
    expect(initialDraft).toEqual({
      values: { sequence: '', substitutions: '', species: 'HUMAN' },
      errors: { fields: {}, form: [] },
    })
  })
})

describe('draftReducer', () => {
  it("sets an edited field's text, and clears that field's errors and the form's", () => {
    const next = draftReducer(withErrors, { type: 'edited', field: 'species', value: 'HUMAN' })

    expect(next.values).toEqual({ ...withErrors.values, species: 'HUMAN' })
    expect(next.errors).toEqual({
      fields: { sequence: ['seq error'], substitutions: ['sub error'] },
      form: [],
    })
  })

  it("keeps an edited field's text exactly as typed", () => {
    const next = draftReducer(initialDraft, {
      type: 'edited',
      field: 'sequence',
      value: ' >x\nmk ',
    })

    expect(next.values.sequence).toBe(' >x\nmk ')
  })

  it('replaces every value with the example, and clears every error', () => {
    const next = draftReducer(withErrors, { type: 'exampleUsed' })

    expect(next).toEqual({ values: example, errors: { fields: {}, form: [] } })
  })

  it("replaces the errors with the client checks' errors", () => {
    const next = draftReducer(withErrors, {
      type: 'checked',
      fields: { sequence: ['Enter a protein sequence.'] },
    })

    expect(next.values).toBe(withErrors.values)
    expect(next.errors).toEqual({ fields: { sequence: ['Enter a protein sequence.'] }, form: [] })
  })

  it("replaces the errors with the API's, naming a substitution by its place and as sent", () => {
    const next = draftReducer(withErrors, {
      type: 'rejected',
      fields: {
        species: [{ msg: 'Bad species.', item: null }],
        substitutions: [
          { msg: 'Bad token.', item: 2 },
          { msg: 'Too many.', item: null },
        ],
      },
      other: ['Extra input.'],
      sent: ['L46P', 'c130r', 'G12|'],
    })

    expect(next.values).toBe(withErrors.values)
    expect(next.errors).toEqual({
      fields: {
        species: ['Bad species.'],
        substitutions: ['Substitution 3 (G12|): Bad token.', 'Too many.'],
      },
      form: ['Extra input.'],
    })
  })

  it('names a substitution by its place alone when the index is past what was sent', () => {
    const next = draftReducer(withErrors, {
      type: 'rejected',
      fields: { substitutions: [{ msg: 'Bad token.', item: 5 }] },
      other: [],
      sent: ['L46P'],
    })

    expect(next.errors.fields.substitutions).toEqual(['Substitution 6: Bad token.'])
  })
})

describe('draftInput', () => {
  it('sends the sequence as typed, the substitutions split, and the species trimmed', () => {
    expect(
      draftInput({ sequence: '>x\nmkv l\n', substitutions: ' L2P\tc3r\n', species: ' HUMAN\n' })
    ).toEqual({ sequence: '>x\nmkv l\n', substitutions: ['L2P', 'c3r'], species: 'HUMAN' })
  })
})

describe('the example', () => {
  it("is the legacy website's: the APOE sequence, four substitutions and HUMAN", () => {
    const input = draftInput(example)

    expect(input.sequence.replace(/\s/g, '')).toMatch(/^MKVLWAALLVTFLAGCQAKVEQAV.*SAAPVPSDNH$/)
    expect(input.sequence.replace(/\s/g, '')).toHaveLength(317)
    expect(input.substitutions).toEqual(['L46P', 'C130R', 'R163C', 'R176C'])
    expect(input.species).toBe('HUMAN')
  })
})

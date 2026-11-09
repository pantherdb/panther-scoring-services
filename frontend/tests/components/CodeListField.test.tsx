import { screen } from '@testing-library/react'
import { useState } from 'react'
import { describe, expect, it, vi } from 'vitest'

import { type CodeList, codeListOf } from '@/components/codeList'
import { CodeListField, type CodeListTexts } from '@/components/CodeListField'

import { renderRoute } from '../utils/render'

const TEXTS: CodeListTexts = {
  label: 'Planet',
  description: 'Type part of a name or a code.',
  loading: 'Loading planets…',
  nothingFound: 'No planet matches',
  failed: 'The planets couldn’t be loaded. Type a code.',
  retry: 'Load the planets again',
}

// Made up for the test, in an order other than by name.
const PLANETS = [
  { code: 'MARS', name: 'Mars' },
  { code: 'EARTH', name: 'Earth' },
  { code: 'VENUS', name: 'Venus' },
  { code: 'JUP', name: 'Jupiter' },
]

type HarnessProps = { list: CodeList; start?: string; limit?: number }

// The field with its value in state, and that value shown, as a form's draft would hold it.
function Harness({ list, start = '', limit }: HarnessProps) {
  const [value, setValue] = useState(start)
  return (
    <>
      <CodeListField
        list={list}
        texts={TEXTS}
        value={value}
        onChange={setValue}
        error={undefined}
        limit={limit}
      />
      <output aria-label="code">{value}</output>
    </>
  )
}

function renderField(props: HarnessProps) {
  return renderRoute('/', { routes: [{ path: '/', element: <Harness {...props} /> }] })
}

const loaded = codeListOf({ data: PLANETS, isError: false, refetch: () => undefined })

describe('a code field', () => {
  it('offers the loaded entries by name and code, sorted by name, and keeps the chosen code', async () => {
    const { user } = renderField({ list: loaded })
    const field = screen.getByRole('combobox', { name: 'Planet' })
    expect(field).toHaveValue('')

    await user.click(field)

    const options = await screen.findAllByRole('option')
    expect(options.map(option => option.textContent)).toEqual([
      'Earth (EARTH)',
      'Jupiter (JUP)',
      'Mars (MARS)',
      'Venus (VENUS)',
    ])
    await user.click(screen.getByRole('option', { name: 'Mars (MARS)' }))
    expect(field).toHaveValue('Mars (MARS)')
    expect(screen.getByRole('status', { name: 'code' })).toHaveTextContent('MARS')
  })

  it('finds an entry by part of its code, in any case', async () => {
    const { user } = renderField({ list: loaded })

    await user.type(screen.getByRole('combobox', { name: 'Planet' }), 'jup')

    const options = await screen.findAllByRole('option')
    expect(options.map(option => option.textContent)).toEqual(['Jupiter (JUP)'])
  })

  it('shows at most `limit` options', async () => {
    const { user } = renderField({ list: loaded, limit: 2 })

    await user.click(screen.getByRole('combobox', { name: 'Planet' }))

    expect(await screen.findAllByRole('option')).toHaveLength(2)
  })

  it('shows the chosen entry first when a long list is cut to `limit`', async () => {
    // By name: Earth, Jupiter, Mars, Venus. Venus is chosen, past the limit.
    const { user } = renderField({ list: loaded, limit: 2, start: 'VENUS' })

    await user.click(screen.getByRole('combobox', { name: 'Planet' }))

    const options = await screen.findAllByRole('option')
    expect(options.map(option => option.textContent)).toEqual(['Venus (VENUS)', 'Earth (EARTH)'])
  })

  it('shows a typed code with spaces as the entry it names, as it will be sent', () => {
    renderField({ list: loaded, start: ' MARS ' })

    expect(screen.getByRole('combobox', { name: 'Planet' })).toHaveValue('Mars (MARS)')
  })

  it('shows a code not in the list as the code itself, not a blank', async () => {
    const { user } = renderField({ list: loaded, start: 'PLUTO' })
    const field = screen.getByRole('combobox', { name: 'Planet' })
    expect(field).toHaveValue('PLUTO')

    await user.click(field)
    await user.click(screen.getByRole('option', { name: 'Earth (EARTH)' }))

    expect(field).toHaveValue('Earth (EARTH)')
    expect(screen.getByRole('status', { name: 'code' })).toHaveTextContent(/^EARTH$/)
  })

  it('shows the code it holds while the list loads', () => {
    renderField({ list: { status: 'loading' }, start: 'MARS' })

    const field = screen.getByRole('combobox', { name: 'Planet' })
    expect(field).toBeDisabled()
    expect(field).toHaveValue('MARS')
  })

  it('says it is loading, disabled', () => {
    renderField({ list: { status: 'loading' } })

    const field = screen.getByRole('combobox', { name: 'Planet' })
    expect(field).toBeDisabled()
    expect(field).toHaveAttribute('placeholder', 'Loading planets…')
  })

  it('offers a box for the code and a retry when the list failed', async () => {
    const retry = vi.fn()
    const { user } = renderField({ list: { status: 'failed', retry }, start: 'MA' })
    const box = screen.getByRole('textbox', { name: 'Planet' })
    expect(box).toHaveValue('MA')
    expect(box).toHaveAccessibleDescription(TEXTS.failed)

    await user.type(box, 'RS')
    await user.click(screen.getByRole('button', { name: 'Load the planets again' }))

    expect(screen.getByRole('status', { name: 'code' })).toHaveTextContent('MARS')
    expect(retry).toHaveBeenCalledOnce()
  })
})

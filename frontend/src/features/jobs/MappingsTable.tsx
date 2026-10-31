import { Pagination, Table } from '@mantine/core'
import { useId, useState } from 'react'

import type { IdMapping } from '@/app/api/wire'

type Props = {
  mappings: readonly IdMapping[]
}

/** Rows on one page of the table: a job can have 100,000, and only one page is rendered. */
export const MAPPINGS_PER_PAGE = 100

const number = new Intl.NumberFormat('en-US')

const CONTROL_LABELS = {
  first: 'First page',
  previous: 'Previous page',
  next: 'Next page',
  last: 'Last page',
} as const

// The mappings, a page at a time, in the API's order, numbered from 1 as submitted: the same
// ID can be submitted twice.
export function MappingsTable({ mappings }: Props) {
  const headingId = useId()
  const [page, setPage] = useState(1)
  const pages = Math.max(1, Math.ceil(mappings.length / MAPPINGS_PER_PAGE))
  const first = (page - 1) * MAPPINGS_PER_PAGE
  const shown = mappings.slice(first, first + MAPPINGS_PER_PAGE)

  return (
    <div className="flex flex-col gap-2">
      <h3 id={headingId} className="font-semibold">
        Mappings
      </h3>
      {/* A long ID or PANTHER ID that doesn't fit a phone scrolls the table, not the page. */}
      <div className="overflow-x-auto">
        <Table aria-labelledby={headingId}>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>#</Table.Th>
              <Table.Th>ID</Table.Th>
              <Table.Th>PANTHER ID</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {shown.map((mapping, index) => (
              <Table.Tr key={first + index}>
                <Table.Td className="text-ink-muted">{number.format(first + index + 1)}</Table.Td>
                <Table.Td className="font-mono">{mapping.id}</Table.Td>
                {mapping.panther_id === null ? (
                  <Table.Td className="text-ink-muted italic">No PANTHER ID</Table.Td>
                ) : (
                  <Table.Td className="font-mono">{mapping.panther_id}</Table.Td>
                )}
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </div>
      {pages > 1 && (
        <nav aria-label="Pages of mappings" className="flex flex-col items-start gap-2">
          <p className="text-sm text-ink-muted">
            Rows {number.format(first + 1)} to {number.format(first + shown.length)} of{' '}
            {number.format(mappings.length)}
          </p>
          <Pagination
            total={pages}
            value={page}
            onChange={setPage}
            size="sm"
            siblings={1}
            boundaries={1}
            getControlProps={control => ({ 'aria-label': CONTROL_LABELS[control] })}
            getItemProps={item => ({ 'aria-label': `Page ${item}` })}
          />
        </nav>
      )}
    </div>
  )
}

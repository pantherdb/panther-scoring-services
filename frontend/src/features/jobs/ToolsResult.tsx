import { Table } from '@mantine/core'
import { useId } from 'react'

import type { ToolsResult as Result } from '@/app/api/wire'

type Props = {
  result: Result
}

// The tools job's result: each tool and its version, in the order reported.
export function ToolsResult({ result }: Props) {
  const headingId = useId()

  return (
    <section className="flex flex-col gap-2">
      <h3 id={headingId} className="font-semibold">
        Tools
      </h3>
      <Table aria-labelledby={headingId} className="max-w-md">
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Tool</Table.Th>
            <Table.Th>Version</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {result.tools.map(tool => (
            <Table.Tr key={tool.name}>
              <Table.Td>{tool.name}</Table.Td>
              <Table.Td className={tool.version === null ? 'italic' : undefined}>
                {tool.version ?? 'not available'}
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </section>
  )
}

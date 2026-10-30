import { Table } from '@mantine/core'
import { useId } from 'react'

import type { CsnpResult } from '@/app/api/wire'

type Props = {
  result: CsnpResult
}

// A csnp job's result: the family, then each score exactly as the API gives it, in its
// order. Nothing is labelled, coloured or rounded here: the thresholds, the prediction
// labels and the pDel values are the API's alone. A null age or pDel is an empty cell.
export function CsnpScores({ result }: Props) {
  const headingId = useId()

  return (
    <section className="flex flex-col gap-4">
      {result.family === null ? (
        <p className="italic">No PANTHER family</p>
      ) : (
        <p className="font-medium">
          PANTHER family <span className="font-mono font-normal">{result.family}</span>
        </p>
      )}

      <div className="flex flex-col gap-2">
        <h3 id={headingId} className="font-semibold">
          Scores
        </h3>
        {/* The columns wrap to fit a phone. A long message or token that still doesn't
            fit scrolls the table sideways, not the page. */}
        <div className="overflow-x-auto">
          <Table aria-labelledby={headingId}>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Substitution</Table.Th>
                <Table.Th>Age (Mya)</Table.Th>
                <Table.Th>Prediction or message</Table.Th>
                <Table.Th>pDel</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {result.scores.map((score, index) => (
                // The index too: the same token can be submitted twice.
                <Table.Tr key={`${index}-${score.substitution}`}>
                  <Table.Td className="font-mono">{score.substitution}</Table.Td>
                  <Table.Td>{score.age}</Table.Td>
                  <Table.Td>{score.message}</Table.Td>
                  <Table.Td>{score.pdel}</Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </div>
      </div>
    </section>
  )
}

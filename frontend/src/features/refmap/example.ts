// Six IDs from the mapping data's own test list for Endocarpon pusillum (ENDPU), one per line:
// `U1G4Q5`, `U1GCA1` and `U1HRR6` map to subfamilies, `U1GLV9` and `U1GJ40` to families, and
// `U1HQ27` to no PANTHER ID, so the example shows every kind of answer. Which they map to is the
// engine's answer, checked against the legacy service's; nothing here is a mapping.
export const example = {
  ids: ['U1G4Q5', 'U1GCA1', 'U1HRR6', 'U1GLV9', 'U1GJ40', 'U1HQ27'].join('\n'),
  organism: 'ENDPU',
}

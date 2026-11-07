import type { components } from '../../app/api/schema'

// The mocked GET /api/v1/refmap/organisms body: six of the 1,533 organisms refmap maps for, with
// their real codes, names and gene counts (engine/src/panther_engine/refmap/organisms.json), in
// the engine's order, by long name. `pusill` finds two, and `eco57` one of two E. coli strains.
// Also read by the @mock e2e spec, so keep to type imports and relative imports.
export const organisms: components['schemas']['RefmapOrganism'][] = [
  { code: 'ABRPR', name: 'Abrus precatorius', genes: 24653, genes_with_panther_id: 24474 },
  { code: 'ARAVE', name: 'Araneus ventricosus', genes: 246021, genes_with_panther_id: 126890 },
  { code: 'ENDPU', name: 'Endocarpon pusillum', genes: 9228, genes_with_panther_id: 7665 },
  { code: 'ECO57', name: 'Escherichia coli O157:H7', genes: 5049, genes_with_panther_id: 3922 },
  { code: 'ECOK1', name: 'Escherichia coli O1:K1', genes: 4870, genes_with_panther_id: 3884 },
  { code: 'MICPC', name: 'Micromonas pusilla', genes: 10246, genes_with_panther_id: 8789 },
]

// Six reviewed human UniProtKB/Swiss-Prot accessions, one per line: A1BG and A2M (P04217 and
// P01023, the IDs the API's own docs use), APOE (P02649, cSNP's example protein), TP53, BRCA1
// and EGFR. Which of them map, and to what, is the engine's answer: nothing here is a mapping.
export const example = {
  ids: ['P04217', 'P01023', 'P02649', 'P04637', 'P38398', 'P00533'].join('\n'),
  organism: 'HUMAN',
}

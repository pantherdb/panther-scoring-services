import { APOE_SEQUENCE } from '@/components/apoe'

// The legacy website's example input (tips_exampleCsnpInput_content.jsp): human APOE,
// with no header, and four substitutions in it, one per line, as the old help page showed.
export const example = {
  sequence: APOE_SEQUENCE,
  substitutions: ['L46P', 'C130R', 'R163C', 'R176C'].join('\n'),
  species: 'HUMAN',
}
